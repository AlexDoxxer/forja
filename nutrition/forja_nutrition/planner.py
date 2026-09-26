"""Plan de comidas semanal (MASTER_PROMPT §8.3): plantillas, selección sembrada, gramos por
mínimos cuadrados no negativos acotados (`scipy.optimize.lsq_linear`), redondeo y
re-verificación de tolerancias.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import lsq_linear

from forja_nutrition import __version__
from forja_nutrition.energy import calculate_target, notice
from forja_nutrition.foods import foods_by_id, foods_hash, load_foods
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
from forja_nutrition.tables import NutritionTables, RoundingTable, load_nutrition_tables

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
# Intentos por día con selección de alimentos distinta hasta cumplir kcal, proteína y techo.
_DAY_ATTEMPTS = 10
_TRIM_MAX_STEPS = 60
# Con exceso sobre el techo de grasa (duro) se sigue intentando hasta este límite.
_DAY_ATTEMPTS_FAT_CEILING = 40
_BASE_SELECTION_WEIGHT = 10.0
_REPEAT_PENALTY_PER_USE = 3.0
_DISLIKED_WEIGHT_FACTOR = 0.2
_MIN_SELECTION_WEIGHT = 0.5
_SAME_DAY_REPEAT_USES = 4  # un alimento ya usado hoy pesa como si llevara 4 usos extra (N3)
# Preferencias gastronómicas (C12): el aceite de oliva domina en la cocina española; el coco
# (grasa saturada casi pura) y el girasol se ofrecen raramente.
_SELECTION_BIAS: dict[str, float] = {
    "aceite_oliva": 4.0,
    "aceite_coco": 0.25,
    "aceite_girasol": 0.25,
}
# Porción mínima útil (B7): un ítem por debajo de esta fracción de la porción típica se elimina.
_MIN_PORTION_FRACTION = 0.30
# El ítem «grasa» de una comida se omite si el resto ya aporta esta fracción de su grasa (B7).
_FAT_ITEM_OPTIONAL_COVERAGE = 0.70
# Ponderación del error de grasa por encima del objetivo (decisión 5): x2 y, si la comida rebasa
# el techo del 35 % kcal, reintento con x3.
_FAT_OVER_WEIGHTS: tuple[float, ...] = (2.0, 3.0)
# Último recurso al pulir el día: el techo de grasa pesa mucho más que el resto de errores.
_FAT_OVER_WEIGHT_LAST_RESORT = 12.0
_PROTECTIVE_PROTEIN_FACTOR = 0.93
_PROTECTIVE_FAT_PCT = 0.32
_FAT_KCAL_PER_GRAM = 9.0
_FAT_TOLERANCE_G = 1e-6
_ROW_IMPORTANCE = np.array([20.0, 10.0, 4.0, 4.0])  # 1 / tolerancia relativa (kcal, P, G, HC)
_MIN_ROW_TARGET = 1.0
_FAT_SHARE_FREE = 0.30  # fracción de kcal en grasa a partir de la cual se penaliza la selección
_PROTEIN_DENSITY_REFERENCE = 8.0  # g de proteína por 100 kcal
_MIN_ROW_SHARE = 0.10
_ANCHOR_STRENGTH = 0.25
_KCAL_PER_GRAM_BY_ROW = np.array([1.0, 4.0, 9.0, 4.0])


def _role_order() -> tuple[FoodMacroRole, ...]:
    return _ROLE_ORDER


def meal_eligible_categories() -> frozenset[FoodCategory]:
    """Categorías que la plantilla mediterránea puede elegir (reusado por `swap.py`)."""
    return _MEAL_ELIGIBLE_CATEGORIES


def _eligible(
    food: Food,
    nutrition_input: NutritionInput,
    allergens: set[object],
    excluded: set[str],
    *,
    slot: MealSlot | None = None,
    usage_counts: dict[str, int] | None = None,
) -> bool:
    if food.category not in _MEAL_ELIGIBLE_CATEGORIES:
        return False
    if food.id in excluded:
        return False
    if nutrition_input.diet_type not in food.diet_types:
        return False
    if set(food.allergens) & allergens:
        return False
    if slot is not None and slot not in food.meal_slots:
        return False
    return not (
        food.weekly_max is not None
        and usage_counts is not None
        and usage_counts.get(food.id, 0) >= food.weekly_max
    )


def _selection_weight(food: Food, usage_counts: dict[str, int], disliked: set[str]) -> float:
    weight = _BASE_SELECTION_WEIGHT - _REPEAT_PENALTY_PER_USE * usage_counts.get(food.id, 0)
    if food.id in disliked:
        weight *= _DISLIKED_WEIGHT_FACTOR
    weight *= _SELECTION_BIAS.get(food.id, 1.0)
    if food.macro_role is FoodMacroRole.protein and food.per_100g.kcal > 0:
        # las fuentes proteicas densas (pechuga, atún, claras) hacen alcanzable el objetivo
        density = food.per_100g.protein_g / food.per_100g.kcal * 100.0
        weight *= min(max(density / _PROTEIN_DENSITY_REFERENCE, 0.25), 2.5)
    if food.macro_role is not FoodMacroRole.fat and food.per_100g.kcal > 0:
        # los alimentos no grasos con mucha grasa (tofu, tempeh, embutidos) se ofrecen menos
        # para no empujar el día por encima del techo de grasa
        fat_share = food.per_100g.fat_g * _FAT_KCAL_PER_GRAM / food.per_100g.kcal
        weight *= min(max(1.0 - (fat_share - _FAT_SHARE_FREE) * 2.5, 0.3), 1.0)
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
    slot: MealSlot | None = None,
) -> Food | None:
    candidates = [
        food
        for food in foods
        if food.macro_role == role
        and _eligible(
            food, nutrition_input, allergens, excluded, slot=slot, usage_counts=usage_counts
        )
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
    slot: MealSlot | None = None,
) -> list[Food]:
    """Un alimento por rol apto para la comida `slot` (B7); si ninguno lo es, se relaja la
    idoneidad por comida para no dejar el plan sin alimentos."""
    chosen = _choose_by_role(
        foods=foods,
        nutrition_input=nutrition_input,
        allergens=allergens,
        excluded=excluded,
        disliked=disliked,
        usage_counts=usage_counts,
        rng=rng,
        slot=slot,
    )
    if not chosen and slot is not None:
        chosen = _choose_by_role(
            foods=foods,
            nutrition_input=nutrition_input,
            allergens=allergens,
            excluded=excluded,
            disliked=disliked,
            usage_counts=usage_counts,
            rng=rng,
            slot=None,
        )
    if not chosen:
        raise ValueError(
            "No hay ningún alimento compatible con la dieta, alérgenos y exclusiones "
            "indicadas; revisa excluded_food_ids/allergens."
        )
    return chosen


def _choose_by_role(
    *,
    foods: tuple[Food, ...],
    nutrition_input: NutritionInput,
    allergens: set[object],
    excluded: set[str],
    disliked: set[str],
    usage_counts: dict[str, int],
    rng: random.Random,
    slot: MealSlot | None,
) -> list[Food]:
    # Cada alimento tiene un único `macro_role` de entre los cuatro de `_ROLE_ORDER`, así que
    # recorrer los cuatro roles cubre exactamente el conjunto de alimentos elegibles: no hace
    # falta una segunda pasada "de repesca" ignorando el rol.
    return [
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
                slot=slot,
            )
        )
        is not None
    ]


def round_grams(grams: float, food: Food, rounding: RoundingTable) -> tuple[float, int | None]:
    """Redondea a unidades o al paso de gramos y respeta `food.max_portion_g` (B7)."""
    if food.unit_grams is not None:
        units = round(grams / food.unit_grams)
        if units < 1 and grams > 0:
            units = 1
        units = min(units, max(1, math.floor(food.max_portion_g / food.unit_grams + 1e-9)))
        return units * food.unit_grams, units if units > 0 else None
    step = rounding.grams_step
    rounded = round(grams / step) * step
    cap = math.floor(food.max_portion_g / step + 1e-9) * step
    return min(rounded, cap if cap > 0 else food.max_portion_g), None


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
    *,
    fat_over_weight: float = _FAT_OVER_WEIGHTS[0],
    anchor: list[float] | None = None,
) -> list[float]:
    """Gramos por alimento vía mínimos cuadrados no negativos acotados (§8.3).

    Cada alimento queda acotado por su `max_portion_g`. Si la solución rebasa el objetivo de
    grasa, se resuelve de nuevo ponderando ese error `fat_over_weight` veces (el sobrepaso de
    grasa cuesta más que el defecto). Con `anchor` (gramos previos) se añade una regularización
    débil hacia esos gramos y cada alimento conserva al menos la porción mínima útil.
    """
    a_matrix = np.array(
        [
            [f.per_100g.kcal / 100.0 for f in foods],
            [f.per_100g.protein_g / 100.0 for f in foods],
            [f.per_100g.fat_g / 100.0 for f in foods],
            [f.per_100g.carbs_g / 100.0 for f in foods],
        ]
    )
    targets = np.array([kcal_target, protein_target, fat_target, carbs_target])
    # Filas normalizadas por objetivo y por importancia: kcal (+-5 %) y proteína (+-10 %)
    # pesan más que grasa y carbohidratos, que solo se acercan a su objetivo.
    # (el denominador tiene un suelo proporcional a las kcal: la realimentación puede dejar
    # un macro restante en ~0 y no debe volver infinito su peso)
    denominators = np.maximum(targets, _MIN_ROW_SHARE * kcal_target / _KCAL_PER_GRAM_BY_ROW)
    row_weights = _ROW_IMPORTANCE / np.maximum(denominators, _MIN_ROW_TARGET)
    a_matrix = a_matrix * row_weights[:, None]
    b_vector = targets * row_weights
    upper = np.array([f.max_portion_g for f in foods])
    lower = np.zeros(len(foods))
    if anchor is not None:
        typical = np.array([f.typical_portion_g for f in foods])
        lower = np.minimum(_MIN_PORTION_FRACTION * typical, upper)
        anchor_rows = np.diag(_ANCHOR_STRENGTH / typical)
        anchor_b = _ANCHOR_STRENGTH * np.array(anchor) / typical
    else:
        anchor_rows = np.zeros((0, len(foods)))
        anchor_b = np.zeros(0)
    bounds = (lower, upper)

    def _solve() -> np.ndarray:
        return lsq_linear(
            np.vstack([a_matrix, anchor_rows]),
            np.concatenate([b_vector, anchor_b]),
            bounds=bounds,
            method="bvls",
        ).x

    solution = _solve()
    if float(a_matrix[2] @ solution) > b_vector[2] + _FAT_TOLERANCE_G:
        scale = math.sqrt(fat_over_weight)
        a_matrix[2] *= scale
        b_vector[2] *= scale
        solution = _solve()
    return [max(float(x), 0.0) for x in solution]


def _fat_g(entries: list[tuple[Food, float, int | None]]) -> float:
    return sum(nutrients_for(food, grams).fat_g for food, grams, _ in entries)


def _kcal(entries: list[tuple[Food, float, int | None]]) -> float:
    return sum(nutrients_for(food, grams).kcal for food, grams, _ in entries)


def _solve_and_round(
    foods: list[Food],
    targets: tuple[float, float, float, float],
    rounding: RoundingTable,
    fat_over_weight: float,
) -> list[tuple[Food, float, int | None]]:
    """Resuelve, redondea y elimina ítems menores que la porción mínima útil (re-resolviendo)."""
    pool = list(foods)
    while True:
        raw = solve_grams(pool, *targets, fat_over_weight=fat_over_weight)
        entries = [
            (food, *round_grams(grams, food, rounding))
            for food, grams in zip(pool, raw, strict=True)
        ]
        ratios = [grams / food.typical_portion_g for food, grams, _ in entries]
        worst = min(range(len(entries)), key=lambda i: ratios[i])
        if len(pool) == 1 or ratios[worst] >= _MIN_PORTION_FRACTION:
            return [entry for entry in entries if entry[1] > 0]
        del pool[worst]


def fat_ceiling_g(*, kcal: float, fat_target_g: float, max_pct_kcal: float) -> float:
    """Techo de grasa: `max_pct_kcal` de las kcal, salvo que el propio objetivo ya lo supere
    (el suelo de grasa de seguridad prevalece sobre el techo)."""
    return max(max_pct_kcal * kcal / _FAT_KCAL_PER_GRAM, fat_target_g)


def _fits_fat_ceiling(
    entries: list[tuple[Food, float, int | None]], fat_target: float, max_pct_kcal: float
) -> bool:
    ceiling = fat_ceiling_g(kcal=_kcal(entries), fat_target_g=fat_target, max_pct_kcal=max_pct_kcal)
    return _fat_g(entries) <= ceiling + _FAT_TOLERANCE_G


def _fit_meal(
    candidates: list[Food],
    targets: tuple[float, float, float, float],
    rounding: RoundingTable,
    max_pct_kcal: float,
) -> list[tuple[Food, float, int | None]]:
    """Gramos de la comida: ítem de grasa opcional, sobrepaso de grasa penalizado y techo 35 %."""
    lean = [food for food in candidates if food.macro_role is not FoodMacroRole.fat]
    fat_target = targets[2]
    pools = [candidates]
    if lean and len(lean) < len(candidates):
        lean_entries = _solve_and_round(lean, targets, rounding, _FAT_OVER_WEIGHTS[0])
        if _fat_g(lean_entries) >= _FAT_ITEM_OPTIONAL_COVERAGE * fat_target:
            pools = [lean]
        else:
            pools.append(lean)
    entries: list[tuple[Food, float, int | None]] = []
    for pool in pools:
        for weight in _FAT_OVER_WEIGHTS:
            entries = _solve_and_round(pool, targets, rounding, weight)
            if _fits_fat_ceiling(entries, fat_target, max_pct_kcal):
                return entries
    return entries


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
    fat_max_pct: float,
) -> Meal:
    candidates = build_meal_candidates(
        foods=foods,
        nutrition_input=nutrition_input,
        allergens=allergens,
        excluded=excluded,
        disliked=disliked,
        usage_counts=usage_counts,
        rng=rng,
        slot=slot,
    )
    fitted = _fit_meal(
        candidates, (kcal_target, protein_target, fat_target, carbs_target), rounding, fat_max_pct
    )

    items: list[MealItem] = []
    for food, grams, units in fitted:
        usage_counts[food.id] = usage_counts.get(food.id, 0) + 1
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
        usage_counts[main_food.id] = usage_counts.get(main_food.id, 0) + 1
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


def _fat_over_ceiling(totals: MacroTotals, fat_target_g: float, tables: NutritionTables) -> bool:
    ceiling = fat_ceiling_g(
        kcal=totals.kcal, fat_target_g=fat_target_g, max_pct_kcal=tables.fat.max_pct_kcal
    )
    return totals.fat_g > ceiling + _FAT_TOLERANCE_G


def _day_score(
    totals: MacroTotals, targets: tuple[float, float, float, float], max_pct_kcal: float
) -> float:
    """Puntuación de un día (menor es mejor): error de kcal y proteína en unidades de su
    tolerancia más el exceso sobre el techo de grasa."""
    tolerances = load_nutrition_tables().tolerances
    kcal_error = abs(relative_deviation(totals.kcal, targets[0])) / tolerances.kcal
    protein_error = abs(relative_deviation(totals.protein_g, targets[1])) / tolerances.macros
    ceiling = fat_ceiling_g(kcal=totals.kcal, fat_target_g=targets[2], max_pct_kcal=max_pct_kcal)
    fat_excess = max(totals.fat_g - ceiling, 0.0) / max(ceiling, 1.0)
    return max(kcal_error, protein_error) + 10.0 * fat_excess


def polish_day(
    meals: list[Meal],
    targets: tuple[float, float, float, float],
    rounding: RoundingTable,
    max_pct_kcal: float,
) -> list[Meal]:
    """Reajusta los gramos del día completo (más grados de libertad que cada comida por
    separado) manteniendo los mismos alimentos; solo se acepta si mejora el día."""
    catalog = foods_by_id()
    foods = [catalog[item.food_id] for meal in meals for item in meal.items]
    anchor = [item.grams for meal in meals for item in meal.items]
    current = sum_macro_totals(meal.totals for meal in meals)
    best_score = _day_score(current, targets, max_pct_kcal)
    best = meals
    # Último recurso: apuntar a la parte baja de la tolerancia de proteína y a una grasa por
    # debajo del techo para que el techo duro prevalezca sobre la exactitud de proteína.
    kcal_t, protein_t, fat_t, carbs_t = targets
    protective = (
        kcal_t,
        protein_t * _PROTECTIVE_PROTEIN_FACTOR,
        min(fat_t, _PROTECTIVE_FAT_PCT * kcal_t / _FAT_KCAL_PER_GRAM),
        carbs_t,
    )
    attempts = [(targets, weight) for weight in _FAT_OVER_WEIGHTS]
    attempts += [
        (targets, _FAT_OVER_WEIGHT_LAST_RESORT),
        (protective, _FAT_OVER_WEIGHT_LAST_RESORT),
    ]
    for solve_targets, weight in attempts:
        raw = solve_grams(foods, *solve_targets, fat_over_weight=weight, anchor=anchor)
        rebuilt = _rebuild_meals(meals, foods, raw, rounding)
        totals = sum_macro_totals(meal.totals for meal in rebuilt)
        score = _day_score(totals, targets, max_pct_kcal)
        if score < best_score:
            best, best_score = rebuilt, score
    return best


def trim_fat(meals: list[Meal], fat_target_g: float, tables: NutritionTables) -> list[Meal]:
    """Garantiza el techo de grasa (decisión 5): mientras el día lo rebase, recorta un paso el
    ítem más graso que aún supere su porción mínima útil."""
    catalog = foods_by_id()
    step = tables.rounding.grams_step
    current = meals
    for _ in range(_TRIM_MAX_STEPS):
        totals = sum_macro_totals(meal.totals for meal in current)
        if not _fat_over_ceiling(totals, fat_target_g, tables):
            break
        candidates: list[tuple[float, int, int]] = []
        for m_index, meal in enumerate(current):
            for i_index, item in enumerate(meal.items):
                food = catalog[item.food_id]
                decrement = food.unit_grams if food.unit_grams is not None else step
                floor = min(_MIN_PORTION_FRACTION * food.typical_portion_g, food.max_portion_g)
                if item.grams - decrement >= floor and item.nutrients.fat_g > 0:
                    share = (
                        item.nutrients.fat_g * _FAT_KCAL_PER_GRAM / max(item.nutrients.kcal, 1.0)
                    )
                    candidates.append((share, m_index, i_index))
        if not candidates:
            break
        _, m_index, i_index = max(candidates)
        current = _trim_item(current, catalog, step, m_index, i_index)
    return current


def _trim_item(
    meals: list[Meal], catalog: dict[str, Food], step: float, m_index: int, i_index: int
) -> list[Meal]:
    meal = meals[m_index]
    item = meal.items[i_index]
    food = catalog[item.food_id]
    if food.unit_grams is not None:
        grams = item.grams - food.unit_grams
        units: int | None = round(grams / food.unit_grams)
    else:
        grams = item.grams - step
        units = None
    new_item = item.model_copy(
        update={"grams": grams, "units": units, "nutrients": nutrients_for(food, grams)}
    )
    items = list(meal.items)
    items[i_index] = new_item
    new_meal = meal.model_copy(
        update={"items": tuple(items), "totals": sum_macro_totals(i.nutrients for i in items)}
    )
    result = list(meals)
    result[m_index] = new_meal
    return result


def _rebuild_meals(
    meals: list[Meal], foods: list[Food], raw: list[float], rounding: RoundingTable
) -> list[Meal]:
    rebuilt: list[Meal] = []
    index = 0
    for meal in meals:
        items: list[MealItem] = []
        for item in meal.items:
            food = foods[index]
            grams, units = round_grams(raw[index], food, rounding)
            grams = max(
                grams, min(_MIN_PORTION_FRACTION * food.typical_portion_g, food.max_portion_g)
            )
            if food.unit_grams is None:
                step = rounding.grams_step
                grams = min(math.ceil(grams / step - 1e-9) * step, food.max_portion_g)
            index += 1
            items.append(
                item.model_copy(
                    update={"grams": grams, "units": units, "nutrients": nutrients_for(food, grams)}
                )
            )
        rebuilt.append(
            meal.model_copy(
                update={
                    "items": tuple(items),
                    "totals": sum_macro_totals(i.nutrients for i in items),
                }
            )
        )
    return rebuilt


def _build_day_meals(
    *,
    slots: tuple[MealSlot, ...],
    fractions: dict[MealSlot, float],
    targets: tuple[float, float, float, float],
    foods: tuple[Food, ...],
    nutrition_input: NutritionInput,
    allergens: set[object],
    excluded: set[str],
    disliked: set[str],
    usage_counts: dict[str, int],
    rng: random.Random,
    tables: NutritionTables,
) -> list[Meal]:
    meals: list[Meal] = []
    day_foods: set[str] = set()
    # Realimentación del error: cada comida apunta al reparto de lo que aún falta del
    # objetivo diario (no al reparto fijo), de modo que el redondeo de las primeras
    # comidas se compensa en las siguientes y el día cierra cerca del objetivo.
    remaining = targets
    remaining_fraction = 1.0
    for slot in slots:
        fraction = fractions[slot]
        share = fraction / remaining_fraction
        # Preferir alimentos distintos en el día (N3): los ya usados hoy pierden peso de
        # selección pero siguen siendo elegibles si no hay alternativa.
        view = dict(usage_counts)
        for food_id in day_foods:
            view[food_id] += _SAME_DAY_REPEAT_USES
        meal = build_meal(
            slot=slot,
            foods=foods,
            nutrition_input=nutrition_input,
            allergens=allergens,
            excluded=excluded,
            disliked=disliked,
            usage_counts=view,
            rng=rng,
            kcal_target=max(remaining[0], 0.0) * share,
            protein_target=max(remaining[1], 0.0) * share,
            fat_target=max(remaining[2], 0.0) * share,
            carbs_target=max(remaining[3], 0.0) * share,
            rounding=tables.rounding,
            fat_max_pct=tables.fat.max_pct_kcal,
        )
        meals.append(meal)
        for item in meal.items:
            usage_counts[item.food_id] = usage_counts.get(item.food_id, 0) + 1
            day_foods.add(item.food_id)
        remaining = (
            remaining[0] - meal.totals.kcal,
            remaining[1] - meal.totals.protein_g,
            remaining[2] - meal.totals.fat_g,
            remaining[3] - meal.totals.carbs_g,
        )
        remaining_fraction -= fraction
    polished = polish_day(meals, targets, tables.rounding, tables.fat.max_pct_kcal)
    return trim_fat(polished, targets[2], tables)


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
        day_targets = (target.target_kcal, target.protein_g, target.fat_g, target.carbs_g)
        best: tuple[float, list[Meal], dict[str, int]] | None = None
        for attempt in range(_DAY_ATTEMPTS_FAT_CEILING):
            trial_usage = dict(usage_counts)
            trial = _build_day_meals(
                slots=slots,
                fractions=fractions,
                targets=day_targets,
                foods=foods,
                nutrition_input=nutrition_input,
                allergens=allergens,
                excluded=excluded,
                disliked=disliked,
                usage_counts=trial_usage,
                rng=rng,
                tables=tables,
            )
            score = _day_score(
                sum_macro_totals(m.totals for m in trial), day_targets, tables.fat.max_pct_kcal
            )
            if best is None or score < best[0]:
                best = (score, trial, trial_usage)
            if score <= 1.0:
                break
            if attempt + 1 >= _DAY_ATTEMPTS and not _fat_over_ceiling(
                sum_macro_totals(m.totals for m in best[1]), day_targets[2], tables
            ):
                break  # sin exceso de grasa: se acepta el mejor día (aviso de tolerancia)
        assert best is not None  # noqa: S101 (_DAY_ATTEMPTS >= 1)
        meals = best[1]
        usage_counts.clear()
        usage_counts.update(best[2])
        totals = sum_macro_totals(m.totals for m in meals)
        deviation = deviation_for(
            totals, target.target_kcal, target.protein_g, target.fat_g, target.carbs_g
        )
        # Decisión 5 (F1b): solo kcal, proteína o techo de grasa generan el aviso; la desviación
        # de grasa o carbohidratos dentro de la banda saludable es informativa.
        if (
            abs(deviation.kcal) > tables.tolerances.kcal
            or abs(deviation.protein) > tables.tolerances.macros
            or _fat_over_ceiling(totals, target.fat_g, tables)
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
