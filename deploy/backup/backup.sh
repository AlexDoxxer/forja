#!/usr/bin/env bash
# Copia de seguridad de la base de datos de Forja (MASTER_PROMPT §12.3).
#   pg_dump -Fc dentro del contenedor `db`, con rotación: 7 diarias + 4 semanales.
# Los medios NO se respaldan: se regeneran con `make ingest` (commit fijado).
#
# Variables:
#   BACKUP_DIR      destino (por defecto /var/backups/forja)
#   FORJA_COMPOSE   comando compose (por defecto: docker compose --env-file .env -f deploy/docker-compose.yml)
#   KEEP_DAILY / KEEP_WEEKLY   copias a conservar (7 / 4)
#   FORJA_BACKUP_WEEKLY=1      fuerza la copia semanal (por defecto: los domingos)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/forja}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
COMPOSE="${FORJA_COMPOSE:-docker compose --env-file $ROOT/.env -f $ROOT/deploy/docker-compose.yml}"

umask 077
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"

stamp="$(date +%Y-%m-%d_%H%M%S)"
target="$BACKUP_DIR/daily/forja-$stamp.dump"
tmp="$target.partial"
trap 'rm -f "$tmp"' EXIT

# El usuario y la base se leen del propio contenedor (sin contraseñas en el host).
# shellcheck disable=SC2016  # las variables se expanden dentro del contenedor
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner' >"$tmp"

# Verificación: el volcado debe ser legible y contener el esquema.
if ! $COMPOSE exec -T db pg_restore --list <"$tmp" >/dev/null; then
    echo "backup: el volcado no es válido" >&2
    exit 1
fi
mv "$tmp" "$target"
echo "backup: $target ($(du -h "$target" | cut -f1))"

if [ "${FORJA_BACKUP_WEEKLY:-0}" = "1" ] || [ "$(date +%u)" = "7" ]; then
    weekly="$BACKUP_DIR/weekly/forja-$(date +%G-W%V).dump"
    cp -f "$target" "$weekly"
    echo "backup: semanal $weekly"
fi

rotate() { # rotate <dir> <keep>
    local dir="$1" keep="$2"
    # Los nombres llevan fecha: el orden lexicográfico inverso es el orden por antigüedad.
    find "$dir" -maxdepth 1 -name 'forja-*.dump' -printf '%f\n' | sort -r | tail -n +"$((keep + 1))" |
        while read -r old; do
            rm -f -- "$dir/$old"
            echo "backup: rotada $dir/$old"
        done
}
rotate "$BACKUP_DIR/daily" "$KEEP_DAILY"
rotate "$BACKUP_DIR/weekly" "$KEEP_WEEKLY"
