---
name: terminal-simulator
description: Permite probar el agente desde la terminal simulando al usuario, sin necesidad de WhatsApp. Úsala durante el desarrollo y en las pruebas de la Fase 2.
---

## Ejecución

- Punto de entrada: `python -m app.simulator` o `python scripts/terminal_simulator.py`.
- Solicitar texto por `input()` y llamar a la misma función `handle_message(phone, text, message_id)` que usa el webhook.
- Número simulado: `SIM_PHONE` de `.env`; si no está, el primer valor de `ALLOWED_NUMBERS`.
- Mostrar `Tú:` y `Jarvis:` en español.

## Comandos

- `/salir`: terminar.
- `/audio <ruta>`: simular una nota de voz usando el mismo pipeline de transcripción.
- `/id <texto>`: fijar un `message_id` personalizado para probar idempotencia.

## Reglas

- No levantar Evolution API ni FastAPI para simular.
- Usar la misma base de datos SQLite que el webhook, o un `DB_PATH` temporal configurable para pruebas aisladas.
- No imprimir secretos. Si el LLM no está configurado, avisar en español y permitir modo eco para la Fase 2.
