#!/bin/sh
# El bind mount ./data:/app/data se crea como root:root en algunos hosts.
# Si arrancamos como root, corregimos permisos y luego ejecutamos la app como app.
set -e

if [ "$(id -u)" = "0" ]; then
    chown -R app:app /app/data 2>/dev/null || true
    chmod -R u+rwX /app/data 2>/dev/null || true
    exec python - "$@" <<'PY'
import os
import pwd
import sys

usuario = pwd.getpwnam("app")
os.setgroups([])
os.setgid(usuario.pw_gid)
os.setuid(usuario.pw_uid)
os.execvp(sys.argv[1], sys.argv[1:])
PY
fi

exec "$@"
