# forja-backend

API de Forja (FastAPI, prefijo `/api/v1`, contrato en `contracts/openapi.yaml`) y pipeline de
ingesta `backend/ingest/` (CLI `forja-ingest`).

| Ruta | Propietario (ADR 0002) |
|---|---|
| `app/{api,core,db,models,schemas,services,repositories,security,pdf}/`, `migrations/`, `tests/` | `backend-api` |
| `ingest/` | `ingesta-datos` |

```bash
uv sync --project backend
cd backend && uv run ruff check . && uv run mypy && uv run pytest -m "not integration"
cd backend && uv run pytest -m integration   # requiere Docker
```

Configuración exclusivamente por variables de entorno (`.env.example` en la raíz),
validada por `app.core.config.Settings`.
