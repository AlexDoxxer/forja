"""`forja_nutrition/swap.py`: intercambio de alimento conservando macros (§8.3)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from forja_nutrition.energy import calculate_target
from forja_nutrition.foods import foods_by_id
from forja_nutrition.models import (
    Allergen,
    DietType,
    Food,
    FoodCategory,
    FoodMacroRole,
    MacroDeviation,
    MacroTotals,
    Meal,
    MealItem,
    MealPlan,
    MealPlanDay,
    MealSlot,
    NutritionNoticeCode,
)
from forja_nutrition.planner import plan_week
from forja_nutrition.swap import (
    _build_replacement_item,
    _is_candidate,
    _locate,
    _pick_replacement,
    _resolve_replacement,
    swap_food,
)
from tests.conftest import MONDAY, make_input

CATALOG = foods_by_id()


def _plan_for(**overrides: object) -> MealPlan:
    nutrition_input = make_input(**overrides)
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    return outcome.plan


# ------------------------------------------------------------------------ _is_candidate


def test_is_candidate_rejects_same_food() -> None:
    manzana = CATALOG["manzana"]
    assert not _is_candidate(
        manzana, original=manzana, nutrition_input=make_input(), excluded=set(), allergens=set()
    )


def test_is_candidate_rejects_different_category() -> None:
    manzana = CATALOG["manzana"]
    pollo = CATALOG["pechuga_pollo"]
    assert not _is_candidate(
        pollo, original=manzana, nutrition_input=make_input(), excluded=set(), allergens=set()
    )


def test_is_candidate_rejects_category_outside_meal_templates() -> None:
    cerveza = CATALOG["cerveza"]
    refresco = CATALOG["refresco_cola"]
    assert cerveza.category == refresco.category == FoodCategory.beverages
    assert not _is_candidate(
        refresco, original=cerveza, nutrition_input=make_input(), excluded=set(), allergens=set()
    )


def test_is_candidate_rejects_excluded_id() -> None:
    manzana = CATALOG["manzana"]
    pera = CATALOG["pera"]
    assert not _is_candidate(
        pera,
        original=manzana,
        nutrition_input=make_input(),
        excluded={"pera"},
        allergens=set(),
    )


def test_is_candidate_rejects_wrong_diet_type() -> None:
    jamon = CATALOG["jamon_cocido"]
    pollo = CATALOG["pechuga_pollo"]
    assert not _is_candidate(
        pollo,
        original=jamon,
        nutrition_input=make_input(diet_type=DietType.vegan),
        excluded=set(),
        allergens=set(),
    )


def test_is_candidate_rejects_declared_allergen() -> None:
    almendra = CATALOG["almendra"]
    nuez = CATALOG["nuez"]
    assert not _is_candidate(
        nuez,
        original=almendra,
        nutrition_input=make_input(),
        excluded=set(),
        allergens={Allergen.tree_nuts},
    )


def test_is_candidate_accepts_valid_match() -> None:
    manzana = CATALOG["manzana"]
    pera = CATALOG["pera"]
    assert _is_candidate(
        pera, original=manzana, nutrition_input=make_input(), excluded=set(), allergens=set()
    )


# --------------------------------------------------------------------- _pick_replacement


def test_pick_replacement_raises_when_no_candidate_exists() -> None:
    cerveza = CATALOG["cerveza"]  # categoría "beverages": nunca es "meal eligible"
    with pytest.raises(ValueError, match="No hay ningún alimento"):
        _pick_replacement(cerveza, make_input(), seed=1)


def test_pick_replacement_prefers_non_disliked() -> None:
    manzana = CATALOG["manzana"]
    all_fruits = {f.id for f in CATALOG.values() if f.category == FoodCategory.fruits}
    disliked = all_fruits - {"manzana", "pera"}
    replacement = _pick_replacement(
        manzana, make_input(disliked_food_ids=tuple(sorted(disliked))), seed=1
    )
    assert replacement.id == "pera"


def test_pick_replacement_falls_back_to_disliked_if_no_alternative() -> None:
    manzana = CATALOG["manzana"]
    fruit_ids = {f.id for f in CATALOG.values() if f.category == FoodCategory.fruits}
    all_other_fruits = tuple(sorted(fruit_ids - {"manzana"}))
    replacement = _pick_replacement(manzana, make_input(disliked_food_ids=all_other_fruits), seed=1)
    assert replacement.category == FoodCategory.fruits
    assert replacement.id != "manzana"


def test_pick_replacement_is_deterministic_for_a_given_seed() -> None:
    manzana = CATALOG["manzana"]
    first = _pick_replacement(manzana, make_input(), seed=7)
    second = _pick_replacement(manzana, make_input(), seed=7)
    assert first.id == second.id


# ------------------------------------------------------------------------------ _locate


def test_locate_rejects_day_index_out_of_range() -> None:
    plan = _plan_for(seed=1)
    with pytest.raises(ValueError, match="day_index fuera de rango"):
        _locate(plan, 7, MealSlot.breakfast, "manzana")
    with pytest.raises(ValueError, match="day_index fuera de rango"):
        _locate(plan, -1, MealSlot.breakfast, "manzana")


def test_locate_rejects_missing_meal_slot() -> None:
    plan = _plan_for(seed=1, meals_per_day=3)
    with pytest.raises(ValueError, match="no existe en el día"):
        _locate(plan, 0, MealSlot.mid_morning, "manzana")


def test_locate_rejects_missing_food_id() -> None:
    plan = _plan_for(seed=1)
    slot = plan.days[0].meals[0].slot
    with pytest.raises(ValueError, match="no está en esa comida"):
        _locate(plan, 0, slot, "alimento_que_no_esta_en_el_plan")


def test_locate_finds_existing_item() -> None:
    plan = _plan_for(seed=1)
    meal = plan.days[0].meals[0]
    food_id = meal.items[0].food_id
    meal_index, item_index = _locate(plan, 0, meal.slot, food_id)
    assert plan.days[0].meals[meal_index].items[item_index].food_id == food_id


# ----------------------------------------------------------------- _resolve_replacement


def test_resolve_replacement_auto_picks_when_no_id_given() -> None:
    manzana = CATALOG["manzana"]
    replacement = _resolve_replacement(
        original_food=manzana,
        nutrition_input=make_input(),
        replacement_food_id=None,
        seed=1,
    )
    assert replacement.category == FoodCategory.fruits
    assert replacement.id != "manzana"


def test_resolve_replacement_rejects_unknown_replacement_id() -> None:
    manzana = CATALOG["manzana"]
    with pytest.raises(ValueError, match="no existe en la base de alimentos"):
        _resolve_replacement(
            original_food=manzana,
            nutrition_input=make_input(),
            replacement_food_id="alimento_fantasma",
            seed=1,
        )


def test_resolve_replacement_rejects_invalid_explicit_replacement() -> None:
    manzana = CATALOG["manzana"]
    with pytest.raises(ValueError, match="no es un sustituto válido"):
        _resolve_replacement(
            original_food=manzana,
            nutrition_input=make_input(),
            replacement_food_id="pechuga_pollo",
            seed=1,
        )


def test_resolve_replacement_accepts_valid_explicit_replacement() -> None:
    manzana = CATALOG["manzana"]
    replacement = _resolve_replacement(
        original_food=manzana,
        nutrition_input=make_input(),
        replacement_food_id="pera",
        seed=1,
    )
    assert replacement.id == "pera"


# ------------------------------------------------------------- _build_replacement_item


def test_build_replacement_item_scales_by_kcal_ratio() -> None:
    original_item = MealItem(
        food_id="manzana",
        name_es="Manzana",
        grams=180.0,
        nutrients=CATALOG["manzana"].per_100g,  # per 100g == totals for 100g; grams differ
    )
    new_item = _build_replacement_item(original_item, CATALOG["pera"])
    expected_grams_raw = original_item.nutrients.kcal / CATALOG["pera"].per_100g.kcal * 100.0
    # redondeado al paso de 5 g (pera no es alimento por unidad)
    assert new_item.grams == pytest.approx(round(expected_grams_raw / 5) * 5)


def test_build_replacement_item_falls_back_to_original_grams_when_replacement_has_no_kcal() -> None:
    zero_kcal_food = Food(
        id="agua_de_prueba",
        name_es="Agua de prueba",
        category=FoodCategory.beverages,
        fdc_id=1,
        per_100g=MacroTotals(kcal=0, protein_g=0, fat_g=0, carbs_g=0, fiber_g=0),
        diet_types=(DietType.omnivore,),
        macro_role=FoodMacroRole.produce,
        typical_portion_g=200.0,
    )
    original_item = MealItem(
        food_id="manzana",
        name_es="Manzana",
        grams=180.0,
        nutrients=MacroTotals(kcal=90, protein_g=0.5, fat_g=0.3, carbs_g=24, fiber_g=4),
    )
    new_item = _build_replacement_item(original_item, zero_kcal_food)
    assert new_item.grams == 180.0


def test_build_replacement_item_uses_minimum_ration_when_rounded_grams_is_zero() -> None:
    original_item = MealItem(
        food_id="manzana",
        name_es="Manzana",
        grams=1.0,
        nutrients=MacroTotals(kcal=0.5, protein_g=0.01, fat_g=0.01, carbs_g=0.1, fiber_g=0.02),
    )
    new_item = _build_replacement_item(original_item, CATALOG["aceite_oliva"])
    assert new_item.grams > 0


def test_build_replacement_item_uses_one_unit_for_unit_foods_when_rounded_to_zero() -> None:
    original_item = MealItem(
        food_id="manzana",
        name_es="Manzana",
        grams=1.0,
        nutrients=MacroTotals(kcal=0.1, protein_g=0.01, fat_g=0.0, carbs_g=0.02, fiber_g=0.0),
    )
    new_item = _build_replacement_item(original_item, CATALOG["huevo"])
    assert new_item.grams == CATALOG["huevo"].unit_grams
    assert new_item.units == 1


# ------------------------------------------------------------------------------ swap_food


def test_swap_food_auto_pick_replaces_item_and_keeps_other_days() -> None:
    plan = _plan_for(seed=1)
    day0 = plan.days[0]
    meal0 = day0.meals[0]
    item0 = meal0.items[0]

    new_plan = swap_food(plan, make_input(seed=1), 0, meal0.slot, item0.food_id, None)

    new_meal0 = new_plan.days[0].meals[0]
    assert new_meal0.items[0].food_id != item0.food_id
    assert new_plan.days[1:] == plan.days[1:]
    assert new_plan.seed == plan.seed
    assert new_plan.week_start == plan.week_start


def test_swap_food_explicit_replacement() -> None:
    plan = _plan_for(seed=1, diet_type=DietType.omnivore)
    day0 = plan.days[0]
    meal0 = day0.meals[0]
    original_food = CATALOG[meal0.items[0].food_id]
    same_category_candidates = [
        f
        for f in CATALOG.values()
        if f.category == original_food.category
        and f.id != original_food.id
        and DietType.omnivore in f.diet_types
    ]
    replacement = same_category_candidates[0]

    new_plan = swap_food(
        plan, make_input(seed=1), 0, meal0.slot, meal0.items[0].food_id, replacement.id
    )
    assert new_plan.days[0].meals[0].items[0].food_id == replacement.id


def test_swap_food_rejects_invalid_explicit_replacement() -> None:
    plan = _plan_for(seed=1)
    meal0 = plan.days[0].meals[0]
    with pytest.raises(ValueError, match="no existe en la base de alimentos"):
        swap_food(
            plan, make_input(seed=1), 0, meal0.slot, meal0.items[0].food_id, "fantasma_inexistente"
        )


def test_swap_food_raises_when_original_food_id_is_not_in_catalog() -> None:
    """Defensivo: `plan_week` nunca produce un `food_id` fuera del catálogo, pero
    `swap_food` no debe fallar de forma opaca si alguna vez ocurriera."""
    unknown_item = MealItem(
        food_id="alimento_inexistente",
        name_es="Alimento inexistente",
        grams=100.0,
        nutrients=MacroTotals(kcal=50, protein_g=1, fat_g=1, carbs_g=5, fiber_g=1),
    )
    meal = Meal(slot=MealSlot.breakfast, items=(unknown_item,), totals=unknown_item.nutrients)
    days = tuple(
        MealPlanDay(
            day_index=day_index,
            date=MONDAY + timedelta(days=day_index),
            meals=(meal,),
            totals=meal.totals,
            deviation=MacroDeviation(kcal=0.0, protein=0.0, fat=0.0, carbs=0.0),
        )
        for day_index in range(7)
    )
    plan = MealPlan(
        nutrition_version="0.1.0",
        foods_hash="a" * 64,
        seed=1,
        week_start=MONDAY,
        diet_type=DietType.omnivore,
        meals_per_day=3,
        target=calculate_target(make_input()),
        days=days,
        notices=(),
    )
    with pytest.raises(ValueError, match="no existe en la base de alimentos"):
        swap_food(plan, make_input(), 0, MealSlot.breakfast, "alimento_inexistente", None)


def test_swap_food_adds_notice_once_even_after_two_swaps() -> None:
    plan = _plan_for(seed=1)
    day0 = plan.days[0]
    meal0 = day0.meals[0]
    once = swap_food(plan, make_input(seed=1), 0, meal0.slot, meal0.items[0].food_id, None)
    codes_once = [n.code for n in once.notices]
    assert codes_once.count(NutritionNoticeCode.swap_macros_adjusted) == 1

    meal0_after = once.days[0].meals[0]
    twice = swap_food(
        once, make_input(seed=1), 0, meal0_after.slot, meal0_after.items[0].food_id, None
    )
    codes_twice = [n.code for n in twice.notices]
    assert codes_twice.count(NutritionNoticeCode.swap_macros_adjusted) == 1
