"""Intercambio de alimento dentro de una comida, conservando sus macros (MASTER_PROMPT §8.3).

El alimento de sustitución debe pertenecer a la misma `FoodCategory`, ser compatible con la
dieta y no contener alérgenos declarados; sus gramos se recalculan para acercarse a las kcal
del alimento sustituido.
"""

from __future__ import annotations

import hashlib
import random
from typing import TYPE_CHECKING

from forja_nutrition.energy import notice
from forja_nutrition.foods import foods_by_id
from forja_nutrition.models import (
    Meal,
    MealItem,
    MealPlan,
    MealPlanDay,
    MealSlot,
    NutritionInput,
    NutritionNoticeCode,
)
from forja_nutrition.planner import (
    deviation_for,
    meal_eligible_categories,
    nutrients_for,
    round_grams,
    sum_macro_totals,
)
from forja_nutrition.tables import load_nutrition_tables

if TYPE_CHECKING:
    from forja_nutrition.models import Food, NutritionTarget


def _is_candidate(
    food: Food,
    *,
    original: Food,
    nutrition_input: NutritionInput,
    excluded: set[str],
    allergens: set[object],
) -> bool:
    if food.id == original.id:
        return False
    if food.category != original.category:
        return False
    if food.category not in meal_eligible_categories():
        return False
    if food.id in excluded:
        return False
    if nutrition_input.diet_type not in food.diet_types:
        return False
    return not (set(food.allergens) & allergens)


def _pick_replacement(
    original: Food, nutrition_input: NutritionInput, seed: int, slot: MealSlot | None = None
) -> Food:
    allergens: set[object] = set(nutrition_input.allergens)
    excluded = set(nutrition_input.excluded_food_ids)
    catalog = foods_by_id().values()
    candidates = [
        food
        for food in catalog
        if _is_candidate(
            food,
            original=original,
            nutrition_input=nutrition_input,
            excluded=excluded,
            allergens=allergens,
        )
    ]
    if not candidates:
        raise ValueError(
            f"No hay ningún alimento de la categoría '{original.category.value}' compatible "
            "con la dieta, los alérgenos y las exclusiones indicadas para sustituir "
            f"'{original.id}'."
        )
    disliked = set(nutrition_input.disliked_food_ids)
    # idoneidad por comida (B7): se prefieren sustitutos aptos para esa comida y no rechazados
    fitting = [food for food in candidates if slot is None or slot in food.meal_slots]
    fitting = fitting or candidates
    preferred = [food for food in fitting if food.id not in disliked]
    pool = preferred or fitting
    rng = random.Random(seed)  # noqa: S311 (PRNG determinista, no criptográfico)
    return rng.choice(sorted(pool, key=lambda food: food.id))


def _swap_seed(plan_seed: int, day_index: int, meal: MealSlot, food_id: str) -> int:
    """Semilla estable entre procesos (no usa `hash()`, que depende de PYTHONHASHSEED)."""
    key = f"{plan_seed}:{day_index}:{meal.value}:{food_id}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:6], "big")


def _locate(plan: MealPlan, day_index: int, meal: MealSlot, food_id: str) -> tuple[int, int]:
    if not 0 <= day_index < len(plan.days):
        raise ValueError(f"day_index fuera de rango: {day_index}")
    day = plan.days[day_index]
    meal_index = next((i for i, m in enumerate(day.meals) if m.slot == meal), None)
    if meal_index is None:
        raise ValueError(f"La comida '{meal.value}' no existe en el día {day_index}")
    target_meal = day.meals[meal_index]
    item_index = next(
        (i for i, item in enumerate(target_meal.items) if item.food_id == food_id), None
    )
    if item_index is None:
        raise ValueError(f"El alimento '{food_id}' no está en esa comida")
    return meal_index, item_index


