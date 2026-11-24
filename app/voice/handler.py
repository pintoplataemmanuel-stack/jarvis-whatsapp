"""Descarga, transcribe y entrega la nota de voz al manejador común."""

import asyncio
import logging
from pathlib import Path

from app.agent import handle_message
from app.config import get_settings
from app.evolution import EvolutionClient
from app.security import is_allowed, mask_phone, normalize_phone, permitir_mensaje
from app.voice.transcription import transcribir

log = logging.getLogger("jarvis.voice")


def ruta_audio(message_id: str) -> Path:
    directorio = Path(get_settings().db_path).parent / "audio"
    directorio.mkdir(parents=True, exist_ok=True)
    seguro = "".join(caracter for caracter in message_id if caracter.isalnum() or caracter in "-_")
    return directorio / f"{seguro or 'audio'}.ogg"


async def procesar_nota_de_voz(phone: str, message_id: str) -> None:
    numero = normalize_phone(phone)
    cliente = EvolutionClient()

    if not is_allowed(numero):
        log.warning("voz_numero_no_permitido id=%s telefono=%s", message_id or "?", mask_phone(phone))
        return
    if not permitir_mensaje(numero):
        log.warning("voz_rate_limit id=%s telefono=%s", message_id or "?", mask_phone(phone))
        return
    if not get_settings().voice_enabled:
        cliente.send_text(numero, "Las notas de voz están desactivadas en este momento.")
        return

    ruta = ruta_audio(message_id or "sin_id")
    try:
        datos = await asyncio.to_thread(cliente.download_media, message_id)
        ruta.write_bytes(datos)
        texto = await asyncio.to_thread(transcribir, ruta)
    except Exception as exc:
        log.error("voz_error id=%s tipo=%s", message_id or "?", type(exc).__name__)
        try:
            cliente.send_text(numero, "No pude descargar tu nota de voz. Intenta de nuevo.")
        except Exception:
            log.error("voz_error_respuesta id=%s", message_id or "?")
        return
    finally:
        ruta.unlink(missing_ok=True)

    texto = (texto or "").strip()
    if not texto:
        cliente.send_text(numero, "No te escuché bien. Repite el mensaje más cerca del micrófono.")
        log.info("voz_vacia id=%s telefono=%s", message_id or "?", mask_phone(phone))
        return

    log.info("voz_transcrita id=%s telefono=%s longitud=%s", message_id or "?", mask_phone(phone), len(texto))
    await handle_message(phone, texto, message_id)
