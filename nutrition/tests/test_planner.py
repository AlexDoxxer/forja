"""`forja_nutrition/planner.py`: selección de alimentos, mínimos cuadrados y `plan_week`."""

from __future__ import annotations

import random
from datetime import timedelta

import pytest

import forja_nutrition.planner as planner_module
from forja_nutrition.foods import foods_by_id
from forja_nutrition.models import (
    Allergen,
    DietType,
    Food,
    FoodCategory,
    FoodMacroRole,
    MacroDeviation,
    MacroTotals,
    MealSlot,
    NutritionGoal,
    NutritionNoticeCode,
)
from forja_nutrition.planner import (
    _eligible,
    _selection_weight,
    build_meal,
    build_meal_candidates,
    deviation_for,
    meal_eligible_categories,
    nutrients_for,
    plan_week,
    relative_deviation,
    round_grams,
    select_food,
    solve_grams,
    sum_macro_totals,
)
from forja_nutrition.seeding import derive_seed
from forja_nutrition.tables import load_nutrition_tables
from tests.conftest import MONDAY, make_input

TABLES = load_nutrition_tables()


def _food(
    food_id: str,
    *,
    category: FoodCategory = FoodCategory.vegetables,
    macro_role: FoodMacroRole = FoodMacroRole.produce,
    diet_types: tuple[DietType, ...] = (DietType.omnivore, DietType.vegan),
    allergens: tuple[Allergen, ...] = (),
    kcal: float = 50.0,
    protein_g: float = 2.0,
    fat_g: float = 1.0,
    carbs_g: float = 8.0,
    unit_grams: float | None = None,
    unit_name_es: str | None = None,
    typical_portion_g: float = 100.0,
) -> Food:
    return Food(
        id=food_id,
        name_es=food_id.replace("_", " ").title(),
        category=category,
        fdc_id=1,
        per_100g=MacroTotals(
            kcal=kcal, protein_g=protein_g, fat_g=fat_g, carbs_g=carbs_g, fiber_g=1.0
        ),
        diet_types=diet_types,
        allergens=allergens,
        macro_role=macro_role,
        typical_portion_g=typical_portion_g,
        unit_grams=unit_grams,
        unit_name_es=unit_name_es,
    )


# --------------------------------------------------------------------------- _eligible


def test_eligible_rejects_non_meal_category() -> None:
    food = _food("cerveza", category=FoodCategory.beverages)
    assert not _eligible(food, make_input(), set(), set())


def test_eligible_rejects_excluded_id() -> None:
    food = _food("tomate")
    assert not _eligible(food, make_input(), set(), {"tomate"})


def test_eligible_rejects_wrong_diet_type() -> None:
    food = _food("jamon", diet_types=(DietType.omnivore,))
    assert not _eligible(food, make_input(diet_type=DietType.vegan), set(), set())


def test_eligible_rejects_declared_allergen() -> None:
    food = _food("almendra", allergens=(Allergen.tree_nuts,))
    assert not _eligible(food, make_input(), {Allergen.tree_nuts}, set())


def test_eligible_accepts_matching_food() -> None:
    food = _food("tomate")
    assert _eligible(food, make_input(), set(), set())


def test_meal_eligible_categories_excludes_condiments_and_beverages() -> None:
    categories = meal_eligible_categories()
    assert FoodCategory.condiments not in categories
    assert FoodCategory.beverages not in categories
    assert FoodCategory.vegetables in categories


# ---------------------------------------------------------------- _selection_weight


def test_selection_weight_base_case() -> None:
    food = _food("tomate")
    assert _selection_weight(food, {}, set()) == 10.0


def test_selection_weight_penalizes_repeat_use() -> None:
    food = _food("tomate")
    weight = _selection_weight(food, {"tomate": 2}, set())
    assert weight == pytest.approx(10.0 - 3.0 * 2)


def test_selection_weight_penalizes_disliked() -> None:
    food = _food("tomate")
    weight = _selection_weight(food, {}, {"tomate"})
    assert weight == pytest.approx(10.0 * 0.2)


