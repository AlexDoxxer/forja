# ADR 0001 · Stack tecnológico

- **Estado**: Aceptado · **Fecha**: 2026-09-23 · **Autor**: arquitecto

## Contexto
MASTER_PROMPT §4.1 fija el stack. Forja es una PWA autoalojada para uso personal/familiar en
un LXC de Proxmox con recursos modestos (2 vCPU, 2–4 GB RAM), con un motor determinista y
offline, sin IA en tiempo de ejecución, y con requisitos estrictos de tipos y cobertura (§2.2).

## Decisión
Se adopta el stack de §4.1 sin cambios y se fijan versiones mínimas:

| Capa | Tecnología y versión mínima |
|---|---|
| Lenguaje backend/motores | Python **3.12** (`.python-version`; `requires-python = ">=3.12,<3.13"`) |
| API | FastAPI ≥ 0.115, Pydantic v2 (≥ 2.9), pydantic-settings, Uvicorn + Gunicorn |
| Datos | SQLAlchemy 2.0 async + `asyncpg`, Alembic, PostgreSQL **16** con `unaccent` y `pg_trgm` |
| Motores | `forja_engine` (stdlib + pydantic + pyyaml), `forja_nutrition` (+ numpy + scipy) |
| PDF | WeasyPrint + Jinja2 |
| Ingesta | Typer (CLI `forja-ingest`), jsonschema, Pillow (solo lectura de dimensiones) |
| Frontend | React **18.3**, TypeScript **5.7** estricto, Vite 6, TanStack Router/Query, Zustand, Tailwind, Radix, dnd-kit, Recharts, vite-plugin-pwa, idb, i18next |
| Cliente API | `openapi-typescript` + `openapi-fetch` generados desde `contracts/openapi.yaml` |
| Tests | pytest, pytest-asyncio, hypothesis, httpx, testcontainers · Vitest 4, Testing Library, MSW · Playwright |
| Calidad | ruff, mypy `--strict`, ESLint 9 (typescript-eslint `strictTypeChecked`), tsc estricto |
| Runtime Node | Node **20.19+** con npm **10+** (ADR 0008) |
| Infra | Docker Compose, nginx, Proxmox LXC Debian 12 |

Solo `frontend-ui` añade al `package.json` las librerías de UI de la tabla cuando las usa;
la Fase 0 instala únicamente React y el utillaje de calidad.

## Alternativas
- **Django/DRF**: más baterías incluidas, pero peor encaje con Pydantic como contrato común
  entre API y motores, y async menos maduro.
- **Node/TypeScript en backend**: un solo lenguaje, pero `scipy.optimize.lsq_linear` y el
  ecosistema científico de Python son clave para nutrición.
- **SQLite**: más simple de operar, pero sin `unaccent`/`pg_trgm` ni concurrencia de escritura
  robusta para `/sync`.
- **Vitest 3**: descartado por un aviso de seguridad moderado en `@vitest/mocker` corregido en
  4.1.11; Vitest 5 exige Node 22.

## Consecuencias
- Un único lenguaje de dominio (Python) para API y motores; los DTOs Pydantic se comparten.
- Los motores quedan aislados en paquetes con sus propias dependencias (ADR 0005, ADR 0008).
- Cualquier cambio de stack requiere un ADR nuevo aprobado por el arquitecto.