def _resolve_replacement(
    *,
    original_food: Food,
    nutrition_input: NutritionInput,
    replacement_food_id: str | None,
    seed: int,
    slot: MealSlot | None = None,
) -> Food:
    catalog = foods_by_id()
    if replacement_food_id is None:
        return _pick_replacement(original_food, nutrition_input, seed, slot)
    replacement = catalog.get(replacement_food_id)
    if replacement is None:
        raise ValueError(f"'{replacement_food_id}' no existe en la base de alimentos")
    allergens: set[object] = set(nutrition_input.allergens)
    excluded = set(nutrition_input.excluded_food_ids)
    if not _is_candidate(
        replacement,
        original=original_food,
        nutrition_input=nutrition_input,
        excluded=excluded,
        allergens=allergens,
    ):
        raise ValueError(
            f"'{replacement_food_id}' no es un sustituto válido de '{original_food.id}' "
            "(misma categoría, dieta compatible, sin alérgenos declarados ni exclusiones)"
        )
    return replacement


def _build_replacement_item(original_item: MealItem, replacement: Food) -> MealItem:
    if replacement.per_100g.kcal > 0:
        raw_grams = original_item.nutrients.kcal / replacement.per_100g.kcal * 100.0
    else:
        raw_grams = original_item.grams

    rounding = load_nutrition_tables().rounding
    grams, units = round_grams(raw_grams, replacement, rounding)
    if grams <= 0:
        grams = replacement.unit_grams or rounding.grams_step
        units = 1 if replacement.unit_grams is not None else None

    return MealItem(
        food_id=replacement.id,
        name_es=replacement.name_es,
        grams=grams,
        units=units,
        nutrients=nutrients_for(replacement, grams),
    )


def _replace_item_in_meal(meal_obj: Meal, item_index: int, new_item: MealItem) -> Meal:
    new_items = list(meal_obj.items)
    new_items[item_index] = new_item
    return meal_obj.model_copy(
        update={
            "items": tuple(new_items),
            "totals": sum_macro_totals(item.nutrients for item in new_items),
        }
    )


def _rebuild_day(
    day: MealPlanDay, meal_index: int, new_meal: Meal, target: NutritionTarget
) -> MealPlanDay:
    new_meals = list(day.meals)
    new_meals[meal_index] = new_meal
    new_totals = sum_macro_totals(m.totals for m in new_meals)
    new_deviation = deviation_for(
        new_totals,
        target.target_kcal or 0.0,
        target.protein_g or 0.0,
        target.fat_g or 0.0,
        target.carbs_g or 0.0,
    )
    return day.model_copy(
        update={"meals": tuple(new_meals), "totals": new_totals, "deviation": new_deviation}
    )


def swap_food(  # noqa: PLR0917 (firma fijada por contracts/domain.md sec 6.3)
    plan: MealPlan,
    nutrition_input: NutritionInput,
    day_index: int,
    meal: MealSlot,
    food_id: str,
    replacement_food_id: str | None,
) -> MealPlan:
    """API pública del motor (`contracts/domain.md` §6.3)."""
    meal_index, item_index = _locate(plan, day_index, meal, food_id)
    day = plan.days[day_index]
    target_meal = day.meals[meal_index]
    original_item = target_meal.items[item_index]

    original_food = foods_by_id().get(food_id)
    if original_food is None:
        raise ValueError(f"'{food_id}' no existe en la base de alimentos")

    swap_seed = _swap_seed(plan.seed, day_index, meal, food_id)
    replacement = _resolve_replacement(
        original_food=original_food,
        nutrition_input=nutrition_input,
        replacement_food_id=replacement_food_id,
        seed=swap_seed,
        slot=meal,
    )

    new_item = _build_replacement_item(original_item, replacement)
    new_meal = _replace_item_in_meal(target_meal, item_index, new_item)
    new_day = _rebuild_day(day, meal_index, new_meal, plan.target)

    new_days = list(plan.days)
    new_days[day_index] = new_day

    notices = list(plan.notices)
    if not any(n.code == NutritionNoticeCode.swap_macros_adjusted for n in notices):
        notices.append(notice(NutritionNoticeCode.swap_macros_adjusted))

    return plan.model_copy(update={"days": tuple(new_days), "notices": tuple(notices)})
