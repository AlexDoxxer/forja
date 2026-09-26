# Handoff · Fase 2 · backend-api

Rama: `f2/backend-api` (sin fusionar). Contrato 1.1.0 (CC-0001/2/3) integrado; `backend/uv.lock`
regenerado con `forja-engine 0.1.1` y `forja-nutrition 0.1.1` (no hay constantes de versión
del motor en los tests del backend).

## Resumen

API completa de `contracts/openapi.yaml` (59 rutas, 100 % de §9 + ampliaciones de ADR 0009),
modelos §5 y migración Alembic reversible `0001`, seguridad §11 y los dos motores integrados.

- **Capas**: `api/routers` (finos) → `services` (reglas y SQL) → `repositories` (consultas del
  catálogo). Esquemas Pydantic **generados desde el contrato** (`datamodel-codegen`) en
  `app/schemas/api.py`.
- **Auth** (ADR 0003): argon2id, sesión opaca hasheada, cookies `__Host-forja_session`/`_csrf`,
  CSRF de doble envío en toda escritura (middleware), expiración deslizante, rotación en login y
  cambio de contraseña, `GET /auth/check` 204/401 sin cuerpo, rate limit en memoria (429 +
  `Retry-After`), cabeceras (CSP, HSTS…), límite de cuerpo (413), `X-Request-ID`, logs JSON sin PII.
- **Motores**: `load_tables()` al crear la app; catálogo `ExerciseCard[]` en memoria (ordenando
  `secondary_muscles` por `position`), invalidado tras ingesta y por huella barata cada 30 s
  (multi-worker); `ValidationError` y `PlanOperationError` ⇒ 422; nutrición calcula `age_years`,
  emite `missing_profile_data` y pasa un lunes como `week_start`.
- **Programas**: persistencia plan = vista previa; `regenerate-day`, `swap`, `PUT days/{id}`
  (`rebalance_after_edit` + `validate_plan`; violaciones ⇒ `422 plan_invalid` con `violations`;
  `warnings` recalculados en el programa). Solo se reescriben los días modificados (conservan ids).
- **Entreno**: sesiones/series con `Idempotency-Key` (tabla `idempotency_key`, 422/409),
  `POST /sync` (applied/duplicate/superseded/rejected, SAVEPOINT por operación, tombstones),
  récords (e1RM, mejor peso, volumen) recalculados desde las series vigentes, estadísticas y
  `GET /sessions/next` con `progression.suggest`.
- **Exportes**: PDF WeasyPrint (Jinja2, `URLFetcher` limitado a `MEDIA_ROOT`, atribución de Gym
  visual en el pie de **cada** página) e ICS RFC 5545 (líneas plegadas, UID estable).
- **Cuenta**: export/import JSON idempotente (ids derivados con uuid5), borrado con contraseña.
- **Admin**: ajustes (prevalecen sobre el entorno), usuarios (409 `last_admin`), ingesta en
  tarea de fondo con `ingest_run` estable + `audit_log`.

## Ficheros tocados

`backend/app/**` (api, core, db, models, repositories, schemas, security, services, pdf, cli.py,
main.py), `backend/migrations/**`, `backend/alembic.ini`, `backend/tests/{integration,contract}`,
`backend/pyproject.toml` (deps `email-validator`, dev `pypdf`, ruff/coverage), `backend/uv.lock`.
Sin cambios en `contracts/` ni fuera de `backend/` salvo `docs/`.

## Decisiones

1. Modelos: `TimestampMixin` con `eager_defaults`; `Base` sigue en `models/catalog.py` (la usa la ingesta).
2. `meal_plan.snapshot` (JSONB, columna añadida a §4.4): plan completo del motor como fuente de
   lectura; `meal_plan_item` es su proyección relacional. Pendiente de reflejar en `domain.md`.
3. Sin `relationship()` el ORM no ordena inserciones por FK: `RowBatch` hace flush por niveles.
4. Manual programs (`generator_input = null`): se validan con un `GeneratorInput` sintético
   (gimnasio completo, ≥ 4 semanas de relleno solo para el motor). `regenerate-day`/`swap` ⇒
   409 `program_not_generated`.
