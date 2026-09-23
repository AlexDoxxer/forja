# ADR 0008 · Gestión de paquetes: proyectos uv independientes y npm

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
Hay tres paquetes Python (`engine`, `nutrition`, `backend`) y un frontend Node. Los motores
deben ser puros (ADR 0005) y cada paquete necesita su propio `pyproject.toml` con ruff, mypy
y pytest (§2.2). El entorno de construcción dispone de `uv`, Node 20 y npm; no hay pnpm.

## Decisión
- **Python**: tres **proyectos uv independientes**, cada uno con su `uv.lock` y su `.venv`
  (no un *workspace* uv). El backend declara los motores como dependencias de ruta editables
  en `[tool.uv.sources]`. Python 3.12 fijado en `.python-version`. Backend de construcción
  `hatchling`.
- Configuración de ruff compartida en `ruff.toml` (raíz), extendida por cada paquete
  (`[tool.ruff] extend = "../ruff.toml"`). mypy `--strict` con el plugin de Pydantic en cada
  paquete. `scripts/` se analiza con las herramientas del entorno de `engine`.
- Reproducibilidad: `uv sync --locked` y `uv run --locked` en Makefile y CI (fallan si el lock
  no corresponde al `pyproject.toml`).
- **Frontend**: **npm ≥ 10** con `package-lock.json` (`npm ci` en CI). Se declara en
  `engines`. npm 9 de Debian tiene un fallo del resolvedor (`Cannot read properties of null
  (reading 'edgesOut')`) al instalar dependencias con *peers* opcionales; con npm 10 (el que
  trae `actions/setup-node` para Node 20) no ocurre. `npm run` funciona con ambas versiones.

## Alternativas
- **Workspace uv único**: un solo lock y venv, pero los motores verían todas las dependencias
  del backend y la pureza dejaría de estar garantizada por el entorno.
- **Poetry / pip-tools**: más lentos y sin gestión integrada de la versión de Python.
- **pnpm**: más rápido y estricto, pero no está disponible en el entorno de construcción;
  añadirlo no aporta lo suficiente para un único paquete frontend.

## Consecuencias
- Tres `uv sync` en lugar de uno (segundos con la caché de uv).
- Actualizar un motor no exige tocar el lock del backend salvo que cambien sus dependencias
  (entonces `uv lock --project backend`).
