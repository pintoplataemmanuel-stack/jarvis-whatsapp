import hmac
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.agent import handle_message
from app.config import get_settings
from app.scheduler import detener_scheduler, iniciar_scheduler
from app.schemas import EvolutionMessage, EvolutionWebhookPayload
from app.security import mask_phone
from app.voice.handler import procesar_nota_de_voz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger("jarvis.webhook")

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await iniciar_scheduler()
    yield
    await detener_scheduler()


app = FastAPI(title="Jarvis WhatsApp backend", version="0.1.0", lifespan=lifespan)


def es_nota_de_voz(message: EvolutionMessage | None) -> bool:
    return bool(message and (message.audio_message or message.ptt_message))


def extract_text(message: EvolutionMessage | None) -> str:
    if message is None:
        return ""
    if message.conversation:
        return message.conversation
    if message.extended_text_message and isinstance(message.extended_text_message.get("text"), str):
        texto = message.extended_text_message["text"]
        contexto = message.extended_text_message.get("contextInfo") or {}
        citado = contexto.get("quotedMessage") or {}
        texto_citado = citado.get("conversation") or (citado.get("extendedTextMessage") or {}).get("text")
        if isinstance(texto_citado, str) and texto_citado:
            return f"{texto}\n<external_data>\n{texto_citado}\n</external_data>"
        return texto
    if es_nota_de_voz(message):
        return ""

    tipos = [
        name
        for name, value in message.model_dump(by_alias=True).items()
        if value not in (None, {}, "")
    ]
    return f"[sin texto: {', '.join(tipos) or 'vacío'}]"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(settings.webhook_path)
async def webhook(request: Request, background_tasks: BackgroundTasks) -> Any:
    config = get_settings()

    if config.webhook_secret:
        recibido = request.headers.get("x-jarvis-secret", "")
        if not hmac.compare_digest(recibido, config.webhook_secret):
            log.warning("webhook_secreto_invalido")
            return JSONResponse(status_code=401, content={"ok": False, "error": "no_autorizado"})

    cabecera_tamano = request.headers.get("content-length")
    if cabecera_tamano and cabecera_tamano.isdigit() and int(cabecera_tamano) > config.max_webhook_bytes:
        log.warning("webhook_payload_grande")
        return JSONResponse(status_code=413, content={"ok": False, "error": "payload_grande"})

    try:
        body = await request.json()
    except Exception:
        log.warning("webhook_json_invalido")
        return JSONResponse(status_code=400, content={"ok": False, "error": "json_invalido"})

    try:
        payload = EvolutionWebhookPayload.model_validate(body)
    except ValidationError:
        log.warning("webhook_payload_invalido event=%s", body.get("event") if isinstance(body, dict) else "?")
        return JSONResponse(status_code=422, content={"ok": False, "error": "payload_invalido"})

    if payload.event.replace(".", "_").upper() != "MESSAGES_UPSERT":
        log.info("evento_ignorado event=%s", payload.event)
        return {"ok": True}

    data = payload.data
    if data is None or data.key is None or data.key.from_me:
        return {"ok": True}

    texto = extract_text(data.message)
    remoto = data.key.remote_jid or ""
    identificador = data.key.id or ""

    if es_nota_de_voz(data.message):
        log.info(
            "NOTA_VOZ_RECIBIDA instance=%s id=%s de=%s",
            payload.instance or "?",
            identificador or "?",
            mask_phone(remoto),
        )
        background_tasks.add_task(procesar_nota_de_voz, remoto, identificador)
        return {"ok": True}

    log.info(
        "MENSAJE_RECIBIDO instance=%s id=%s de=%s tipo=%s texto=%r",
        payload.instance or "?",
        identificador or "?",
        mask_phone(remoto),
        data.message_type or "?",
        texto[:200],
    )
    background_tasks.add_task(handle_message, remoto, texto, identificador)
    return {"ok": True}
