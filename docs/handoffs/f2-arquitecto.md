# Handoff f2-arquitecto

## Resumen
Aprobados CC-0001, CC-0002 y CC-0003; contrato **1.1.0**. Nuevo ADR 0011 y test que mantiene idénticas las dos copias de `nutrition.yaml`.

## Ficheros tocados
`contracts/openapi.yaml`, `contracts/domain.md`, `docs/CONTRACT_CHANGES.md`, `docs/adr/0011-nutrition-tables-single-source.md`, `docs/adr/README.md`, `backend/tests/contract/test_nutrition_tables_sync.py`, este handoff.

## Decisiones
- `Allergen` pasa a 8 valores (`peanuts`); `PlanWarningCode` +`excluded_exercise`, `avoided_exercise`, `unknown_exercise`; `exercise_secondary_muscle.position smallint not null`.
- ADR 0011: `specs/nutrition.yaml` es la fuente; la copia empaquetada se verifica por test (comparación byte a byte), no se genera.
- `test_openapi_contract.py` no codifica estos valores ni la versión: sin cambios necesarios.

## Cómo verificar
`cd backend && uv run pytest tests/contract -q --no-cov` (380 passed; el umbral de cobertura global falla al ejecutar solo el subconjunto, es esperado).

## Métricas
380 tests de contrato en verde, ruff limpio. No se ejecutó la suite completa (modo rápido).

## Riesgos/pendientes
- El orquestador debe etiquetar `contracts-v1.1`.
- Al editar `specs/nutrition.yaml` hay que copiarlo al paquete o el test falla.

## Peticiones a otros agentes
- motor-nutricion: añadir `peanuts` a `Allergen` en modelos y etiquetar `cacahuete` y `mantequilla_cacahuete` en `foods.json`.
- motor-rutinas: emitir los tres códigos nuevos en `ops.py::_exercise_violations`.
- backend-api / ingesta-datos: `position` ya implementada; alinear el esquema exportado y regenerar el cliente del frontend (frontend-ui).