def test_selection_weight_never_below_minimum() -> None:
    food = _food("tomate")
    weight = _selection_weight(food, {"tomate": 100}, set())
    assert weight == 0.5


# --------------------------------------------------------------------- select_food


def test_select_food_returns_none_without_candidates() -> None:
    foods = (_food("pollo", macro_role=FoodMacroRole.protein),)
    result = select_food(
        role=FoodMacroRole.fat,
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
    )
    assert result is None


def test_select_food_returns_a_candidate() -> None:
    foods = (_food("tomate", macro_role=FoodMacroRole.produce),)
    result = select_food(
        role=FoodMacroRole.produce,
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
    )
    assert result is not None
    assert result.id == "tomate"


# ------------------------------------------------------------- build_meal_candidates


def test_build_meal_candidates_fills_every_role() -> None:
    foods = (
        _food("pollo", macro_role=FoodMacroRole.protein, category=FoodCategory.meat),
        _food("arroz", macro_role=FoodMacroRole.carb, category=FoodCategory.grains),
        _food("tomate", macro_role=FoodMacroRole.produce, category=FoodCategory.vegetables),
        _food("aceite", macro_role=FoodMacroRole.fat, category=FoodCategory.fats_oils),
    )
    chosen = build_meal_candidates(
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
    )
    assert {f.macro_role for f in chosen} == {
        FoodMacroRole.protein,
        FoodMacroRole.carb,
        FoodMacroRole.produce,
        FoodMacroRole.fat,
    }


def test_build_meal_candidates_skips_roles_without_candidates() -> None:
    # Solo hay un alimento, de rol "produce": los otros tres roles no aportan nada y la
    # comida se queda con un único candidato.
    foods = (_food("tomate", macro_role=FoodMacroRole.produce),)
    chosen = build_meal_candidates(
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
    )
    assert [f.id for f in chosen] == ["tomate"]


def test_build_meal_candidates_raises_when_nothing_is_eligible() -> None:
    foods = (_food("tomate", category=FoodCategory.beverages),)
    with pytest.raises(ValueError, match="No hay ningún alimento"):
        build_meal_candidates(
            foods=foods,
            nutrition_input=make_input(),
            allergens=set(),
            excluded=set(),
            disliked=set(),
            usage_counts={},
            rng=random.Random(1),  # noqa: S311
        )


# --------------------------------------------------------------------- round_grams


def test_round_grams_unit_food_rounds_to_nearest_unit() -> None:
    food = _food("huevo", unit_grams=50.0, unit_name_es="huevo")
    grams, units = round_grams(120.0, food, TABLES.rounding)
    assert units == 2
    assert grams == 100.0


def test_round_grams_unit_food_below_half_unit_still_gets_one() -> None:
    food = _food("huevo", unit_grams=50.0, unit_name_es="huevo")
    grams, units = round_grams(5.0, food, TABLES.rounding)
    assert units == 1
    assert grams == 50.0


def test_round_grams_unit_food_zero_grams_stays_zero() -> None:
    food = _food("huevo", unit_grams=50.0, unit_name_es="huevo")
    grams, units = round_grams(0.0, food, TABLES.rounding)
    assert grams == 0.0
    assert units is None


def test_round_grams_non_unit_food_rounds_to_step() -> None:
    food = _food("tomate")
    grams, units = round_grams(103.0, food, TABLES.rounding)
    assert grams == 105.0
    assert units is None


# ------------------------------------------------------------------- nutrients_for


def test_nutrients_for_scales_per_100g() -> None:
    food = _food("tomate", kcal=50.0, protein_g=2.0, fat_g=1.0, carbs_g=8.0)
    totals = nutrients_for(food, 200.0)
    assert totals.kcal == 100.0
    assert totals.protein_g == 4.0


def test_nutrients_for_never_negative() -> None:
    food = _food("tomate")
    totals = nutrients_for(food, -50.0)
    assert totals.kcal == 0.0
    assert totals.protein_g == 0.0


# ---------------------------------------------------------------------- solve_grams


