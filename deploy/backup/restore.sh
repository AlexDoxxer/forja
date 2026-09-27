#!/usr/bin/env bash
# Restauración de una copia de Forja (MASTER_PROMPT §12.3).
#
#   restore.sh --verify <dump>         restaura en una BD EFÍMERA (contenedor postgres:16-alpine
#                                      desechable) y comprueba tablas y versión de Alembic.
#                                      No toca la instalación real. Es lo que ejecuta la CI.
#   restore.sh --yes <dump>            SUSTITUYE la base de datos real por el volcado.
#                                      Detiene api y web durante la operación.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="${FORJA_COMPOSE:-docker compose --env-file $ROOT/.env -f $ROOT/deploy/docker-compose.yml}"
PG_IMAGE="${PG_IMAGE:-postgres:16-alpine}"

usage() {
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

[ "$#" -eq 2 ] || usage
mode="$1"
dump="$2"
[ -r "$dump" ] || {
    echo "restore: no se puede leer $dump" >&2
    exit 1
}

verify_ephemeral() {
    local name="forja-restore-verify-$$"
    trap 'docker rm -f "$name" >/dev/null 2>&1 || true' RETURN
    docker run -d --rm --name "$name" -e POSTGRES_PASSWORD=verify -e POSTGRES_DB=forja_verify \
        "$PG_IMAGE" >/dev/null
    for _ in $(seq 1 60); do
        docker exec "$name" pg_isready -U postgres -d forja_verify >/dev/null 2>&1 && break
        sleep 1
    done
    docker exec "$name" pg_isready -U postgres -d forja_verify >/dev/null
    # Los volcados usan --no-owner: se restauran con el superusuario efímero.
    docker exec -i "$name" pg_restore -U postgres -d forja_verify --no-owner --exit-on-error <"$dump"
    local tables version exercises
    tables="$(docker exec "$name" psql -U postgres -d forja_verify -Atc \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")"
    version="$(docker exec "$name" psql -U postgres -d forja_verify -Atc \
        "SELECT version_num FROM alembic_version")"
    exercises="$(docker exec "$name" psql -U postgres -d forja_verify -Atc \
        "SELECT count(*) FROM exercise" 2>/dev/null || echo 0)"
    echo "restore --verify: OK · tablas=$tables · alembic=$version · ejercicios=$exercises"
    [ "$tables" -gt 0 ] && [ -n "$version" ]
}

restore_live() {
    echo "restore: deteniendo api y web"
    $COMPOSE stop web api
    # shellcheck disable=SC2016  # se expande dentro del contenedor
    $COMPOSE exec -T db sh -c '
        set -e
        psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
            -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\" WITH (FORCE)" \
            -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\""
    '
    # shellcheck disable=SC2016
    $COMPOSE exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' <"$dump"
    echo "restore: base de datos restaurada; arrancando api y web"
    $COMPOSE up -d api web
}

case "$mode" in
--verify) verify_ephemeral ;;
--yes) restore_live ;;
*) usage ;;
esac
