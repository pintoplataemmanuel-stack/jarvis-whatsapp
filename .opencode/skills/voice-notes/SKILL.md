---
name: voice-notes
description: Descarga notas de voz de Evolution API, las transcribe en español y opcionalmente responde con audio. Úsala cuando el webhook reciba mensajes de audio o cuando se active la respuesta por voz.
---

## Recepción

- En el payload `MESSAGES_UPSERT`, detectar `message.audioMessage` o `message.pttMessage` según la versión desplegada (verificar en la documentación).
- Obtener el archivo solo mediante la ruta oficial de descarga de multimedia documentada para esa versión. No inventar la ruta.
- v2 verificado: `POST /chat/getBase64FromMediaMessage/{instance}` con `{"message":{"key":{"id":"..."}},"convertToMp4":false}`. La respuesta trae el campo `base64` (algunas versiones usan `media` o `data`); puede llevar prefijo `data:...;base64,`.
- Guardar temporalmente en `data/audio/<message_id>.ogg`. Crear la carpeta si no existe.
- Borrar el archivo después de transcribir. Nunca loguear el contenido del audio.

## Transcripción

- Usar faster-whisper con `model="small"`, `language="es"` y `vad_filter=True`.
- Si la transcripción sale vacía, responder en español pidiendo que repita el mensaje más cerca del micrófono.
- Pasar el texto transcrito al mismo `handle_message` que usa el texto escrito.

## Respuesta en audio (opcional)

- Generar audio con un proveedor local o configurable, nunca con un servicio no autorizado en `.env`.
- Enviar multimedia solo con el endpoint documentado por Evolution API para esa versión. v2: `POST /message/sendWhatsAppAudio/{instance}` con `{"number":"57...","audio":"<base64>","encoding":true}`; v1: `{"number":"57...","audioMessage":{"audio":"<base64>"},"options":{"encoding":true,"presence":"recording"}}`.
- Antes de activar respuestas en audio por defecto, comprobar que el número está en `ALLOWED_NUMBERS`.
- El texto del audio debe ser el mismo que la respuesta de texto, en español.
