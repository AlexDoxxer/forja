#!/usr/bin/env bash
# Prepara `.env` para el despliegue: lo crea desde `.env.example` si falta y rellena los
# secretos vacíos (SECRET_KEY, POSTGRES_PASSWORD, DATABASE_URL). Idempotente: nunca
# sobrescribe un valor ya presente.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"

if [ ! -f "$ENV_FILE" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    echo "init-env: creado $ENV_FILE desde .env.example"
fi
chmod 600 "$ENV_FILE"

get() { # get KEY -> valor actual (vacío si no existe o está vacío)
    { grep -E "^$1=" "$ENV_FILE" || true; } | tail -n1 | cut -d= -f2-
}

set_if_empty() { # set_if_empty KEY VALUE
    local key="$1" value="$2"
    if [ -n "$(get "$key")" ]; then
        return
    fi
    if grep -qE "^$key=" "$ENV_FILE"; then
        sed -i "s|^$key=.*|$key=$value|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$value" >>"$ENV_FILE"
    fi
    echo "init-env: generado $key"
}

random_hex() { openssl rand -hex "$1"; }

set_if_empty SECRET_KEY "$(random_hex 32)"
set_if_empty POSTGRES_PASSWORD "$(random_hex 32)"
set_if_empty DATABASE_URL \
    "postgresql+asyncpg://$(get POSTGRES_USER):$(get POSTGRES_PASSWORD)@db:5432/$(get POSTGRES_DB)"
