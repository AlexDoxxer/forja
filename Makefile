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
	format build clean

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

clean: ## Elimina artefactos generados
	rm -rf dist frontend/dist frontend/coverage frontend/playwright-report frontend/test-results
	find . -name coverage.json -not -path './frontend/node_modules/*' -delete
