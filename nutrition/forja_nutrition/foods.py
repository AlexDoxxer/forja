"""Carga de la base de alimentos empaquetada (`data/foods.json`, USDA FoodData Central).

Es la única E/S permitida en tiempo de ejecución del motor de nutrición (ADR 0005).
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib import resources

from forja_nutrition.models import Food

_FOODS_PACKAGE = "forja_nutrition.data"
_FOODS_FILENAME = "foods.json"


@lru_cache(maxsize=1)
def _raw_foods_text() -> str:
    return resources.files(_FOODS_PACKAGE).joinpath(_FOODS_FILENAME).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_foods() -> tuple[Food, ...]:
    """Lee `forja_nutrition/data/foods.json` empaquetado y valida cada alimento."""
    raw_items = json.loads(_raw_foods_text())
    foods = tuple(Food.model_validate(item) for item in raw_items)
    ids = [food.id for food in foods]
    if len(ids) != len(set(ids)):
        raise ValueError("data/foods.json contiene ids de alimento duplicados")
    return foods


@lru_cache(maxsize=1)
def foods_hash() -> str:
    """SHA-256 del contenido exacto de `data/foods.json` (para `MealPlan.foods_hash`)."""
    return hashlib.sha256(_raw_foods_text().encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def foods_by_id() -> dict[str, Food]:
    return {food.id: food for food in load_foods()}
