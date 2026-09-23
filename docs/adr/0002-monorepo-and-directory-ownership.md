# ADR 0002 · Monorepo y propiedad de directorios

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
Forja la construyen varios subagentes en paralelo (ORCHESTRATION.md). Sin fronteras claras,
dos agentes pueden editar el mismo fichero y producir conflictos o cambios de contrato
silenciosos. MASTER_PROMPT §4.2 fija la estructura del monorepo.

## Decisión
1. Un único repositorio con la estructura de §4.2 (`backend/`, `engine/`, `nutrition/`,
   `frontend/`, `deploy/`, `contracts/`, `specs/`, `docs/`, `.github/`).
2. **Propiedad de directorios** (solo el propietario escribe; el resto pide cambios en su
   handoff y el orquestador los encarga):

| Zona | Propietario |
|---|---|
| `contracts/`, `docs/adr/`, `docs/TASKS.md` (estructura), `docs/CONTRACT_CHANGES.md` (resoluciones), `ruff.toml`, `.python-version`, `.gitignore`, `scripts/`, objetivos de calidad del `Makefile` (`lint`, `typecheck`, `test*`, `e2e`, `format`, `build`, `clean`, `install`) | `arquitecto` |
| `backend/ingest/`, `specs/overrides/`, `docs/enrichment-report.md`, `docs/names-es-review.md` | `ingesta-datos` |
| `engine/` | `motor-rutinas` |
| `nutrition/` | `motor-nutricion` |
| `backend/` salvo `backend/ingest/` | `backend-api` |
| `frontend/` salvo `frontend/e2e/` | `frontend-ui` |
| `deploy/`, `.github/workflows/` (trabajos de imágenes, Trivy, E2E con compose, backups), `.env.example` (variables nuevas), objetivos de operación del `Makefile` (`bootstrap`, `up`, `down`, `logs`, `migrate`, `ingest`, `backup`, `restore`, `create-admin`), Dockerfiles | `devops-despliegue` |
| `frontend/e2e/`, `tests/` transversales en la raíz, `lighthouserc.json`, `docs/DOD_REPORT.md` | `qa-tests` |
| `docs/reviews/` | `experto-entrenamiento` |
| `docs/SECURITY_REVIEW.md` | `revisor-seguridad` |
| `docs/handoffs/<fase>-<agente>.md` | cada agente el suyo |
| `specs/*.yaml` (tablas del motor) | `motor-rutinas` / `motor-nutricion` (`nutrition.yaml`), cambios revisados por `experto-entrenamiento` |
| `MASTER_PROMPT.md`, `ORCHESTRATION.md`, `CLAUDE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, `docs/USER_GUIDE.md` | orquestador |

3. Zonas compartidas con regla explícita:
   - `backend/app/models/catalog.py`: lo crea `ingesta-datos` si `backend-api` aún no lo ha
     hecho (según `contracts/domain.md`) y a partir de ese momento pasa a `backend-api`.
   - `backend/pyproject.toml` y `backend/uv.lock`: los mantiene `backend-api`; `ingesta-datos`
     puede añadir la entrada `[project.scripts] forja-ingest` y las dependencias que use
     `backend/ingest/`, avisándolo en su handoff.
   - `docs/TASKS.md`: cada agente marca el estado de **sus** tareas; solo el arquitecto y el
     orquestador crean o reasignan tareas.
   - `.github/workflows/ci.yml`: el arquitecto mantiene los trabajos de calidad (lint, tipos,
     unit, integración, cobertura); `devops-despliegue` y `qa-tests` añaden los suyos.
4. Nadie edita fuera de su zona sin pasar por el arquitecto: la petición se registra en el
   handoff (sección «Peticiones a otros agentes») o, si afecta a contratos, en
   `docs/CONTRACT_CHANGES.md`.

## Alternativas
- **Polirepo** (un repo por paquete): aislamiento fuerte pero coordinación de versiones y CI
  mucho más costosa para un proyecto autoalojado de un solo propietario.
- **Propiedad por fichero (CODEOWNERS fino)**: más granular pero difícil de mantener durante la
  construcción; se puede añadir un `CODEOWNERS` derivado de esta tabla si el propietario usa
  revisiones en GitHub/Gitea.

## Consecuencias
- Las ramas por agente (`f1/motor-rutinas`) casi nunca entran en conflicto.
- Los cambios transversales son explícitos y trazables (handoffs, CONTRACT_CHANGES, ADRs).
- El orquestador puede rechazar una entrega que toque ficheros fuera de la zona del agente.
