# Makefile raíz de Forja.
# Objetivos de calidad (lint, typecheck, test y derivados): propiedad de `arquitecto`.
# Objetivos de operación de §12.3 (bootstrap, up, down, logs, migrate, ingest, backup,
# restore, create-admin): los añade `devops-despliegue` en Fase 3 (ADR 0002).

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

UV ?= uv
UV_RUN := $(UV) run --locked
NPM ?= npm
PY_PACKAGES := engine nutrition backend
GATE := $(UV_RUN) --project engine python scripts/coverage_gate.py

# Directorios de código de producción revisados por la comprobación de marcadores (§15).
PLACEHOLDER_PATHS := backend/app backend/ingest backend/migrations engine/forja_engine \
	nutrition/forja_nutrition frontend/src contracts deploy scripts
PLACEHOLDER_PATTERN := TODO|FIXME|XXX|NotImplementedError|[Ll]orem ipsum

.PHONY: help install lint lint-python lint-frontend lint-contracts lint-placeholders \
	typecheck typecheck-python typecheck-frontend test test-engine test-nutrition \
	test-backend test-backend-unit test-backend-integration test-frontend test-slow e2e \
	format build clean seed-demo \
	bootstrap up down logs migrate ingest backup restore restore-verify create-admin ps

help: ## Muestra esta ayuda
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias exactas (uv.lock y package-lock.json)
	@for p in $(PY_PACKAGES); do $(UV) sync --locked --project $$p; done
	cd frontend && $(NPM) ci

# ---------------------------------------------------------------------------- lint
lint: lint-python lint-frontend lint-contracts lint-placeholders ## Lint de todo el monorepo

lint-python: ## ruff check + ruff format --check en cada paquete Python y scripts/
	@for p in $(PY_PACKAGES); do \
		echo "==> ruff $$p"; \
		(cd $$p && $(UV_RUN) ruff check . && $(UV_RUN) ruff format --check .); \
	done
	@echo "==> ruff scripts"
	$(UV_RUN) --project engine ruff check scripts
	$(UV_RUN) --project engine ruff format --check scripts

lint-frontend: ## ESLint del frontend (0 avisos)
	cd frontend && $(NPM) run --silent lint

lint-contracts: ## Valida contracts/openapi.yaml (OpenAPI 3.1)
	$(UV_RUN) --project backend openapi-spec-validator contracts/openapi.yaml

lint-placeholders: ## Falla si hay marcadores prohibidos (§2.2, §15) en código de producción
	@if grep -rnE '$(PLACEHOLDER_PATTERN)' $(PLACEHOLDER_PATHS); then \
		echo "Marcadores prohibidos encontrados (ver arriba)"; exit 1; \
	else echo "==> sin marcadores prohibidos"; fi

# ----------------------------------------------------------------------- typecheck
typecheck: typecheck-python typecheck-frontend ## mypy --strict + tsc --strict

typecheck-python: ## mypy --strict en cada paquete Python y scripts/
	@for p in $(PY_PACKAGES); do \
		echo "==> mypy $$p"; (cd $$p && $(UV_RUN) mypy); \
	done
	$(UV_RUN) --project engine mypy --strict scripts

typecheck-frontend: ## tsc --noEmit (app, tests y configuración)
	cd frontend && $(NPM) run --silent typecheck

# ---------------------------------------------------------------------------- test
test: test-engine test-nutrition test-backend test-frontend ## Tests + umbrales de cobertura (§2.2)

test-engine: ## Motor de rutinas: 100 % líneas, >= 95 % ramas
	cd engine && $(UV_RUN) pytest -m "not slow"
	$(GATE) engine/coverage.json --lines 100 --branches 95

test-nutrition: ## Motor de nutrición: 100 % líneas, >= 95 % ramas
	cd nutrition && $(UV_RUN) pytest -m "not slow"
	$(GATE) nutrition/coverage.json --lines 100 --branches 95

test-backend: ## Backend + ingesta (unit, contrato e integración con Docker): >= 90 %
	cd backend && $(UV_RUN) pytest -m "not slow"
	$(GATE) backend/coverage.json --lines 90 --branches 90

test-backend-unit: ## Backend sin Docker (unit + contrato), sin umbral de cobertura
	cd backend && $(UV_RUN) pytest -m "not integration and not slow" --cov-fail-under=0

