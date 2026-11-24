---
name: docker-deploy
description: Crea Dockerfile y docker-compose.yml con reinicio automático y volúmenes para la sesión de WhatsApp y la base de datos. Úsala al preparar contenedores o despliegue.
---

## Servicios

- `evolution`: imagen oficial `evoapicloud/evolution-api:latest`, puerto 8080, `AUTHENTICATION_API_KEY` desde `.env`, variables de PostgreSQL y Redis según la documentación oficial.
- `evolution-postgres`: base de datos requerida por Evolution API, con usuario/contraseña/bd desde `.env`.
- `evolution-redis`: caché de sesiones recomendada por la documentación.
- `backend`: build de este repositorio, puerto 8000, `env_file: .env`, `depends_on` con healthchecks, un solo worker de uvicorn.

## Volúmenes

- Volumen nombrado para datos de Evolution API (instancias y media), según las rutas indicadas en la documentación oficial de la versión elegida.
- Volumen nombrado para PostgreSQL y otro para Redis.
- Bind mount `./data:/app/data` para SQLite y audio del agente.

## Reglas

- `restart: unless-stopped` en los cuatro servicios.
- Nunca copiar `.env` dentro de la imagen. Usar `env_file` o secrets de Compose.
- `.dockerignore` debe excluir `.env`, `.git`, `.venv`, `data/` y caches.
- Healthcheck del backend: `GET /health`. Healthcheck de Evolution: `GET /instance/fetchInstances` con la apikey, para no depender de internet.
- Usar `x-logging` con `max-size`/`max-file` y `stop_grace_period` en el backend.
- Verificar siempre las variables de entorno contra `env.config.ts` del repositorio oficial antes de fijarlas en Compose.
- Comandos útiles: `docker compose up -d`, `docker compose logs -f backend`, `docker compose ps`.
