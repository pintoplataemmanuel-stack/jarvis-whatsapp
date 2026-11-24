import re
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from app.config import Settings, get_settings

_CONTADORES: dict[str, deque[float]] = defaultdict(deque)
_BLOQUEO = Lock()
VENTANA_SEGUNDOS = 60


def normalize_phone(value: str | None) -> str:
    """Deja solo dígitos: 57300...@s.whatsapp.net -> 573001112233."""
    return re.sub(r"\D", "", value or "")


def mask_phone(value: str | None) -> str:
    digits = normalize_phone(value)
    return f"***{digits[-4:]}" if digits else "desconocido"


def allowed_numbers(settings: Settings | None = None) -> set[str]:
    config = settings or get_settings()
    return {normalize_phone(item) for item in config.allowed_numbers_raw.split(",") if item.strip()}


def is_allowed(phone: str, settings: Settings | None = None) -> bool:
    actual = normalize_phone(phone)
    return bool(actual) and actual in allowed_numbers(settings)


def permitir_mensaje(phone: str, settings: Settings | None = None) -> bool:
    """Límite de mensajes por minuto y por número. No afecta a otros números."""
    config = settings or get_settings()
    limite = config.max_messages_per_minute
    if limite <= 0:
        return True

    numero = normalize_phone(phone)
    ahora = monotonic()
    with _BLOQUEO:
        cola = _CONTADORES[numero]
        while cola and ahora - cola[0] >= VENTANA_SEGUNDOS:
            cola.popleft()
        if len(cola) >= limite:
            return False
        cola.append(ahora)
        return True


def reiniciar_limites() -> None:
    """Solo para pruebas y reinicios controlados."""
    with _BLOQUEO:
        _CONTADORES.clear()


def sanitizar_texto(texto: str | None, max_caracteres: int | None = None) -> str:
    """Elimina caracteres de control y limita el tamaño del texto entrante."""
    limite = max_caracteres or get_settings().max_message_chars
    crudo = texto or ""
    limpio = "".join(caracter if caracter.isprintable() or caracter in "\n\t" else " " for caracter in crudo)
    return limpio.strip()[:limite]
