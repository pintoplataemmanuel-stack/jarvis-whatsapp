---
name: scheduler
description: Programa recordatorios y mensajes proactivos con APScheduler usando America/Bogota. Úsala al crear app/scheduler.py o al añadir tareas automáticas como resumen matutino y cierre diario.
---

## Configuración

- Usar `AsyncIOScheduler` de APScheduler, iniciado desde el `lifespan` de FastAPI.
- Zona horaria: `zoneinfo.ZoneInfo("America/Bogota")`. Guardar en SQLite siempre en UTC ISO 8601 y convertir al programar.
- Leer la zona desde `TIMEZONE` con valor por defecto `America/Bogota`.
- El backend corre con **un solo worker** de uvicorn: APScheduler vive en el proceso y duplicarlo enviaría cada mensaje dos veces.

## Tareas

- Resumen al despertar: 07:00 (`resumen_matutino`).
- Cierre del día: 21:00 (`cierre_diario`).
- Revisión de `scheduled_jobs` cada minuto (`recordatorios`).
- Recordatorios creados por el usuario con la herramienta `programar_recordatorio`: guardar en `scheduled_jobs` con `id`, `due_at` (UTC), `phone` y `payload`.
- Enviar mensajes usando el mismo `EvolutionClient` del resto del proyecto.

## Reglas

- Evitar duplicados con `last_sent_at` y un `job_id` estable; `guardar_job` usa `INSERT OR IGNORE`.
- Si WhatsApp no está conectado, dejar el job pendiente y reintentar en el siguiente minuto; no perder el recordatorio.
- Al reiniciar el proceso, los trabajos pendientes se recargan automáticamente desde SQLite.
- Números fuera de `ALLOWED_NUMBERS`: eliminar el job y no enviar nada.
- `detener_scheduler` debe tolerar un event loop ya cerrado y limpiar la referencia global.
- Logs: solo `job_id`, `phone` enmascarado y resultado. Nunca secretos ni contenido completo.
- Toda respuesta proactiva va en español.