def test_solve_grams_returns_non_negative_values_of_right_length() -> None:
    foods = [_food("tomate"), _food("arroz", kcal=350.0, carbs_g=75.0)]
    grams = solve_grams(foods, 300.0, 10.0, 5.0, 50.0)
    assert len(grams) == 2
    assert all(g >= 0.0 for g in grams)


# ------------------------------------------------------------------------ build_meal


def test_build_meal_produces_at_least_one_item() -> None:
    foods = (
        _food("pollo", macro_role=FoodMacroRole.protein, category=FoodCategory.meat, kcal=165),
        _food("arroz", macro_role=FoodMacroRole.carb, category=FoodCategory.grains, kcal=350),
        _food("tomate", macro_role=FoodMacroRole.produce, category=FoodCategory.vegetables),
        _food("aceite", macro_role=FoodMacroRole.fat, category=FoodCategory.fats_oils, kcal=884),
    )
    meal = build_meal(
        slot=MealSlot.lunch,
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
        kcal_target=600.0,
        protein_target=40.0,
        fat_target=20.0,
        carbs_target=60.0,
        rounding=TABLES.rounding,
    )
    assert len(meal.items) >= 1
    assert meal.totals.kcal >= 0


def test_build_meal_falls_back_to_minimum_ration_when_everything_rounds_to_zero() -> None:
    # Un único candidato de coste calórico enorme por gramo típico y un objetivo minúsculo:
    # lsq_linear devolverá gramos casi nulos que redondean a 0 con el paso de 5 g.
    foods = (
        _food(
            "condimento_potente",
            macro_role=FoodMacroRole.produce,
            kcal=900.0,
            protein_g=0.1,
            fat_g=0.1,
            carbs_g=0.1,
            typical_portion_g=5.0,
        ),
    )
    meal = build_meal(
        slot=MealSlot.snack,
        foods=foods,
        nutrition_input=make_input(),
        allergens=set(),
        excluded=set(),
        disliked=set(),
        usage_counts={},
        rng=random.Random(1),  # noqa: S311
        kcal_target=0.01,
        protein_target=0.001,
        fat_target=0.001,
        carbs_target=0.001,
        rounding=TABLES.rounding,
    )
    assert len(meal.items) == 1
    assert meal.items[0].food_id == "condimento_potente"
    assert meal.items[0].grams > 0


# ------------------------------------------------------- sum/deviation helpers


def test_sum_macro_totals_adds_up() -> None:
    totals = sum_macro_totals(
        [
            MacroTotals(kcal=100, protein_g=10, fat_g=5, carbs_g=10, fiber_g=2),
            MacroTotals(kcal=50, protein_g=5, fat_g=2, carbs_g=5, fiber_g=1),
        ]
    )
    assert totals.kcal == 150
    assert totals.protein_g == 15


def test_relative_deviation_zero_target_returns_zero() -> None:
    assert relative_deviation(100.0, 0.0) == 0.0
    assert relative_deviation(100.0, None) == 0.0


def test_relative_deviation_normal_case() -> None:
    assert relative_deviation(110.0, 100.0) == pytest.approx(0.1)


def test_deviation_for() -> None:
    totals = MacroTotals(kcal=110, protein_g=55, fat_g=22, carbs_g=110, fiber_g=10)
    deviation = deviation_for(totals, 100.0, 50.0, 20.0, 100.0)
    assert deviation.kcal == pytest.approx(0.1)
    assert deviation.protein == pytest.approx(0.1)


# -------------------------------------------------------------------------- plan_week


def test_plan_week_returns_block_for_blocked_input() -> None:
    outcome = plan_week(make_input(age_years=15), MONDAY)
    assert outcome.plan is None
    assert outcome.block is not None


def test_plan_week_returns_a_full_seven_day_plan() -> None:
    outcome = plan_week(make_input(), MONDAY)
    assert outcome.block is None
    assert outcome.plan is not None
    assert len(outcome.plan.days) == 7
    for day in outcome.plan.days:
        assert len(day.meals) == 3


@pytest.mark.parametrize("meals_per_day", [3, 4, 5])
def test_plan_week_respects_meals_per_day(meals_per_day: int) -> None:
    outcome = plan_week(make_input(meals_per_day=meals_per_day), MONDAY)
    assert outcome.plan is not None
    for day in outcome.plan.days:
        assert len(day.meals) == meals_per_day


