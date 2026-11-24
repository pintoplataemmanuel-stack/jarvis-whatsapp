# AGENTS.md

Asistente personal "Jarvis" que funciona por WhatsApp.

## Reglas generales

- Prohibido usar o nombrar asistentes o proveedores propietarios ajenos a la configuración abierta de este repositorio. Todo se construye sobre el proveedor LLM configurable.
- Python 3.11+. Framework web: FastAPI. Gestor de dependencias: `uv` o `pip` con `requirements.txt` (`requirements-dev.txt` añade pytest).
- El LLM debe ser intercambiable. Se usa una única interfaz compatible con la API de OpenAI, configurada por `LLM_BASE_URL`, `LLM_API_KEY` y `LLM_MODEL`. Cambiar de proveedor no debe requerir cambios de código.
- Zona horaria por defecto: `America/Bogota`. Idioma de respuesta del agente: español.
- Secretos solo en `.env`. `.env.example` sin valores reales. `.env` incluido en `.gitignore`. Nunca imprimir claves, tokens ni API keys en logs.
- No inventar endpoints ni formatos de payload de Evolution API. Consultar primero la documentación oficial y el repositorio del proyecto. Si algo no está claro, preguntar antes de continuar.
- Antes de dar algo por terminado: ejecutarlo, probarlo y explicar brevemente qué se hizo, porque el objetivo es aprender.
- Trabajar por fases. No pasar a la siguiente sin confirmación explícita.
- El webhook admite la cabecera opcional `x-jarvis-secret` definida en `WEBHOOK_SECRET`. `scripts/setup_evolution.py` la configura en Evolution API v2.
- El backend corre con un solo worker de uvicorn: APScheduler vive en el proceso y duplicarlo enviaría cada mensaje proactivo dos veces.

## Stack

| Capa | Herramienta |
|---|---|
| Lenguaje / API | Python 3.11+, FastAPI, Pydantic v2, uvicorn |
| Puente WhatsApp | Evolution API v2 (integración `WHATSAPP-BAILEYS`) |
| Base de datos del puente | PostgreSQL (según documentación oficial) |
| Cachés / sesión | Redis (opcional, recomendado por la doc) |
| LLM | Cliente compatible con API de OpenAI, vía variables de entorno |
| Agent / tools | Bucle propio de tool calling con registro central de herramientas |
| Memoria | SQLite + resúmenes automáticos, zona `America/Bogota` |
| Voz | Transcripción local con faster-whisper, respuesta de audio opcional |
| Tareas proactivas | APScheduler con `ZoneInfo("America/Bogota")` |
| Pruebas | pytest (`requirements-dev.txt`) |
| Contenedores | Dockerfile + docker-compose.yml con reinicio automático |

## Estructura de carpetas prevista

```text
.
├── AGENTS.md
├── .env.example
├── .env                      # local, ignorado por git
├── .gitignore
├── .dockerignore
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .opencode/
│   └── skills/
│       ├── evolution-api/SKILL.md
│       ├── fastapi-webhook/SKILL.md
│       ├── llm-provider-abstraction/SKILL.md
│       ├── tool-design/SKILL.md
│       ├── sqlite-memory/SKILL.md
│       ├── voice-notes/SKILL.md
│       ├── scheduler/SKILL.md
│       ├── security-hardening/SKILL.md
│       ├── terminal-simulator/SKILL.md
│       └── docker-deploy/SKILL.md
├── data/                     # ignorado por git; se crea en runtime
│   ├── jarvis.db
│   ├── audio/
│   └── qr.png
├── scripts/
│   ├── setup_evolution.py
│   └── preparar_docker.ps1   # Windows: habilita WSL2 y levanta el stack
├── tests/
│   ├── test_fase2.py
│   ├── test_fase3.py
│   ├── test_fase4.py
│   └── test_fase5.py
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── schemas.py
    ├── security.py
    ├── scheduler.py
    ├── simulator.py
    ├── evolution/
    │   ├── __init__.py
    │   └── client.py
    ├── agent/
    │   ├── __init__.py
    │   ├── conversation.py
    │   ├── llm.py
    │   └── runner.py
    ├── tools/
    │   ├── __init__.py
    │   ├── registry.py
    │   └── builtin.py
    ├── memory/
    │   ├── __init__.py
    │   ├── db.py
    │   └── repository.py
    └── voice/
        ├── __init__.py
        ├── handler.py
        ├── transcription.py
        └── tts.py
```

## Skills

Las skills en `.opencode/skills/` son guías cortas de ejecución. Cargar la que corresponda antes de tocar esa capa:

- `evolution-api`: puente, QR, webhooks, parseo y envío.
- `fastapi-webhook`: estructura del backend y respuesta rápida al webhook.
- `llm-provider-abstraction`: cliente único y bucle de tool calling.
- `tool-design`: contrato de herramientas y confirmaciones.
- `sqlite-memory`: esquema y resúmenes.
- `voice-notes`: notas de voz.
- `scheduler`: recordatorios y mensajes proactivos.
- `security-hardening`: lista blanca, rate limit, secreto del webhook y datos externos.
- `terminal-simulator`: pruebas sin WhatsApp.
- `docker-deploy`: contenedores y volúmenes.

## Fases del plan

1. **Paso 0 — Base.** Crear este archivo, las skills, `.gitignore` y `.env.example`. Mostrar el árbol y esperar confirmación.
2. **Fase 1 — El puente.** Levantar Evolution API con su base de datos y el backend con docker-compose. Preparar creación de instancia y QR. El webhook solo registra en consola cada mensaje recibido.
3. **Fase 2 — Eco seguro.** El backend responde repitiendo el texto solo a números de `ALLOWED_NUMBERS`. Añadir simulador de terminal. Pruebas de número no permitido, texto y payload mal formado.
4. **Fase 3 — Agente y herramientas.** LLM intercambiable, bucle de tool calling, registro de herramientas y confirmaciones.
5. **Fase 4 — Memoria y voz.** Historial en SQLite, resúmenes automáticos y notas de voz transcritas en español.
6. **Fase 5 — Proactividad y despliegue (completada).** Scheduler en `America/Bogota`, recordatorios persistentes, hardening del webhook y Dockerfile de producción con un solo worker.

## Verificación rápida

```powershell
python -m pip install -r requirements-dev.txt
$env:PYTHONPATH='E:\whatsApp_chat'; python -m pytest tests -q
python -m compileall -q app scripts tests
python C:\Users\Usuario\AppData\Local\Temp\opencode\validate_step0.py
docker compose config
```

## Despliegue en Windows

Si WSL2 no está habilitado, ejecuta PowerShell como Administrador:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\preparar_docker.ps1
```

El script habilita WSL2, pide confirmación antes de reiniciar, arranca Docker Desktop,
levanta `docker compose up -d --build` y ejecuta `setup_evolution.py` para el QR.
Tras el reinicio, ejecútalo de nuevo: detectará WSL activo y continuará con el stack.
