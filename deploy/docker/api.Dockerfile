# syntax=docker/dockerfile:1.7
# Imagen de la API y de la ingesta de Forja (MASTER_PROMPT §12.1).
# Contexto de construcción: la raíz del repositorio (`docker build -f deploy/docker/api.Dockerfile .`).
# Etapa 1: uv resuelve e instala las dependencias congeladas (backend/uv.lock) en un venv.
# Etapa 2: python:3.12-slim solo con el venv, specs/, alembic, git y las librerías de WeasyPrint.

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.12.18

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
# Los motores son dependencias por ruta (`../engine`, `../nutrition`); se instalan como
# ruedas (--no-editable) para que el venv sea autosuficiente.
COPY engine ./engine
COPY nutrition ./nutrition
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/
COPY backend/app ./backend/app
COPY backend/ingest ./backend/ingest
RUN --mount=type=cache,target=/root/.cache/uv \
    cd backend && uv sync --locked --no-dev --no-editable

FROM python:${PYTHON_VERSION}-slim AS runtime
# WeasyPrint (Pango/HarfBuzz/Fontconfig), git (servicio `ingest`) y tini como init.
# `apt-get upgrade` aplica los parches de seguridad ya publicados para Debian
# trixie sin esperar un nuevo rebuild de la etiqueta `python:3.12-slim`
# (defensa en profundidad para HIGH/CRITICAL corregibles detectados por Trivy).
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        git tini libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 \
        fonts-dejavu-core shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --user-group --home-dir /home/forja --create-home forja \
    && install -d -o forja -g forja /var/lib/forja/media

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FORJA_SPECS_DIR=/app/specs \
    MEDIA_ROOT=/var/lib/forja/media \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    GUNICORN_WORKERS=2

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY specs ./specs
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY deploy/scripts/migrate_locked.py ./deploy/migrate_locked.py
COPY deploy/scripts/api-entrypoint.sh /usr/local/bin/api-entrypoint

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD ["python", "-c", "import sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=4).status == 200 else 1)"]
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/api-entrypoint"]
CMD ["sh", "-c", "exec gunicorn 'app.main:create_app()' --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS} --worker-tmp-dir /dev/shm --timeout 60 --graceful-timeout 20 --keep-alive 5 --access-logfile - --access-logformat '%(s)s %(m)s %(U)s %(L)ss'"]
