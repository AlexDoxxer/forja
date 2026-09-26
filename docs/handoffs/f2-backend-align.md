# Handoff f2-backend-align (backend-api)

## 1. Resumen
Backend alineado con contrato 1.2.0 / nutrition 0.2.0 / engine 0.2.0. Rama `f2/backend-align`.

## 2. Cambios
- `API_VERSION` (`app/api/routers/system.py`) y `FastAPI(version=)` (`app/main.py`) a 1.2.0.
- `schemas/api.py` `Food`: `max_portion_g`, `meal_slots`, `weekly_max` (requeridos); `GET /foods` los serializa desde el modelo del motor.

## 3. Verificado sin cambios
- `meal_plan.snapshot` valida con `nm.MealPlan` 0.2.0; `tolerance_not_met` viene del motor (el backend solo reenvía avisos).
- `POST /sync` ya devuelve `server_id` en `session_upsert` applied/duplicate/superseded.
- `finish` ya es idempotente: una sesión completada conserva su primer `finished_at`.
- `uv lock --check` en sincronía.

## 4. Tests
Contrato + `test_nutrition*`: 465 passed (modo rápido). ruff y `mypy --strict app` limpios. Los dos tests de contrato ahora pasan.

## 5. Pendiente
La tabla `food` no persiste los campos nuevos (el catálogo sale del motor); no hace falta migración. Suite completa/slow sin ejecutar.

## 6. Contrato
Sin cambios de contrato.

## 7. Riesgos
`schemas/api.py` es generado por datamodel-codegen; se editó a mano igual que el contrato. Regenerar dará el mismo resultado.
