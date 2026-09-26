"""F1b B7/C12 y decisión 5: porciones máximas, idoneidad por comida, grasa y barrido de perfiles."""

from __future__ import annotations

import random

import pytest

from forja_nutrition.foods import foods_by_id, load_foods
from forja_nutrition.models import Food, FoodCategory, FoodMacroRole, Meal, MealItem, MealSlot
from forja_nutrition.planner import (
    _selection_weight,
    build_meal_candidates,
    nutrients_for,
    plan_week,
    polish_day,
    round_grams,
    solve_grams,
    sum_macro_totals,
    trim_fat,
)
from forja_nutrition.tables import load_nutrition_tables
from scripts.sweep import run_sweep, sweep_inputs
from tests.conftest import MONDAY, make_input
from tests.test_planner import _food

TABLES = load_nutrition_tables()
CATALOG = foods_by_id()


def test_every_food_has_a_valid_max_portion_and_slots() -> None:
    for food in load_foods():
        assert food.max_portion_g > 0, food.id
        if food.unit_grams is not None:
            assert food.max_portion_g >= food.unit_grams, food.id
        if food.category in {FoodCategory.condiments, FoodCategory.beverages}:
            assert food.meal_slots == (), food.id


def test_reviewed_max_portions_and_weekly_limits() -> None:
    assert CATALOG["anchoa_lata"].max_portion_g == 30
    assert CATALOG["higado_vacuno"].max_portion_g == 100
    assert CATALOG["higado_vacuno"].weekly_max == 1
    assert CATALOG["aceite_oliva"].max_portion_g == 30
    assert CATALOG["aceite_coco"].max_portion_g == 10
    assert CATALOG["sesamo"].max_portion_g == 15
    assert CATALOG["bacon"].weekly_max == 2


def test_legumes_fish_and_stewed_meat_are_never_breakfast_foods() -> None:
    cured = {"jamon_cocido", "jamon_curado", "bacon", "salchicha_cerdo"}
    for food in load_foods():
        if food.category in {FoodCategory.legumes, FoodCategory.fish_seafood} or (
            food.category is FoodCategory.meat and food.id not in cured
        ):
            assert MealSlot.breakfast not in food.meal_slots, food.id
            assert MealSlot.snack not in food.meal_slots or food.id == "atun_lata", food.id


def test_olive_oil_is_preferred_over_coconut_and_sunflower() -> None:
    olive = _selection_weight(CATALOG["aceite_oliva"], {}, set())
    assert olive > 3 * _selection_weight(CATALOG["aceite_canola"], {}, set())
    assert _selection_weight(CATALOG["aceite_coco"], {}, set()) < _selection_weight(
        CATALOG["aceite_canola"], {}, set()
    )
    assert _selection_weight(CATALOG["aceite_girasol"], {}, set()) < _selection_weight(
        CATALOG["aceite_canola"], {}, set()
    )


def test_dense_protein_and_fat_heavy_foods_are_weighted() -> None:
    lean = _food("magro", macro_role=FoodMacroRole.protein, kcal=100.0, protein_g=25.0, fat_g=1.0)
    diluted = _food(
        "diluido", macro_role=FoodMacroRole.protein, kcal=100.0, protein_g=3.0, fat_g=1.0
    )
    fatty = _food("graso", macro_role=FoodMacroRole.carb, kcal=100.0, protein_g=3.0, fat_g=9.0)
    plain = _food("normal", macro_role=FoodMacroRole.carb, kcal=100.0, protein_g=3.0, fat_g=1.0)
    assert _selection_weight(lean, {}, set()) > _selection_weight(diluted, {}, set())
    assert _selection_weight(fatty, {}, set()) < _selection_weight(plain, {}, set())


def test_round_grams_respects_max_portion_for_weight_and_unit_foods() -> None:
    rounding = TABLES.rounding
    grams, units = round_grams(500.0, CATALOG["anchoa_lata"], rounding)
    assert grams == 30
    assert units is None
    grams, units = round_grams(900.0, CATALOG["huevo"], rounding)
    assert grams == CATALOG["huevo"].max_portion_g
    assert units == 4
    tiny_cap = _food("tope", max_portion_g=3.0)
    assert round_grams(50.0, tiny_cap, rounding) == (3.0, None)


def test_solve_grams_never_exceeds_max_portion() -> None:
    foods = [_food("a", kcal=900.0, fat_g=100.0, max_portion_g=20.0)]
    assert solve_grams(foods, 2000.0, 0.0, 200.0, 0.0)[0] <= 20.0 + 1e-9


def test_solve_grams_anchor_keeps_items_above_minimum_portion() -> None:
    foods = [_food("a", typical_portion_g=100.0), _food("b", kcal=300.0, typical_portion_g=50.0)]
    grams = solve_grams(foods, 10.0, 0.0, 0.0, 0.0, anchor=[100.0, 50.0])
    assert grams[0] >= 30.0 - 1e-9
    assert grams[1] >= 15.0 - 1e-9


def _candidates(slot: MealSlot, *foods: Food) -> list[Food]:
    return build_meal_candidates(
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
        slot=slot,
    )


