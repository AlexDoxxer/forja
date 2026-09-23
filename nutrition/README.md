# forja-nutrition

Motor de nutrición opcional de Forja (MASTER_PROMPT §8). Paquete Python **puro y
determinista**: la única E/S permitida es leer `forja_nutrition/data/foods.json`, que se
empaqueta con el propio paquete. Recibe un `NutritionInput` y devuelve objetivos
(`NutritionTarget`) y planes semanales (`MealPlan`) según `contracts/domain.md`.
Depende de la librería estándar, `pydantic`, `pyyaml`, `numpy` y `scipy`.

Propietario: agente `motor-nutricion` (ADR 0002).

```bash
uv sync --project nutrition
cd nutrition && uv run ruff check . && uv run mypy && uv run pytest
```
