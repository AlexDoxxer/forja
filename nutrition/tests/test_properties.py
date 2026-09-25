"""Propiedades de MASTER_PROMPT §8.6 con Hypothesis.

1. Los suelos de seguridad se respetan siempre.
2. Los macros suman las kcal objetivo (±2 %).
3. Ningún alimento excluido ni alérgeno declarado aparece en un plan.
4. Un plan es reproducible con la misma semilla.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from forja_nutrition.energy import calculate_target
from forja_nutrition.foods import foods_by_id, load_foods
from forja_nutrition.models import (
    ActivityLevel,
    Allergen,
    DietType,
    MealPlan,
    NutritionGoal,
    NutritionInput,
    NutritionNoticeCode,
    NutritionPace,
    Sex,
)
from forja_nutrition.planner import plan_week
from forja_nutrition.shopping import shopping_list
from forja_nutrition.swap import swap_food
from forja_nutrition.tables import load_nutrition_tables
from tests.conftest import MONDAY

TABLES = load_nutrition_tables()
FOOD_IDS = sorted(food.id for food in load_foods())
CATALOG = foods_by_id()

_MACRO_SUM_TOLERANCE = 0.02

TARGET_SETTINGS = settings(max_examples=300, deadline=None)
PLAN_SETTINGS = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@st.composite
def any_inputs(draw: st.DrawFn) -> NutritionInput:
    """Entradas válidas de todo el dominio del contrato, incluidas las que se bloquean."""
    return NutritionInput(
        sex=draw(st.sampled_from(Sex)),
        age_years=draw(st.integers(min_value=0, max_value=120)),
        height_cm=draw(st.floats(min_value=100, max_value=250, allow_nan=False)),
        weight_kg=draw(st.floats(min_value=20, max_value=400, allow_nan=False)),
        activity_level=draw(st.sampled_from(ActivityLevel)),
        training_days_per_week=draw(st.integers(min_value=0, max_value=7)),
        goal=draw(st.sampled_from(NutritionGoal)),
        pace=draw(st.sampled_from(NutritionPace)),
        diet_type=draw(st.sampled_from(DietType)),
        meals_per_day=draw(st.integers(min_value=3, max_value=5)),
        pregnant=draw(st.booleans()),
        breastfeeding=draw(st.booleans()),
    )


@st.composite
def plannable_inputs(draw: st.DrawFn) -> NutritionInput:
    """Adultos no bloqueados, con alérgenos, exclusiones y rechazos reales del catálogo."""
    allergens = draw(st.lists(st.sampled_from(Allergen), unique=True, max_size=7))
    excluded = draw(st.lists(st.sampled_from(FOOD_IDS), unique=True, max_size=8))
    disliked = draw(st.lists(st.sampled_from(FOOD_IDS), unique=True, max_size=8))
    return NutritionInput(
        sex=draw(st.sampled_from(Sex)),
        age_years=draw(st.integers(min_value=18, max_value=90)),
        height_cm=draw(st.floats(min_value=140, max_value=210, allow_nan=False)),
        weight_kg=draw(st.floats(min_value=40, max_value=150, allow_nan=False)),
        activity_level=draw(st.sampled_from(ActivityLevel)),
        training_days_per_week=draw(st.integers(min_value=0, max_value=7)),
        goal=draw(st.sampled_from(NutritionGoal)),
        pace=draw(st.sampled_from(NutritionPace)),
        diet_type=draw(st.sampled_from(DietType)),
        meals_per_day=draw(st.integers(min_value=3, max_value=5)),
        allergens=tuple(allergens),
        excluded_food_ids=tuple(excluded),
        disliked_food_ids=tuple(disliked),
        seed=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=2**53 - 1))),
    )


@TARGET_SETTINGS
@given(any_inputs())
def test_target_is_blocked_or_fully_specified(nutrition_input: NutritionInput) -> None:
    target = calculate_target(nutrition_input)
    must_block = (
        nutrition_input.age_years < TABLES.safety.min_age
        or nutrition_input.pregnant
        or nutrition_input.breastfeeding
    )
    assert target.blocked is must_block
    if target.blocked:
        assert target.block is not None
        assert target.target_kcal is None
        assert target.protein_g is None
        assert target.fat_g is None
        assert target.carbs_g is None
        assert target.fiber_g is None
    else:
        assert target.block is None
        assert None not in (
            target.target_kcal,
            target.protein_g,
            target.fat_g,
            target.carbs_g,
            target.fiber_g,
        )


@TARGET_SETTINGS
@given(any_inputs())
def test_safety_floors_are_always_respected(nutrition_input: NutritionInput) -> None:
    target = calculate_target(nutrition_input)
    if target.blocked:
        return
    assert target.target_kcal is not None
    assert target.protein_g is not None
    assert target.fat_g is not None
    assert target.carbs_g is not None

    kcal_floor = TABLES.safety.kcal_floor[nutrition_input.sex]
    assert target.target_kcal >= max(target.bmr_kcal, kcal_floor) - 1e-6
    assert target.tdee_kcal - target.target_kcal <= 500.0 + 1e-6
    assert target.protein_g >= TABLES.protein_g_per_kg.min * nutrition_input.weight_kg - 1e-6
    assert target.protein_g <= TABLES.protein_g_per_kg.max * nutrition_input.weight_kg + 1e-6
    assert target.fat_g >= TABLES.fat.min_g_per_kg * nutrition_input.weight_kg - 1e-6
    assert target.fat_g * 9 >= TABLES.fat.min_pct_kcal * target.target_kcal - 1e-6
    assert target.carbs_g >= 0.0


@TARGET_SETTINGS
@given(any_inputs())
def test_low_bmi_never_keeps_a_lose_goal(nutrition_input: NutritionInput) -> None:
    target = calculate_target(nutrition_input)
    if target.blocked:
        return
    height_m = nutrition_input.height_cm / 100
    bmi = nutrition_input.weight_kg / (height_m * height_m)
    if bmi < TABLES.safety.block_lose_if_bmi_below:
        assert target.effective_goal != NutritionGoal.lose
        if nutrition_input.goal == NutritionGoal.lose:
            codes = {n.code for n in target.notices}
            assert NutritionNoticeCode.lose_blocked_low_bmi in codes


@TARGET_SETTINGS
@given(any_inputs())
def test_macros_sum_to_target_kcal_within_two_percent(nutrition_input: NutritionInput) -> None:
    target = calculate_target(nutrition_input)
    if target.blocked:
        return
    assert target.target_kcal is not None
    assert target.protein_g is not None
    assert target.fat_g is not None
    assert target.carbs_g is not None
    macro_kcal = 4 * target.protein_g + 4 * target.carbs_g + 9 * target.fat_g
    assert abs(macro_kcal - target.target_kcal) <= _MACRO_SUM_TOLERANCE * target.target_kcal


@TARGET_SETTINGS
@given(any_inputs())
def test_target_always_carries_the_health_disclaimer(nutrition_input: NutritionInput) -> None:
    target = calculate_target(nutrition_input)
    codes = {n.code for n in target.notices}
    assert NutritionNoticeCode.health_disclaimer in codes


def _assert_plan_respects_constraints(nutrition_input: NutritionInput, plan: MealPlan) -> None:
    excluded = set(nutrition_input.excluded_food_ids)
    allergens = set(nutrition_input.allergens)
    for day in plan.days:
        assert len(day.meals) == nutrition_input.meals_per_day
        for meal in day.meals:
            assert len(meal.items) >= 1
            for item in meal.items:
                food = CATALOG[item.food_id]
                assert item.food_id not in excluded
                assert not (set(food.allergens) & allergens)
                assert nutrition_input.diet_type in food.diet_types
                assert item.grams > 0


@PLAN_SETTINGS
@given(plannable_inputs())
def test_plan_never_contains_excluded_foods_or_declared_allergens(
    nutrition_input: NutritionInput,
) -> None:
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.block is None
    assert outcome.plan is not None
    _assert_plan_respects_constraints(nutrition_input, outcome.plan)


@PLAN_SETTINGS
@given(plannable_inputs())
def test_plan_is_reproducible_with_the_same_seed(nutrition_input: NutritionInput) -> None:
    first = plan_week(nutrition_input, MONDAY)
    second = plan_week(nutrition_input, MONDAY)
    assert first.plan is not None
    assert second.plan is not None
    assert first.plan.model_dump() == second.plan.model_dump()


@PLAN_SETTINGS
@given(plannable_inputs())
def test_plan_target_floors_and_tolerance_contract(nutrition_input: NutritionInput) -> None:
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    plan = outcome.plan
    target = plan.target
    assert target.target_kcal is not None
    kcal_floor = TABLES.safety.kcal_floor[nutrition_input.sex]
    assert target.target_kcal >= max(target.bmr_kcal, kcal_floor) - 1e-6

    exceeded = any(
        abs(day.deviation.kcal) > TABLES.tolerances.kcal
        or max(abs(day.deviation.protein), abs(day.deviation.fat), abs(day.deviation.carbs))
        > TABLES.tolerances.macros
        for day in plan.days
    )
    codes = {n.code for n in plan.notices}
    # contrato (`domain.md` §6.2): dentro de tolerancia o aviso `tolerance_not_met`
    assert exceeded == (NutritionNoticeCode.tolerance_not_met in codes)


@PLAN_SETTINGS
@given(plannable_inputs(), st.integers(min_value=0, max_value=6), st.data())
def test_swap_never_introduces_excluded_or_allergenic_foods(
    nutrition_input: NutritionInput, day_index: int, data: st.DataObject
) -> None:
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    plan = outcome.plan
    meal = data.draw(st.sampled_from(plan.days[day_index].meals))
    item = data.draw(st.sampled_from(meal.items))
    try:
        swapped = swap_food(plan, nutrition_input, day_index, meal.slot, item.food_id, None)
    except ValueError:
        # sin sustituto compatible en la categoría (p. ej. todos excluidos): es un error
        # explícito, no una violación de seguridad
        return
    _assert_plan_respects_constraints(nutrition_input, swapped)


@PLAN_SETTINGS
@given(plannable_inputs())
def test_shopping_list_totals_match_the_plan(nutrition_input: NutritionInput) -> None:
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    plan = outcome.plan
    planned = sum(item.grams for day in plan.days for meal in day.meals for item in meal.items)
    listed = sum(item.total_grams for cat in shopping_list(plan).categories for item in cat.items)
    # cada total se redondea a 0,1 g: tolerancia de 0,05 g por alimento distinto
    assert abs(planned - listed) <= 0.05 * len(CATALOG) + 1e-6