def test_candidates_respect_meal_slots() -> None:
    breakfast_food = _food("desayuno", meal_slots=(MealSlot.breakfast,))
    dinner_food = _food("cena", meal_slots=(MealSlot.dinner,))
    chosen = _candidates(MealSlot.breakfast, breakfast_food, dinner_food)
    assert [food.id for food in chosen] == ["desayuno"]


def test_candidates_relax_meal_slots_when_nothing_fits() -> None:
    only_dinner = _food("cena", meal_slots=(MealSlot.dinner,))
    chosen = _candidates(MealSlot.breakfast, only_dinner)
    assert [food.id for food in chosen] == ["cena"]


def test_weekly_max_removes_a_food_after_its_limit() -> None:
    limited = _food("embutido", macro_role=FoodMacroRole.protein, weekly_max=1)
    chosen = build_meal_candidates(
        foods=(limited, _food("otro", macro_role=FoodMacroRole.protein)),
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={"embutido": 1},
        rng=random.Random(1),  # noqa: S311
        slot=MealSlot.lunch,
    )
    assert [food.id for food in chosen] == ["otro"]


def _meal_of(food_id: str, grams: float) -> Meal:
    food = CATALOG[food_id]
    item = MealItem(
        food_id=food_id, name_es=food.name_es, grams=grams, nutrients=nutrients_for(food, grams)
    )
    return Meal(slot=MealSlot.lunch, items=(item,), totals=sum_macro_totals([item.nutrients]))


def test_trim_fat_reduces_a_day_over_the_ceiling() -> None:
    meals = [_meal_of("aceite_oliva", 30.0), _meal_of("arroz_blanco", 100.0)]
    trimmed = trim_fat(meals, fat_target_g=10.0, tables=TABLES)
    assert trimmed[0].items[0].grams < 30.0
    assert trimmed[1].items[0].grams == 100.0


def test_trim_fat_stops_when_no_item_can_shrink_further() -> None:
    meals = [_meal_of("aceite_oliva", 5.0)]  # 5 g = mínimo útil (0,3 x 10 g) no se puede recortar
    trimmed = trim_fat(meals, fat_target_g=0.0, tables=TABLES)
    assert trimmed[0].items[0].grams == 5.0


def test_trim_fat_shrinks_unit_foods_by_whole_units() -> None:
    meals = [_meal_of("huevo", 200.0)]
    trimmed = trim_fat(meals, fat_target_g=1.0, tables=TABLES)
    item = trimmed[0].items[0]
    assert item.grams < 200.0
    assert item.units == round(item.grams / 50.0)


def test_polish_day_never_worsens_the_day() -> None:
    meals = [_meal_of("pechuga_pollo", 150.0), _meal_of("arroz_blanco", 70.0)]
    targets = (700.0, 50.0, 12.0, 80.0)
    polished = polish_day(meals, targets, TABLES.rounding, TABLES.fat.max_pct_kcal)
    before = sum(m.totals.kcal for m in meals)
    after = sum(m.totals.kcal for m in polished)
    assert abs(after - 700.0) <= abs(before - 700.0) + 1e-9


def test_sweep_inputs_cover_288_profiles() -> None:
    assert len(sweep_inputs()) == 288


def test_sweep_subset_meets_the_f1b_targets() -> None:
    """Subconjunto rápido (1 de cada 6 perfiles, 48 planes); el barrido completo es `slow`."""
    inputs = sweep_inputs()[::6]
    result = run_sweep(inputs)
    assert result.plans == len(inputs)
    assert result.days_fat_above_ceiling == 0
    assert result.tolerance_not_met_rate <= 0.25
    assert result.breakfasts_with_forbidden_food == 0
    assert result.items_above_max_portion == 0
    assert result.items_below_min_portion == 0
    assert result.allergen_violations == 0


@pytest.mark.slow
def test_full_288_profile_sweep_meets_the_f1b_targets() -> None:
    result = run_sweep()
    assert result.plans == 288
    assert result.days == 2016
    assert result.days_fat_above_ceiling == 0
    assert result.tolerance_not_met_rate <= 0.25
    assert result.breakfasts_with_forbidden_food == 0
    assert result.items_above_max_portion == 0
    assert result.items_below_min_portion == 0
    assert result.allergen_violations == 0
    assert result.vegan_days_fat_over_allowed / result.vegan_days <= 0.25
    assert "days_fat_above_ceiling" in result.to_json()


def test_sesame_and_celery_are_never_auto_selected() -> None:
    # sin valor de `Allergen` en v1: `meal_slots` vacío los excluye de la selección automática
    for food_id in ("sesamo", "apio", "mostaza"):
        assert CATALOG[food_id].meal_slots == (), food_id
    for inp in sweep_inputs()[:24]:
        plan = plan_week(inp, MONDAY).plan
        assert plan is not None
        used = {i.food_id for d in plan.days for m in d.meals for i in m.items}
        assert not used & {"sesamo", "apio", "mostaza"}


def test_days_prefer_distinct_foods() -> None:
    repeated = days = 0
    for inp in sweep_inputs()[:48]:
        plan = plan_week(inp, MONDAY).plan
        assert plan is not None
        for day in plan.days:
            ids = [i.food_id for m in day.meals for i in m.items]
            days += 1
            repeated += len(ids) != len(set(ids))
    assert repeated / days < 0.30