5. `apply_to_all_weeks` en `PUT days`: copia la estructura y re-periodiza series (por
   `volume_ratio`) y RIR de cada semana (el motor no ofrece esa operación).
6. Importación entre cuentas: `set_log.client_uuid` es único global ⇒ en otra cuenta se deriva
   un uuid5 estable (repetir la importación no duplica).
7. `GET /sessions/next`: `rest_day` si ya se entrenó hoy; fecha = próximo día de la semana del
   día del programa (o reparto uniforme si no tiene `weekday`); zona horaria = UTC (no se guarda zona).
8. Ingesta desde la API: fila `queued` propia; al terminar se copia el resultado de la fila que
   crea `load_catalog` y se borra esta (id estable para el cliente). Flag de módulo `FULL_DATASET`
   (los tests usan un dataset reducido).
9. Tests de contrato: `tests/contract/test_api_matches_contract.py` compara rutas, `operationId`,
   parámetros, códigos de estado, cuerpos y forma de los esquemas compartidos; además **todas las
   respuestas JSON de los tests de integración se validan contra el esquema del contrato**.
10. Coverage con `concurrency = ["greenlet", "thread"]` (necesario con SQLAlchemy async).

## Cómo verificar

```bash
cd backend && uv sync --locked
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest -m "not slow"                  # requiere Docker (testcontainers-postgres)
uv run pytest tests/contract --no-cov        # contrato
uv run alembic upgrade head                  # DATABASE_URL en el entorno
uv run python -m app.cli seed-demo           # usuario demo@forja.local (solo desarrollo)
uv run python -m app.cli create-admin --email a@b.co --name Admin
uvicorn --factory app.main:create_app        # API en /api/v1 (docs desactivados)
```

Ejemplos `httpie` (HTTPS; la cookie `__Host-` exige `Secure`):

```bash
http --session=forja GET :8000/api/v1/auth/csrf
http --session=forja POST :8000/api/v1/auth/login X-CSRF-Token:$CSRF email=demo@forja.local password=brasa-y-yunque-2026
http --session=forja POST :8000/api/v1/generator/preview X-CSRF-Token:$CSRF goal=hypertrophy days_per_week:=4 \
  sex=female experience=intermediate session_minutes:=60 equipment:='{"preset":"full_gym","items":[]}'
```

## Métricas

| Métrica | Valor |
|---|---|
| `pytest -m "not slow"` (backend + ingesta) | 671 passed, 4 deseleccionados (`slow`) en ~135 s |
| Cobertura backend+ingesta | **96,9 %** (líneas+ramas combinadas; umbral 90) |
| `ruff check/format`, `mypy --strict` | 0 errores (95 ficheros) |
| Contrato | 75 comprobaciones de `test_api_matches_contract` + validación de cada respuesta JSON de los tests de integración |

## Riesgos/pendientes

- Rendimiento §9 (`pytest-benchmark`, marcado `slow`) no ejecutado en modo rápido; `GET /exercises`
  y `preview` se probaron funcionalmente (motor p95 21 ms según su handoff).
- Rate limit y caché de catálogo son por proceso (con 2 workers los límites se duplican).
- Límite de cuerpo por `Content-Length` (sin `Content-Length` lo aplica nginx).
- Zona horaria de estadísticas/calendario = UTC.
- `create-admin`/`seed-demo` viven en `python -m app.cli`; `make seed-demo` y `make create-admin`
  (Makefile del arquitecto/devops) deben invocarlo.
- La imagen debe incluir `specs/` (o `FORJA_SPECS_DIR`) y `git`; la ingesta desde la API necesita red.
- Contraseñas comunes: lista local mínima (~120 entradas); ampliar con una lista mayor si se desea.

## Peticiones a otros agentes

- **arquitecto**: reflejar `meal_plan.snapshot` y `idempotency_key` en `domain.md`; `make seed-demo`.
- **devops**: `alembic upgrade head` en el arranque/`make migrate`; `uvicorn --factory app.main:create_app`.
- **frontend**: las cookies requieren HTTPS o `localhost`; enviar `X-CSRF-Token` en toda escritura
  (incluidos login/registro tras `GET /auth/csrf`).