test-backend-integration: ## Solo tests de integración del backend (requiere Docker)
	cd backend && $(UV_RUN) pytest -m "integration and not slow" --cov-fail-under=0

test-frontend: ## Vitest con cobertura >= 85 %
	cd frontend && $(NPM) run --silent test

test-slow: ## Tests marcados como lentos (dataset completo, 1.890 combinaciones)
	cd engine && $(UV_RUN) pytest -m slow --cov-fail-under=0
	cd nutrition && $(UV_RUN) pytest -m slow --cov-fail-under=0
	cd backend && $(UV_RUN) pytest -m slow --cov-fail-under=0

e2e: ## Playwright (Chromium escritorio + WebKit móvil)
	cd frontend && npx playwright test

# ------------------------------------------------------------------------- utilidades
format: ## Formatea Python (ruff) y corrige lo autocorregible de ESLint
	@for p in $(PY_PACKAGES); do (cd $$p && $(UV_RUN) ruff format . && $(UV_RUN) ruff check --fix .); done
	$(UV_RUN) --project engine ruff format scripts
	cd frontend && npx eslint . --fix

build: ## Construye wheels de los paquetes Python y el bundle del frontend
	@for p in $(PY_PACKAGES); do $(UV) build --project $$p --out-dir dist/$$p; done
	cd frontend && $(NPM) run --silent build

seed-demo: ## Datos de demostración (solo desarrollo)
	cd backend && $(UV_RUN) python -m app.cli seed-demo

clean: ## Elimina artefactos generados
	rm -rf dist frontend/dist frontend/coverage frontend/playwright-report frontend/test-results
	find . -name coverage.json -not -path './frontend/node_modules/*' -delete

# ------------------------------------------------------------------ operación (§12.3)
# Objetivos de despliegue de `devops-despliegue`. Requieren Docker con el plugin compose y
# un `.env` (lo crea `make bootstrap` desde `.env.example`).
COMPOSE ?= docker compose --env-file .env -f deploy/docker-compose.yml
export FORJA_COMPOSE := $(COMPOSE)
BACKUP_DIR ?= /var/backups/forja

bootstrap: ## Primera instalación: secretos, imágenes, BD, migraciones, ingesta, admin y arranque
	deploy/scripts/init-env.sh
	$(COMPOSE) build
	$(COMPOSE) up -d --wait db
	$(COMPOSE) --profile tools run --rm ingest
	$(COMPOSE) run --rm api python -m app.cli create-admin
	$(COMPOSE) up -d --wait
	@echo "==> Forja lista en http://localhost:$$(grep -E '^WEB_PORT=' .env | cut -d= -f2-)"

up: ## Construye (si hace falta) y arranca la pila en segundo plano
	$(COMPOSE) up -d --build --wait

down: ## Detiene la pila (conserva volúmenes; usa `down -v` a mano para borrarlos)
	$(COMPOSE) down

ps: ## Estado de los contenedores
	$(COMPOSE) ps

logs: ## Sigue los logs (SERVICE=api para uno solo)
	$(COMPOSE) logs -f --tail=200 $(SERVICE)

migrate: ## Aplica las migraciones de Alembic (con bloqueo consultivo)
	$(COMPOSE) run --rm api true

ingest: ## Migra, descarga el commit fijado del dataset y carga el catálogo
	$(COMPOSE) --profile tools run --rm ingest

create-admin: ## Crea un usuario administrador (pide email y contraseña)
	$(COMPOSE) run --rm -e FORJA_MIGRATE=0 api python -m app.cli create-admin

backup: ## pg_dump -Fc con rotación 7 diarias + 4 semanales en $(BACKUP_DIR)
	BACKUP_DIR=$(BACKUP_DIR) deploy/backup/backup.sh

restore: ## Restaura una copia sobre la BD real: make restore FILE=/ruta/forja.dump
	@test -n "$(FILE)" || { echo "Uso: make restore FILE=/ruta/forja.dump"; exit 2; }
	deploy/backup/restore.sh --yes "$(FILE)"

restore-verify: ## Comprueba una copia restaurándola en una BD efímera: make restore-verify FILE=...
	@test -n "$(FILE)" || { echo "Uso: make restore-verify FILE=/ruta/forja.dump"; exit 2; }
	deploy/backup/restore.sh --verify "$(FILE)"
