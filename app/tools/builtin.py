import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app.agent.conversation import limpiar
from app.config import get_settings
from app.memory import repository
from app.security import normalize_phone, sanitizar_texto
from app.tools.registry import Tool, register


class SumarArgs(BaseModel):
    a: float
    b: float


class BorrarArgs(BaseModel):
    phone: str
    motivo: str | None = None


class RecordatorioArgs(BaseModel):
    phone: str
    mensaje: str
    hora: str
    dia: str | None = None


def hora_local(_args: dict) -> str:
    ahora = datetime.now(ZoneInfo("America/Bogota"))
    return f"Fecha y hora en Bogotá: {ahora.strftime('%Y-%m-%d %H:%M:%S')}"


def sumar(args: dict) -> str:
    return f"Resultado: {args['a'] + args['b']:g}"


def borrar_historial(args: dict) -> str:
    limpiar(args["phone"])
    return "Historial de conversación borrado."


def programar_recordatorio(args: dict) -> str:
    config = get_settings()
    zona = ZoneInfo(config.timezone)
    dia = datetime.strptime(args["dia"], "%Y-%m-%d").date() if args.get("dia") else datetime.now(zona).date()
    hora = datetime.strptime(args["hora"], "%H:%M").time()
    momento = datetime.combine(dia, hora, tzinfo=zona)
    if momento <= datetime.now(zona):
        return "Ese momento ya pasó. Indica una hora futura en America/Bogota."

    identificador = uuid.uuid4().hex[:8]
    repository.guardar_job(
        identificador,
        normalize_phone(args["phone"]),
        sanitizar_texto(args["mensaje"]),
        momento.astimezone(timezone.utc).isoformat(timespec="seconds"),
    )
    return f"Recordatorio {identificador} programado para el {dia.isoformat()} a las {hora:%H:%M} en {config.timezone}."


register(
    Tool(
        name="obtener_hora_local",
        description="Devuelve la fecha y hora actual en la zona America/Bogota. No necesita argumentos.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=hora_local,
    )
)

register(
    Tool(
        name="sumar_numeros",
        description="Suma dos números decimales y devuelve el resultado.",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "Primer número"},
                "b": {"type": "number", "description": "Segundo número"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
        handler=sumar,
        args_model=SumarArgs,
    )
)

register(
    Tool(
        name="borrar_historial",
        description="Borra el historial de conversación de este número. Acción destructiva: requiere confirmación explícita del usuario.",
        parameters={
            "type": "object",
            "properties": {
                "motivo": {"type": "string", "description": "Motivo opcional del borrado"}
            },
            "additionalProperties": False,
        },
        handler=borrar_historial,
        requires_confirmation=True,
        args_model=BorrarArgs,
    )
)

register(
    Tool(
        name="programar_recordatorio",
        description="Programa un mensaje para este mismo número en una fecha y hora de America/Bogota. Formato dia YYYY-MM-DD (opcional) y hora HH:MM.",
        parameters={
            "type": "object",
            "properties": {
                "mensaje": {"type": "string", "description": "Texto del recordatorio en español"},
                "hora": {"type": "string", "description": "Hora en HH:MM, zona America/Bogota"},
                "dia": {"type": "string", "description": "Fecha en YYYY-MM-DD; por defecto hoy"},
            },
            "required": ["mensaje", "hora"],
            "additionalProperties": False,
        },
        handler=programar_recordatorio,
        args_model=RecordatorioArgs,
    )
)
