# Handoff · Fase 2 · motor-nutricion

Rama: `f2/motor-nutricion` (sin fusionar). Zona escrita: `nutrition/**` + este handoff.

## Resumen
Adaptación al contrato 1.1.0 (CC-0002): `Allergen.peanuts`; `cacahuete` y `mantequilla_cacahuete`
etiquetados con él en `foods.json`; la exclusión por alérgeno ya es genérica, así que lo cubre.

## Ficheros tocados
`nutrition/forja_nutrition/{__init__,models}.py`, `data/foods.json`, `nutrition/pyproject.toml`,
`nutrition/uv.lock`, `nutrition/tests/{test_planner,test_swap}.py`, `tests/golden/*.json`.

## Decisiones (y ADRs)
- ADR 0011: `specs/nutrition.yaml` no cambia (CC-0002 no toca tablas); no se edita la copia empaquetada.
- `NUTRITION_VERSION` y paquete 0.1.0 -> 0.1.1 (cambia `foods_hash`); snapshots regenerados.
- `ValueError` sin alimentos elegibles se mantiene: `NutritionBlockReason` sigue sin motivo para ello.

## Cómo verificar
`cd nutrition && uv run ruff check . && uv run mypy && uv run pytest -m "not slow"`

## Métricas
191 tests en verde (+2), 100 % líneas y ramas, ruff y mypy --strict sin errores (modo rápido: sin `slow`).

## Riesgos/pendientes
Etiquetas de alérgenos pendientes de revisión del experto (F1b-EXP-06). Los planes guardados con
`foods_hash` antiguo dejarán de coincidir (esperado).

## Peticiones a otros agentes
- backend-api y frontend-ui: exponer «cacahuete» (`peanuts`) en el selector de alérgenos.
