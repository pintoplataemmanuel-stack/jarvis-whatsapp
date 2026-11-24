---
name: evolution-api
description: Gestiona instancias, QR, webhooks, parseo de mensajes entrantes y envío en Evolution API. Úsala al construir o depurar el puente de WhatsApp; consulta siempre la documentación oficial antes de escribir endpoints.
---

## Fuentes obligatorias

- Documentación oficial: https://doc.evolution-api.com/v2/ y https://doc.evolution-api.com/v1/
- Repositorio: https://github.com/evolution-foundation/evolution-api (la ruta antigua `EvolutionAPI/evolution-api` redirige aquí).
- Leer la versión que se vaya a desplegar antes de fijar rutas o payloads.

## Reglas

- Nunca inventar rutas ni formatos. Si la doc no lo confirma, decirlo y preguntar.
- API key en `EVOLUTION_API_KEY` (.env). Enviarla como header `apikey`. Nunca loguearla.
- Verificar si la versión desplegada es v1 o v2: cambian nombres de campos.

## Crear instancia

- `POST {EVOLUTION_BASE_URL}/instance/create` con header `apikey`.
- v2: body con `instanceName`, `integration: "WHATSAPP-BAILEYS"`, `qrcode: true`, `number` opcional, `token` opcional y objeto `webhook` con `url`, `events`, `byEvents`, `base64`.
- v1: `webhook` es un string y `events`, `webhook_by_events`, `webhook_base64` van al nivel raíz.
- Eventos mínimos: `MESSAGES_UPSERT`, `QRCODE_UPDATED`, `CONNECTION_UPDATE`.

## Conectar y verificar

- `GET {BASE_URL}/instance/connect/{instance}` devuelve el QR (campo `code` o `base64`; también puede aparecer `pairingCode`). No asumir el nombre del campo sin verificar.
- `GET {BASE_URL}/instance/connectionState/{instance}` devuelve `instance.state` (por ejemplo `open`).

## Webhook

- `POST {BASE_URL}/webhook/set/{instance}`.
- v2: `{ "enabled": true, "url": "...", "webhookByEvents": false, "webhookBase64": false, "events": ["MESSAGES_UPSERT", ...] }`.
- v1: misma idea en `snake_case` (`webhook_by_events`, `webhook_base64`, `enabled`, `url`, `events`).
- Si la versión ofrece validación de firma, activarla y verificarla antes de procesar.

## Mensaje entrante `MESSAGES_UPSERT`

- Forma general: `{ "event": "...", "instance": "...", "data": { "key": { "remoteJid", "fromMe", "id" }, "pushName", "message": {...}, "messageType", "messageTimestamp" } }`.
- El campo `event` llega en minúsculas y con punto, por ejemplo `messages.upsert`. Normalizar con `.replace(".", "_").upper()` antes de compararlo con `MESSAGES_UPSERT`. Verificado en prueba local del Fase 1.
- Texto: `message.conversation` o `message.extendedTextMessage.text`.
- Audio: buscar `message.audioMessage` o `message.pttMessage` según la versión.
- Ignorar mensajes con `key.fromMe = true` para no responder eco a nosotros mismos.
- Usar `key.remoteJid` normalizado a solo dígitos como identificador de remitente.
- `data.key.id` sirve como clave de idempotencia.

## Enviar

- Texto v2: `POST {BASE_URL}/message/sendText/{instance}` con `{ "number": "57...", "text": "..." }`.
- Texto v1: `{ "number": "57...", "textMessage": { "text": "..." }, "options": {...} }`.
- `number` con código de país y sin `@s.whatsapp.net` para el envío.
- Para audio o multimedia, buscar la ruta exacta en la sección Media de la documentación de la versión desplegada. No inventarla.
