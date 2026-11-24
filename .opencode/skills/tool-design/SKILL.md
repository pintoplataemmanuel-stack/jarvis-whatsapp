---
name: tool-design
description: Define el contrato de cada herramienta del agente y exige confirmación antes de acciones destructivas o que envíen información a terceros. Úsala al crear o modificar app/tools.
---

## Contrato

- Nombre `snake_case`, descripción corta en español y JSON Schema con `type`, `properties` y `required`.
- Registro central `TOOL_REGISTRY`: nombre -> callable, schema y flag `requires_confirmation`.
- El LLM solo puede invocar herramientas presentes en el registro. Nunca ejecutar código arbitrario ni shell libre.
- Validar los argumentos con Pydantic antes de ejecutar.
- Devolver resultados pequeños, serializables y sin secretos.

## Confirmación

- Acciones destructivas, envío a terceros, pagos o cambios de configuración requieren `requires_confirmation: true`.
- Flujo: el agente propone la acción con un `confirm_id`, el usuario responde `CONFIRMAR <confirm_id>` desde un número permitido y se ejecuta antes de una expiración corta.
- Guardar confirmaciones pendientes en memoria con `phone`, `confirm_id`, `tool`, `args` y `expires_at` en UTC.
- Si expira o llega de otro número, rechazar y avisar en español.

## Estilo

- Una herramienta = una sola tarea.
- Preferir herramientas puras y fáciles de testear con pytest.
- Documentar cada herramienta en `app/tools/builtin.py` con su schema junto al código.
