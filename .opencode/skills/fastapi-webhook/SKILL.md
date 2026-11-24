---
name: fastapi-webhook
description: Estructura el backend FastAPI del webhook, valida payloads con Pydantic y separa la respuesta rápida del procesamiento en segundo plano. Úsala al crear o modificar app/main.py y los modelos de request.
---

## Estructura

- `app/main.py`: crear la app, healthcheck y registrar routers.
- `app/schemas.py`: modelos Pydantic v2 del payload de Evolution API.
- `app/agent/`: razonamiento y bucle de herramientas.
- `app/tools/`: registro de herramientas.
- `app/memory/`: SQLite y repositorio.

## Reglas del endpoint

- Endpoint `POST /webhook/evolution` (o el que defina `WEBHOOK_PATH` en .env).
- Validar `Content-Type: application/json` y tamaño máximo del body.
- Usar modelos Pydantic con `ConfigDict(extra="ignore")` porque el payload de Evolution varía entre versiones, pero marcar como obligatorios `event`, `data.key.remoteJid` y `data.key.id`.
- Responder `200` con `{"ok": true}` en menos de 1 segundo. Nunca esperar al LLM dentro del request.
- Procesar con `BackgroundTasks` de FastAPI o con una cola `asyncio.Queue` + worker. Un solo punto de entrada `handle_message(phone, text, message_id)`.
- Idempotencia: guardar `message_id` en SQLite antes de procesar; si ya existe, solo devolver OK.
- Loguear `message_id` y número enmascarado. Nunca loguear API keys ni el cuerpo completo si contiene datos sensibles.

## Pruebas

- `pytest` con `TestClient` de FastAPI.
- Cubrir: payload válido, payload mal formado, evento que no es `MESSAGES_UPSERT`, mensaje propio (`fromMe=true`) y número no permitido.