def test_plan_week_is_reproducible_with_explicit_seed() -> None:
    nutrition_input = make_input(seed=999, goal=NutritionGoal.lose)
    first = plan_week(nutrition_input, MONDAY)
    second = plan_week(nutrition_input, MONDAY)
    assert first.plan is not None
    assert second.plan is not None
    assert first.plan.model_dump() == second.plan.model_dump()


def test_plan_week_seed_recorded_matches_explicit_seed() -> None:
    outcome = plan_week(make_input(seed=4242), MONDAY)
    assert outcome.plan is not None
    assert outcome.plan.seed == 4242


def test_plan_week_derives_seed_when_none_given() -> None:
    nutrition_input = make_input(seed=None)
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    assert outcome.plan.seed == derive_seed(nutrition_input)


def test_plan_week_never_uses_excluded_or_allergenic_foods() -> None:
    nutrition_input = make_input(allergens=(Allergen.gluten,), excluded_food_ids=("huevo",), seed=5)
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    catalog = foods_by_id()
    for day in outcome.plan.days:
        for meal in day.meals:
            for item in meal.items:
                food = catalog[item.food_id]
                assert item.food_id != "huevo"
                assert Allergen.gluten not in food.allergens


def test_plan_week_only_uses_foods_matching_diet_type() -> None:
    nutrition_input = make_input(diet_type=DietType.vegan, seed=11)
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    catalog = foods_by_id()
    for day in outcome.plan.days:
        for meal in day.meals:
            for item in meal.items:
                food = catalog[item.food_id]
                assert DietType.vegan in food.diet_types


def test_plan_week_flags_tolerance_not_met_when_a_day_drifts() -> None:
    # Dieta vegana + alergia a frutos secos reduce mucho el catálogo elegible para "fat" y
    # empuja la desviación de grasa más allá de la tolerancia en al menos un día (observado
    # de forma determinista con esta semilla).
    nutrition_input = make_input(
        diet_type=DietType.vegan,
        allergens=(Allergen.tree_nuts,),
        goal=NutritionGoal.maintain,
        seed=42,
    )
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    codes = {n.code for n in outcome.plan.notices}
    assert NutritionNoticeCode.tolerance_not_met in codes


def test_plan_week_does_not_flag_tolerance_when_every_day_is_on_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Con `lsq_linear` y un catálogo de ~200 alimentos rara vez los 7 días caen dentro de
    tolerancia a la vez; se fuerza con una `deviation_for` que siempre da 0 para probar la
    rama en la que `tolerance_not_met` NO se añade."""
    monkeypatch.setattr(
        planner_module,
        "deviation_for",
        lambda *_args, **_kwargs: MacroDeviation(kcal=0.0, protein=0.0, fat=0.0, carbs=0.0),
    )
    outcome = plan_week(make_input(seed=1), MONDAY)
    assert outcome.plan is not None
    codes = {n.code for n in outcome.plan.notices}
    assert NutritionNoticeCode.tolerance_not_met not in codes


def test_plan_week_uses_date_range_starting_at_week_start() -> None:
    outcome = plan_week(make_input(seed=3), MONDAY)
    assert outcome.plan is not None
    dates = [day.date for day in outcome.plan.days]
    assert dates == [MONDAY + timedelta(days=i) for i in range(7)]


def test_peanuts_allergen_tags_and_never_in_plan() -> None:
    catalog = foods_by_id()
    for food_id in ("cacahuete", "mantequilla_cacahuete"):
        assert Allergen.peanuts in catalog[food_id].allergens
    for diet in (DietType.omnivore, DietType.vegan):
        for seed in range(3):
            outcome = plan_week(
                make_input(allergens=(Allergen.peanuts,), diet_type=diet, seed=seed), MONDAY
            )
            assert outcome.plan is not None
            for day in outcome.plan.days:
                for meal in day.meals:
                    for item in meal.items:
                        assert Allergen.peanuts not in catalog[item.food_id].allergens
