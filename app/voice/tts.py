"""Síntesis local opcional para responder con audio.

Requiere `pyttsx3` instalado (y `espeak` en Linux). Si no está disponible,
el llamador debe caer a texto. Nunca usa un servicio externo configurado
fuera de `.env`.
"""

import base64
import logging
from pathlib import Path

from app.config import get_settings

log = logging.getLogger("jarvis.tts")


def sintetizar(texto: str) -> str:
    """Devuelve el audio en base64. Lanza ImportError si falta pyttsx3."""
    import pyttsx3

    config = get_settings()
    directorio = Path(config.db_path).parent / "audio"
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / "respuesta.wav"

    motor = pyttsx3.init()
    motor.save_to_file(texto, str(ruta))
    motor.run_and_wait()
    datos = ruta.read_bytes()
    ruta.unlink(missing_ok=True)
    return base64.b64encode(datos).decode("ascii")
