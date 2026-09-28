#!/usr/bin/env bash
# Arranca Forja entera de un solo comando: crea .env si falta, construye las imágenes,
# levanta la base de datos, ejecuta la ingesta del catálogo, crea el usuario admin (la
# primera vez) y deja los tres contenedores (db, api, web) en marcha.
#
# Uso: ./start.sh
# Repetible: si ya está todo hecho, solo reconstruye lo que haya cambiado y reinicia.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

COMPOSE=(docker compose --env-file .env -f deploy/docker-compose.yml)
CREDS_FILE=".admin-credentials"

if [ ! -f .env ]; then
  echo "==> Generando .env desde .env.example"
  deploy/scripts/init-env.sh
fi

echo "==> Construyendo imágenes"
"${COMPOSE[@]}" build

echo "==> Levantando la base de datos"
"${COMPOSE[@]}" up -d --wait db

echo "==> Ingesta del catálogo de ejercicios (idempotente)"
"${COMPOSE[@]}" --profile tools run --rm ingest

if [ -f "$CREDS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$CREDS_FILE"
else
  # ".local"/".test"/".invalid" son dominios reservados: el validador de correo del backend
  # los rechaza en /auth/login (aunque el CLI, que no pasa por ese esquema, sí los acepta al
  # crear el usuario). Se usa PUBLIC_BASE_URL del .env, que ya debe ser un dominio real.
  admin_domain="$(grep -E '^PUBLIC_BASE_URL=' .env | cut -d= -f2- | sed -E 's#^https?://##; s#/.*$##; s#:[0-9]+$##')"
  ADMIN_EMAIL="admin@${admin_domain:-localhost}"
  ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)"
fi

echo "==> Creando/verificando el usuario admin"
"${COMPOSE[@]}" run --rm api python -m app.cli create-admin \
  --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" --name Admin

if [ ! -f "$CREDS_FILE" ]; then
  {
    printf 'ADMIN_EMAIL=%q\n' "$ADMIN_EMAIL"
    printf 'ADMIN_PASSWORD=%q\n' "$ADMIN_PASSWORD"
  } > "$CREDS_FILE"
  chmod 600 "$CREDS_FILE"
fi

echo "==> Arrancando la pila completa"
"${COMPOSE[@]}" up -d --wait

WEB_PORT="$(grep -E '^WEB_PORT=' .env | cut -d= -f2-)"
echo
echo "==> Forja lista en http://localhost:${WEB_PORT:-8080}"
echo "==> Admin: $ADMIN_EMAIL / ver contraseña en $CREDS_FILE"
