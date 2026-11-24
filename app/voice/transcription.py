"""Transcripción local en español con faster-whisper."""

import logging
from pathlib import Path

from app.config import get_settings

log = logging.getLogger("jarvis.voice")

_MODELOS: dict[tuple[str, str, str], object] = {}


def _modelo():
    config = get_settings()
    clave = (config.whisper_model, config.whisper_device, config.whisper_compute_type)
    if clave not in _MODELOS:
        from faster_whisper import WhisperModel

        log.info(
            "whisper_cargando modelo=%s dispositivo=%s",
            config.whisper_model,
            config.whisper_device,
        )
        _MODELOS[clave] = WhisperModel(
            config.whisper_model,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
        )
    return _MODELOS[clave]


def transcribir(ruta: Path | str) -> str:
    """Devuelve el texto en español; nunca registra el contenido del audio."""
    modelo = _modelo()
    segmentos, _informacion = modelo.transcribe(
        str(ruta),
        language="es",
        vad_filter=True,
    )
    texto = " ".join(segmento.text.strip() for segmento in segmentos if segmento.text.strip())
    return texto.strip()
