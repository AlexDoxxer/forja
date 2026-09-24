"""Plan de comidas semanal (MASTER_PROMPT §8.3): plantillas, selección sembrada, gramos por
mínimos cuadrados no negativos acotados (`scipy.optimize.lsq_linear`), redondeo y
re-verificación de tolerancias.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import lsq_linear

from forja_nutrition import __version__
from forja_nutrition.energy import calculate_target, notice
from forja_nutrition.foods import foods_hash, load_foods
from forja_nutrition.models import (
    FoodCategory,
    FoodMacroRole,
    MacroDeviation,
    MacroTotals,
    Meal,
    MealItem,
    MealPlan,
    MealPlanDay,
    MealPlanOutcome,
    MealSlot,
    NutritionInput,
    NutritionNoticeCode,
)
from forja_nutrition.seeding import effective_seed
from forja_nutrition.tables import RoundingTable, load_nutrition_tables

if TYPE_CHECKING:
    from collections.abc import Iterable

    from forja_nutrition.models import Food

_ROLE_ORDER: tuple[FoodMacroRole, ...] = (
    FoodMacroRole.protein,
    FoodMacroRole.carb,
    FoodMacroRole.produce,
    FoodMacroRole.fat,
)
# Categorías que la plantilla mediterránea puede seleccionar automáticamente; condiments y
# beverages quedan fuera de la selección de comidas (siguen en el catálogo para intercambios
# y en la lista de la compra si aparecen por otra vía), evitando p. ej. cerveza como "carb".
_MEAL_ELIGIBLE_CATEGORIES: frozenset[FoodCategory] = frozenset(
    {
        FoodCategory.fruits,
        FoodCategory.vegetables,
        FoodCategory.legumes,
        FoodCategory.grains,
        FoodCategory.bakery,
        FoodCategory.dairy,
        FoodCategory.eggs,
        FoodCategory.meat,
        FoodCategory.fish_seafood,
        FoodCategory.plant_protein,
        FoodCategory.nuts_seeds,
        FoodCategory.fats_oils,
    }
)
_DAYS_PER_WEEK = 7
_BASE_SELECTION_WEIGHT = 10.0
_REPEAT_PENALTY_PER_USE = 3.0
_DISLIKED_WEIGHT_FACTOR = 0.2
_MIN_SELECTION_WEIGHT = 0.5
_MAX_PORTION_MULTIPLIER = 6.0
_MIN_TYPICAL_PORTION_FOR_BOUNDS = 30.0


def _role_order() -> tuple[FoodMacroRole, ...]:
    return _ROLE_ORDER


def meal_eligible_categories() -> frozenset[FoodCategory]:
    """Categorías que la plantilla mediterránea puede elegir (reusado por `swap.py`)."""
    return _MEAL_ELIGIBLE_CATEGORIES


def _eligible(
    food: Food, nutrition_input: NutritionInput, allergens: set[object], excluded: set[str]
) -> bool:
    if food.category not in _MEAL_ELIGIBLE_CATEGORIES:
        return False
    if food.id in excluded:
        return False
    if nutrition_input.diet_type not in food.diet_types:
        return False
    return not (set(food.allergens) & allergens)


def _selection_weight(food: Food, usage_counts: dict[str, int], disliked: set[str]) -> float:
    weight = _BASE_SELECTION_WEIGHT - _REPEAT_PENALTY_PER_USE * usage_counts.get(food.id, 0)
    if food.id in disliked:
        weight *= _DISLIKED_WEIGHT_FACTOR
    return max(weight, _MIN_SELECTION_WEIGHT)


def select_food(
    *,
    role: FoodMacroRole,
    foods: tuple[Food, ...],
    nutrition_input: NutritionInput,
    allergens: set[object],
    excluded: set[str],
    disliked: set[str],
    usage_counts: dict[str, int],
    rng: random.Random,
) -> Food | None:
    candidates = [
        food
        for food in foods
        if food.macro_role == role and _eligible(food, nutrition_input, allergens, excluded)
    ]
    if not candidates:
        return None
    weights = [_selection_weight(food, usage_counts, disliked) for food in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def build_meal_candidates(
    *,
    foods: tuple[Food, ...],
    nutrition_input: NutritionInput,
    allergens: set[object],
    excluded: set[str],
    disliked: set[str],
    usage_counts: dict[str, int],
    rng: random.Random,
) -> list[Food]:
    # Cada alimento tiene un único `macro_role` de entre los cuatro de `_ROLE_ORDER`, así que
    # recorrer los cuatro roles cubre exactamente el conjunto de alimentos elegibles: no hace
    # falta una segunda pasada "de repesca" ignorando el rol.
    chosen: list[Food] = [
        food
        for role in _role_order()
        if (
            food := select_food(
                role=role,
                foods=foods,
                nutrition_input=nutrition_input,
                allergens=allergens,
                excluded=excluded,
                disliked=disliked,
                usage_counts=usage_counts,
                rng=rng,
            )
        )
        is not None
    ]
    if not chosen:
        raise ValueError(
            "No hay ningún alimento compatible con la dieta, alérgenos y exclusiones "
            "indicadas; revisa excluded_food_ids/allergens."
        )
    return chosen


def round_grams(grams: float, food: Food, rounding: RoundingTable) -> tuple[float, int | None]:
    if food.unit_grams is not None:
        units = round(grams / food.unit_grams)
        if units < 1 and grams > 0:
            units = 1
        return units * food.unit_grams, units if units > 0 else None
    step = rounding.grams_step
    rounded = round(grams / step) * step
    return rounded, None


def nutrients_for(food: Food, grams: float) -> MacroTotals:
    factor = grams / 100.0
    per_100g = food.per_100g
    return MacroTotals(
        kcal=max(per_100g.kcal * factor, 0.0),
        protein_g=max(per_100g.protein_g * factor, 0.0),
        fat_g=max(per_100g.fat_g * factor, 0.0),
        carbs_g=max(per_100g.carbs_g * factor, 0.0),
        fiber_g=max(per_100g.fiber_g * factor, 0.0),
    )


def solve_grams(
    foods: list[Food],
    kcal_target: float,
    protein_target: float,
    fat_target: float,
    carbs_target: float,
) -> list[float]:
    """Gramos por alimento vía mínimos cuadrados no negativos acotados (§8.3)."""
    a_matrix = np.array(
        [
            [f.per_100g.kcal / 100.0 for f in foods],
            [f.per_100g.protein_g / 100.0 for f in foods],
            [f.per_100g.fat_g / 100.0 for f in foods],
            [f.per_100g.carbs_g / 100.0 for f in foods],
        ]
    )
    b_vector = np.array([kcal_target, protein_target, fat_target, carbs_target])
    upper = np.array(
        [
            max(f.typical_portion_g * _MAX_PORTION_MULTIPLIER, _MIN_TYPICAL_PORTION_FOR_BOUNDS)
            for f in foods
        ]
    )
    lower = np.zeros(len(foods))
    result = lsq_linear(a_matrix, b_vector, bounds=(lower, upper))
    return [max(float(x), 0.0) for x in result.x]


def build_meal(
    *,
    slot: MealSlot,
    foods: tuple[Food, ...],
    nutrition_input: NutritionInput,
    allergens: set[object],
    excluded: set[str],
    disliked: set[str],
    usage_counts: dict[str, int],
    rng: random.Random,
    kcal_target: float,
    protein_target: float,
    fat_target: float,
    carbs_target: float,
    rounding: RoundingTable,
) -> Meal:
    candidates = build_meal_candidates(
        foods=foods,
        nutrition_input=nutrition_input,
        allergens=allergens,
        excluded=excluded,
        disliked=disliked,
        usage_counts=usage_counts,
        rng=rng,
    )
    grams_solution = solve_grams(candidates, kcal_target, protein_target, fat_target, carbs_target)

    items: list[MealItem] = []
    for food, raw_grams in zip(candidates, grams_solution, strict=True):
        grams, units = round_grams(raw_grams, food, rounding)
        usage_counts[food.id] = usage_counts.get(food.id, 0) + 1
        if grams <= 0:
            continue
        items.append(
            MealItem(
                food_id=food.id,
                name_es=food.name_es,
                grams=grams,
                units=units,
                nutrients=nutrients_for(food, grams),
            )
        )

    if not items:
        # Ningún alimento sobrevivió al redondeo (comida muy pequeña, p. ej. un snack de
        # baja proporción calórica): se conserva el candidato principal con una ración mínima.
        main_food = candidates[0]
        grams = main_food.unit_grams if main_food.unit_grams is not None else rounding.grams_step
        units = 1 if main_food.unit_grams is not None else None
        items.append(
            MealItem(
                food_id=main_food.id,
                name_es=main_food.name_es,
                grams=grams,
                units=units,
                nutrients=nutrients_for(main_food, grams),
            )
        )

    totals = sum_macro_totals(item.nutrients for item in items)
    return Meal(slot=slot, items=tuple(items), totals=totals)


def sum_macro_totals(totals_iter: Iterable[MacroTotals]) -> MacroTotals:
    kcal = protein = fat = carbs = fiber = 0.0
    for totals in totals_iter:
        kcal += totals.kcal
        protein += totals.protein_g
        fat += totals.fat_g
        carbs += totals.carbs_g
        fiber += totals.fiber_g
    return MacroTotals(kcal=kcal, protein_g=protein, fat_g=fat, carbs_g=carbs, fiber_g=fiber)


def relative_deviation(actual: float, target: float | None) -> float:
    if not target:
        return 0.0
    return (actual - target) / target


def deviation_for(
    totals: MacroTotals, target_kcal: float, protein: float, fat: float, carbs: float
) -> MacroDeviation:
    return MacroDeviation(
        kcal=relative_deviation(totals.kcal, target_kcal),
        protein=relative_deviation(totals.protein_g, protein),
        fat=relative_deviation(totals.fat_g, fat),
        carbs=relative_deviation(totals.carbs_g, carbs),
    )


def plan_week(nutrition_input: NutritionInput, week_start: date) -> MealPlanOutcome:
    """API pública del motor (`contracts/domain.md` §6.3): plan xor bloqueo."""
    target = calculate_target(nutrition_input)
    if target.blocked:
        return MealPlanOutcome(plan=None, block=target.block)

    assert target.target_kcal is not None  # noqa: S101 (invariante de NutritionTarget)
    assert target.protein_g is not None  # noqa: S101
    assert target.fat_g is not None  # noqa: S101
    assert target.carbs_g is not None  # noqa: S101

    tables = load_nutrition_tables()
    foods = load_foods()
    seed = effective_seed(nutrition_input)
    rng = random.Random(seed)  # noqa: S311 (PRNG determinista, no criptográfico)
    usage_counts: dict[str, int] = {}

    slots = tables.meal_templates[nutrition_input.meals_per_day]
    fractions = tables.meal_kcal_split[nutrition_input.meals_per_day]
    allergens: set[object] = set(nutrition_input.allergens)
    excluded = set(nutrition_input.excluded_food_ids)
    disliked = set(nutrition_input.disliked_food_ids)

    days: list[MealPlanDay] = []
    any_tolerance_exceeded = False
    for day_index in range(_DAYS_PER_WEEK):
        day_date = week_start + timedelta(days=day_index)
        meals = []
        for slot in slots:
            fraction = fractions[slot]
            meal = build_meal(
                slot=slot,
                foods=foods,
                nutrition_input=nutrition_input,
                allergens=allergens,
                excluded=excluded,
                disliked=disliked,
                usage_counts=usage_counts,
                rng=rng,
                kcal_target=target.target_kcal * fraction,
                protein_target=target.protein_g * fraction,
                fat_target=target.fat_g * fraction,
                carbs_target=target.carbs_g * fraction,
                rounding=tables.rounding,
            )
            meals.append(meal)
        totals = sum_macro_totals(m.totals for m in meals)
        deviation = deviation_for(
            totals, target.target_kcal, target.protein_g, target.fat_g, target.carbs_g
        )
        if (
            abs(deviation.kcal) > tables.tolerances.kcal
            or max(abs(deviation.protein), abs(deviation.fat), abs(deviation.carbs))
            > tables.tolerances.macros
        ):
            any_tolerance_exceeded = True
        days.append(
            MealPlanDay(
                day_index=day_index,
                date=day_date,
                meals=tuple(meals),
                totals=totals,
                deviation=deviation,
            )
        )

    notices = list(target.notices)
    if any_tolerance_exceeded:
        notices.append(notice(NutritionNoticeCode.tolerance_not_met))

    plan = MealPlan(
        nutrition_version=__version__,
        foods_hash=foods_hash(),
        seed=seed,
        week_start=week_start,
        diet_type=nutrition_input.diet_type,
        meals_per_day=nutrition_input.meals_per_day,
        target=target,
        days=tuple(days),
        notices=tuple(notices),
    )
    return MealPlanOutcome(plan=plan, block=None)
