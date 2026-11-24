"""Tareas proactivas con APScheduler en America/Bogota."""

import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.evolution import EvolutionClient
from app.memory import repository
from app.security import allowed_numbers, is_allowed, mask_phone, normalize_phone

log = logging.getLogger("jarvis.scheduler")

_scheduler: AsyncIOScheduler | None = None


def zona_horaria() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


async def enviar(numero: str, texto: str, job_id: str) -> bool:
    try:
        await asyncio.to_thread(EvolutionClient().send_text, numero, texto)
        log.info("job_enviado job_id=%s telefono=%s", job_id, mask_phone(numero))
        return True
    except Exception as exc:
        log.error("job_error job_id=%s tipo=%s", job_id, type(exc).__name__)
        return False


async def resumen_matutino() -> None:
    fecha = datetime.now(zona_horaria()).strftime("%A %d de %B de %Y")
    for numero in sorted(allowed_numbers()):
        resumen = repository.obtener_resumen(numero) or "No hay pendientes registrados."
        texto = f"Buenos días. Hoy es {fecha}. {resumen}"
        await enviar(numero, texto, "resumen_matutino")


async def cierre_diario() -> None:
    for numero in sorted(allowed_numbers()):
        hechos = repository.obtener_hechos(numero)
        pendiente = hechos.get("pendiente") or "No tienes pendientes anotados."
        texto = f"Buenas noches. Cierre del día: {pendiente}"
        await enviar(numero, texto, "cierre_diario")


async def procesar_recordatorios() -> None:
    """Revisa la SQLite en cada minuto; un fallo deja el job pendiente para reintentar."""
    for trabajo in repository.jobs_pendientes():
        numero = normalize_phone(trabajo["phone"])
        if not is_allowed(numero):
            log.warning("job_numero_no_permitido job_id=%s", trabajo["id"])
            repository.eliminar_job(trabajo["id"])
            continue
        if await enviar(numero, trabajo["payload"], trabajo["id"]):
            repository.marcar_job_enviado(trabajo["id"])


async def iniciar_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    zona = zona_horaria()
    _scheduler = AsyncIOScheduler(timezone=zona)
    comun = {"max_instances": 1, "coalesce": True, "replace_existing": True}
    _scheduler.add_job(
        resumen_matutino,
        CronTrigger(hour=7, minute=0, timezone=zona),
        id="resumen_matutino",
        **comun,
    )
    _scheduler.add_job(
        cierre_diario,
        CronTrigger(hour=21, minute=0, timezone=zona),
        id="cierre_diario",
        **comun,
    )
    _scheduler.add_job(
        procesar_recordatorios,
        CronTrigger(second=0, timezone=zona),
        id="recordatorios",
        **comun,
    )
    _scheduler.start()
    log.info("scheduler_iniciado zona=%s trabajos=%s", get_settings().timezone, len(_scheduler.get_jobs()))


async def detener_scheduler() -> None:
    global _scheduler
    actual = _scheduler
    _scheduler = None
    if actual is None:
        return
    try:
        if actual.running:
            actual.shutdown(wait=False)
    except RuntimeError as exc:
        # El event loop puede haberse cerrado antes del apagado (p. ej. en pruebas).
        log.warning("scheduler_shutdown_loop_cerrado tipo=%s", type(exc).__name__)


def trabajos_programados() -> list:
    return list(_scheduler.get_jobs()) if _scheduler is not None else []


def utc_de_bogota(momento: datetime) -> datetime:
    """Convierte un datetime consciente a UTC para guardarlo en SQLite."""
    return momento.astimezone(timezone.utc)
