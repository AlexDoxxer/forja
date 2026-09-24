"""Invariantes de los DTOs (`contracts/domain.md` §6.2)."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from forja_nutrition.models import (
    Allergen,
    BmrMethod,
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
    MealPlanOutcome,
    MealSlot,
    NutritionBlock,
    NutritionBlockReason,
    NutritionGoal,
    NutritionNotice,
    NutritionNoticeCode,
    NutritionPace,
    NutritionTarget,
)
from tests.conftest import MONDAY, make_input


def _macro_totals(**overrides: float) -> MacroTotals:
    base = {"kcal": 100.0, "protein_g": 5.0, "fat_g": 3.0, "carbs_g": 10.0, "fiber_g": 2.0}
    base.update(overrides)
    return MacroTotals(**base)


def _meal_item(food_id: str = "manzana") -> MealItem:
    return MealItem(food_id=food_id, name_es="Manzana", grams=100, nutrients=_macro_totals())


def _meal(slot: MealSlot = MealSlot.breakfast) -> Meal:
    item = _meal_item()
    return Meal(slot=slot, items=(item,), totals=item.nutrients)


def _day(day_index: int) -> MealPlanDay:
    meal = _meal()
    return MealPlanDay(
        day_index=day_index,
        date=MONDAY,
        meals=(meal,),
        totals=meal.totals,
        deviation=MacroDeviation(kcal=0.0, protein=0.0, fat=0.0, carbs=0.0),
    )


def _target(*, blocked: bool = False) -> NutritionTarget:
    if blocked:
        return NutritionTarget(
            method=BmrMethod.mifflin_male,
            age_years=30,
            bmr_kcal=1800.0,
            activity_factor=1.5,
            tdee_kcal=2700.0,
            requested_goal=NutritionGoal.lose,
            effective_goal=NutritionGoal.lose,
            pace=NutritionPace.standard,
            target_kcal=None,
            protein_g=None,
            fat_g=None,
            carbs_g=None,
            fiber_g=None,
            blocked=True,
            block=NutritionBlock(reason_code=NutritionBlockReason.under_18, message_es="x"),
            notices=(),
        )
    return NutritionTarget(
        method=BmrMethod.mifflin_male,
        age_years=30,
        bmr_kcal=1800.0,
        activity_factor=1.5,
        tdee_kcal=2700.0,
        requested_goal=NutritionGoal.maintain,
        effective_goal=NutritionGoal.maintain,
        pace=NutritionPace.standard,
        target_kcal=2700.0,
        protein_g=150.0,
        fat_g=80.0,
        carbs_g=300.0,
        fiber_g=38.0,
        blocked=False,
        block=None,
        notices=(NutritionNotice(code=NutritionNoticeCode.health_disclaimer, message_es="x"),),
    )


def test_nutrition_input_rejects_duplicate_allergens() -> None:
    with pytest.raises(ValidationError):
        make_input(allergens=(Allergen.egg, Allergen.egg))


def test_nutrition_input_rejects_duplicate_excluded_ids() -> None:
    with pytest.raises(ValidationError):
        make_input(excluded_food_ids=("huevo", "huevo"))


def test_nutrition_input_accepts_unique_lists() -> None:
    nutrition_input = make_input(allergens=(Allergen.egg, Allergen.soy))
    assert nutrition_input.allergens == (Allergen.egg, Allergen.soy)


def test_nutrition_target_blocked_requires_block() -> None:
    with pytest.raises(ValidationError):
        NutritionTarget(
            method=BmrMethod.mifflin_male,
            age_years=30,
            bmr_kcal=1800.0,
            activity_factor=1.5,
            tdee_kcal=2700.0,
            requested_goal=NutritionGoal.lose,
            effective_goal=NutritionGoal.lose,
            pace=NutritionPace.standard,
            target_kcal=None,
            protein_g=None,
            fat_g=None,
            carbs_g=None,
            fiber_g=None,
            blocked=True,
            block=None,
            notices=(),
        )


def test_nutrition_target_blocked_forbids_numbers() -> None:
    with pytest.raises(ValidationError):
        NutritionTarget(
            method=BmrMethod.mifflin_male,
            age_years=30,
            bmr_kcal=1800.0,
            activity_factor=1.5,
            tdee_kcal=2700.0,
            requested_goal=NutritionGoal.lose,
            effective_goal=NutritionGoal.lose,
            pace=NutritionPace.standard,
            target_kcal=1500.0,
            protein_g=None,
            fat_g=None,
            carbs_g=None,
            fiber_g=None,
            blocked=True,
            block=NutritionBlock(reason_code=NutritionBlockReason.under_18, message_es="x"),
            notices=(),
        )


def test_nutrition_target_unblocked_forbids_block() -> None:
    with pytest.raises(ValidationError):
        NutritionTarget(
            method=BmrMethod.mifflin_male,
            age_years=30,
            bmr_kcal=1800.0,
            activity_factor=1.5,
            tdee_kcal=2700.0,
            requested_goal=NutritionGoal.maintain,
            effective_goal=NutritionGoal.maintain,
            pace=NutritionPace.standard,
            target_kcal=2700.0,
            protein_g=150.0,
            fat_g=80.0,
            carbs_g=300.0,
            fiber_g=38.0,
            blocked=False,
            block=NutritionBlock(reason_code=NutritionBlockReason.under_18, message_es="x"),
            notices=(),
        )


def test_nutrition_target_unblocked_requires_numbers() -> None:
    with pytest.raises(ValidationError):
        NutritionTarget(
            method=BmrMethod.mifflin_male,
            age_years=30,
            bmr_kcal=1800.0,
            activity_factor=1.5,
            tdee_kcal=2700.0,
            requested_goal=NutritionGoal.maintain,
            effective_goal=NutritionGoal.maintain,
            pace=NutritionPace.standard,
            target_kcal=None,
            protein_g=150.0,
            fat_g=80.0,
            carbs_g=300.0,
            fiber_g=38.0,
            blocked=False,
            block=None,
            notices=(),
        )


def test_nutrition_target_valid_cases() -> None:
    assert _target(blocked=True).blocked is True
    assert _target(blocked=False).blocked is False


def test_meal_plan_requires_monday_week_start() -> None:
    days = tuple(_day(i) for i in range(7))
    with pytest.raises(ValidationError):
        MealPlan(
            nutrition_version="0.1.0",
            foods_hash="a" * 64,
            seed=1,
            week_start=date(2026, 9, 29),  # martes
            diet_type=DietType.omnivore,
            meals_per_day=3,
            target=_target(),
            days=days,
            notices=(),
        )


def test_meal_plan_requires_day_indexes_in_order() -> None:
    days = tuple(_day(i) for i in range(7))
    bad_days = (days[1], days[0], *days[2:])
    with pytest.raises(ValidationError):
        MealPlan(
            nutrition_version="0.1.0",
            foods_hash="a" * 64,
            seed=1,
            week_start=MONDAY,
            diet_type=DietType.omnivore,
            meals_per_day=3,
            target=_target(),
            days=bad_days,
            notices=(),
        )


def test_meal_plan_valid() -> None:
    days = tuple(_day(i) for i in range(7))
    plan = MealPlan(
        nutrition_version="0.1.0",
        foods_hash="a" * 64,
        seed=1,
        week_start=MONDAY,
        diet_type=DietType.omnivore,
        meals_per_day=3,
        target=_target(),
        days=days,
        notices=(),
    )
    assert plan.week_start == MONDAY


def test_meal_plan_outcome_requires_exactly_one() -> None:
    with pytest.raises(ValidationError):
        MealPlanOutcome(plan=None, block=None)
    days = tuple(_day(i) for i in range(7))
    plan = MealPlan(
        nutrition_version="0.1.0",
        foods_hash="a" * 64,
        seed=1,
        week_start=MONDAY,
        diet_type=DietType.omnivore,
        meals_per_day=3,
        target=_target(),
        days=days,
        notices=(),
    )
    block = NutritionBlock(reason_code=NutritionBlockReason.pregnant, message_es="x")
    with pytest.raises(ValidationError):
        MealPlanOutcome(plan=plan, block=block)
    assert MealPlanOutcome(plan=plan, block=None).plan is plan
    assert MealPlanOutcome(plan=None, block=block).block is block


def test_food_requires_unit_grams_and_name_together() -> None:
    with pytest.raises(ValidationError):
        Food(
            id="test_food",
            name_es="Alimento de prueba",
            category=FoodCategory.fruits,
            fdc_id=1,
            per_100g=_macro_totals(),
            diet_types=(DietType.omnivore,),
            macro_role=FoodMacroRole.produce,
            typical_portion_g=100.0,
            unit_grams=50.0,
            unit_name_es=None,
        )
    with pytest.raises(ValidationError):
        Food(
            id="test_food",
            name_es="Alimento de prueba",
            category=FoodCategory.fruits,
            fdc_id=1,
            per_100g=_macro_totals(),
            diet_types=(DietType.omnivore,),
            macro_role=FoodMacroRole.produce,
            typical_portion_g=100.0,
            unit_grams=None,
            unit_name_es="unidad",
        )


def test_food_valid() -> None:
    food = Food(
        id="test_food",
        name_es="Alimento de prueba",
        category=FoodCategory.fruits,
        fdc_id=1,
        per_100g=_macro_totals(),
        diet_types=(DietType.omnivore,),
        macro_role=FoodMacroRole.produce,
        typical_portion_g=100.0,
    )
    assert food.unit_grams is None
    assert food.unit_name_es is None
