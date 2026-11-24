---
name: llm-provider-abstraction
description: Implementa un cliente único compatible con la API de OpenAI y un bucle de tool calling con límite, reintentos y manejo de errores. Úsala al conectar el LLM o al añadir herramientas al agente.
---

## Configuración

- Leer solo de entorno: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.
- Instanciar el cliente oficial de OpenAI apuntando `base_url=LLM_BASE_URL` y `api_key=LLM_API_KEY`.
- Nunca imprimir `LLM_API_KEY`. En errores, devolver mensaje genérico en español.

## Interfaz

- `class LLMProvider` con método `chat(messages, tools=None) -> ChatResult`.
- `ChatResult` expone `content: str | None` y `tool_calls: list[ToolCall]`.
- El resto del código solo conoce esta interfaz, nunca al proveedor concreto.

## Bucle de tool calling

1. Llamar al modelo con mensajes + schemas de herramientas.
2. Si hay `tool_calls`, validar argumentos con Pydantic, ejecutar solo tools registradas y añadir los mensajes de tipo `tool` con `tool_call_id`. El mensaje `assistant` previo debe conservar los `tool_calls` crudos (`id`, `type`, `function`). En código async, llamar al proveedor con `asyncio.to_thread`.
3. Repetir como máximo `MAX_TOOL_ITERATIONS` (por defecto 6).
4. Si se agota el límite, responder en español que no se pudo completar y detenerse.
5. Si no hay `tool_calls`, devolver `content`.

## Reintentos y errores

- Reintentar hasta 3 veces con backoff exponencial y jitter ante `429`, `5xx` y timeouts.
- No reintentar errores `4xx` de validación ni errores de autenticación.
- Definir `LLMError` propio y traducirlo a un mensaje breve en español para el usuario.
- Registrar en logs solo tipo de error, modelo y duración, nunca claves ni prompts completos.
