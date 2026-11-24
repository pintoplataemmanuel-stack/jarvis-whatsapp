---
name: sqlite-memory
description: Define el esquema SQLite para conversaciones, hechos y resúmenes, con resumen automático cuando crece el contexto. Úsala al crear app/memory o al persistir mensajes del agente.
---

## Esquema mínimo

- `messages(id TEXT PRIMARY KEY, phone TEXT, direction TEXT, content TEXT, created_at TEXT)` para idempotencia por `key.id`.
- `conversation(phone TEXT, role TEXT, content TEXT, tokens INTEGER, meta TEXT, created_at TEXT)` para el historial. `meta` guarda en JSON los `tool_calls` y `tool_call_id` del bucle de herramientas; `created_at` es autoincremental por `id` para conservar el orden.
- `facts(phone TEXT, key TEXT, value TEXT, updated_at TEXT, PRIMARY KEY(phone, key))`.
- `summaries(phone TEXT, period TEXT, text TEXT, created_at TEXT, PRIMARY KEY(phone, period))`.
- `scheduled_jobs(id TEXT PRIMARY KEY, phone TEXT, payload TEXT, due_at TEXT, last_sent_at TEXT)`.

## Reglas

- Ruta desde `DB_PATH`, por defecto `data/jarvis.db`. Crear la carpeta `data/` si no existe.
- Usar `PRAGMA journal_mode=WAL` y `PRAGMA foreign_keys=ON`.
- Guardar fechas en UTC ISO 8601. Convertir a `America/Bogota` solo para mostrar o programar con `zoneinfo.ZoneInfo("America/Bogota")`.
- Nunca guardar API keys, tokens ni secretos en la base de datos.

## Resumen automático

- Cuando `SUM(tokens)` o el número de mensajes supere un umbral configurable, resumir los mensajes antiguos con el LLM intercambiable.
- Reemplazar el historial antiguo por el resumen y conservar los últimos N mensajes tal cual.
- El resumen debe conservar hechos, decisiones y pendientes, en español.
- Guardar el resumen en `summaries` antes de borrar mensajes del historial activo. Usar `period = 'historial'` fijo con `ON CONFLICT ... DO UPDATE` para que solo exista un resumen vigente por número; `cargar_historial` lo antepone como mensaje `system`.
- Verificado en Fase 4: `resumir_si_necesario()` comprueba umbrales antes de llamar al LLM, por lo que no consume tokens en conversaciones cortas.
