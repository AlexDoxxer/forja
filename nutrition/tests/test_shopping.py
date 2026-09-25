"""`forja_nutrition/shopping.py`: lista de la compra semanal agregada (§8.3)."""

from __future__ import annotations

from datetime import timedelta

from forja_nutrition.energy import calculate_target
from forja_nutrition.models import (
    FoodCategory,
    MacroDeviation,
    MacroTotals,
    Meal,
    MealItem,
    MealPlan,
    MealPlanDay,
    MealSlot,
)
from forja_nutrition.planner import plan_week
from forja_nutrition.shopping import CATEGORY_LABELS_ES, shopping_list
from tests.conftest import MONDAY, make_input


def test_category_labels_cover_every_food_category() -> None:
    assert set(CATEGORY_LABELS_ES) == set(FoodCategory)
    assert all(len(label) > 0 for label in CATEGORY_LABELS_ES.values())


def test_shopping_list_aggregates_grams_across_the_week() -> None:
    outcome = plan_week(make_input(seed=1), MONDAY)
    assert outcome.plan is not None
    plan = outcome.plan

    expected_grams: dict[str, float] = {}
    expected_units: dict[str, int] = {}
    for day in plan.days:
        for meal in day.meals:
            for item in meal.items:
                expected_grams[item.food_id] = expected_grams.get(item.food_id, 0.0) + item.grams
                if item.units is not None:
                    expected_units[item.food_id] = expected_units.get(item.food_id, 0) + item.units

    result = shopping_list(plan)
    assert result.week_start == plan.week_start

    actual_grams: dict[str, float] = {}
    actual_units: dict[str, int] = {}
    for category in result.categories:
        # cada categoría está ordenada alfabéticamente por nombre
        names = [item.name_es for item in category.items]
        assert names == sorted(names)
        for shopping_item in category.items:
            actual_grams[shopping_item.food_id] = round(expected_grams[shopping_item.food_id], 1)
            if shopping_item.units is not None:
                actual_units[shopping_item.food_id] = shopping_item.units

    for food_id, grams in expected_grams.items():
        assert actual_grams[food_id] == round(grams, 1)
    assert actual_units == expected_units


def test_shopping_list_skips_food_ids_missing_from_the_catalog() -> None:
    """`shopping_list` es defensiva ante un `food_id` que no esté en `foods.json` (no debería
    ocurrir con un `MealPlan` generado por `plan_week`, pero no debe romper la agregación)."""
    unknown_item = MealItem(
        food_id="alimento_inexistente",
        name_es="Alimento inexistente",
        grams=100.0,
        nutrients=MacroTotals(kcal=50, protein_g=1, fat_g=1, carbs_g=5, fiber_g=1),
    )
    known_item = MealItem(
        food_id="manzana",
        name_es="Manzana",
        grams=150.0,
        nutrients=MacroTotals(kcal=75, protein_g=0.5, fat_g=0.3, carbs_g=20, fiber_g=3),
    )
    meal = Meal(
        slot=MealSlot.breakfast,
        items=(unknown_item, known_item),
        totals=MacroTotals(kcal=125, protein_g=1.5, fat_g=1.3, carbs_g=25, fiber_g=4),
    )
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
        diet_type=make_input().diet_type,
        meals_per_day=3,
        target=calculate_target(make_input()),
        days=days,
        notices=(),
    )

    result = shopping_list(plan)
    all_ids = {item.food_id for category in result.categories for item in category.items}
    assert "alimento_inexistente" not in all_ids
    assert "manzana" in all_ids


def test_shopping_list_categories_are_non_empty_and_ordered() -> None:
    outcome = plan_week(make_input(seed=2), MONDAY)
    assert outcome.plan is not None
    result = shopping_list(outcome.plan)

    category_order = list(FoodCategory)
    seen_indexes = [category_order.index(cat.category) for cat in result.categories]
    assert seen_indexes == sorted(seen_indexes)
    for category in result.categories:
        assert len(category.items) >= 1
        assert category.label_es == CATEGORY_LABELS_ES[category.category]
