#!/bin/sh
# Entrypoint de la imagen de Forja: aplica las migraciones (con bloqueo consultivo) cuando
# FORJA_MIGRATE=1 y después ejecuta el comando recibido.
set -eu
if [ "${FORJA_MIGRATE:-0}" = "1" ]; then
    python /app/deploy/migrate_locked.py
fi
exec "$@"
