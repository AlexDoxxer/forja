# Handoff f2-arquitecto-2

## 1. Resumen
CC-0004 aprobado y aplicado; contrato 1.2.0. `make seed-demo` cableado.

## 2. Cambios
- `contracts/domain.md`: v1.2.0; `Food` (+`max_portion_g`, `meal_slots`, `weekly_max`); regla `tolerance_not_met` nueva; `meal_plan.snapshot`; `loadable_in_main` (ADR 0012) en §8; `idempotency_key` ya estaba en §4 (sin cambios).
- `contracts/openapi.yaml`: `info.version` 1.2.0; `Food` con 3 campos requeridos nuevos y ejemplo.
- `docs/CONTRACT_CHANGES.md`: CC-0004 aprobado 2026-09-26.
- `Makefile`: `seed-demo` -> `python -m app.cli seed-demo` (en `backend/`).

## 3. Verificación
openapi-spec-validator OK. Tests de contrato: 453 pasan, 2 fallan por diseño (backend aún en 1.1.0).

## 4. Decisiones
`Food` nuevos campos son `required` (el motor los emite siempre); `weekly_max` admite null.

## 5. Seguimientos
- backend: `API_VERSION` (`app/api/routers/system.py`) y `FastAPI(version=)` (`app/main.py`) a 1.2.0; exportar `Food` con los campos nuevos (nutrition >= 0.2.0 instalado); los 2 tests de contrato deben pasar.
- frontend: `npm run gen:api` y `gen:mocks`.
- orquestador: etiqueta `contracts-v1.2` al fusionar.

## 6. Riesgos
Hasta que backend siga, `test_api_matches_contract` falla en la rama.

## 7. No hecho
No se tocó backend/, frontend/, engine/, nutrition/.
