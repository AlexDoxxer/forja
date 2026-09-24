"""`forja_nutrition/safety.py`: bloqueos y suelos de §8.5 (criterio de aceptación de fase)."""

from __future__ import annotations

import pytest

from forja_nutrition.models import NutritionBlockReason, NutritionGoal, Sex
from forja_nutrition.safety import bmi, check_block, effective_goal_for_bmi, kcal_floor
from forja_nutrition.tables import load_nutrition_tables

TABLES = load_nutrition_tables()


def test_check_block_under_18() -> None:
    block = check_block(age_years=17, pregnant=False, breastfeeding=False, tables=TABLES)
    assert block is not None
    assert block.reason_code == NutritionBlockReason.under_18
    assert len(block.message_es) > 10


def test_check_block_pregnant() -> None:
    block = check_block(age_years=30, pregnant=True, breastfeeding=False, tables=TABLES)
    assert block is not None
    assert block.reason_code == NutritionBlockReason.pregnant


def test_check_block_breastfeeding() -> None:
    block = check_block(age_years=30, pregnant=False, breastfeeding=True, tables=TABLES)
    assert block is not None
    assert block.reason_code == NutritionBlockReason.breastfeeding


def test_check_block_none_when_adult_and_not_pregnant_or_breastfeeding() -> None:
    block = check_block(age_years=30, pregnant=False, breastfeeding=False, tables=TABLES)
    assert block is None


def test_check_block_under_18_takes_priority_over_pregnant() -> None:
    # block_if = [pregnant, breastfeeding, under_18] en la tabla real: pregnant se evalúa
    # primero, así que una menor embarazada se bloquea por embarazo.
    block = check_block(age_years=16, pregnant=True, breastfeeding=False, tables=TABLES)
    assert block is not None
    assert block.reason_code == NutritionBlockReason.pregnant


def test_bmi_calculation() -> None:
    assert bmi(weight_kg=70.0, height_cm=175.0) == pytest.approx(22.857, abs=1e-3)


def test_effective_goal_for_bmi_downgrades_lose_below_threshold() -> None:
    goal, blocked = effective_goal_for_bmi(
        goal=NutritionGoal.lose, weight_kg=45.0, height_cm=170.0, tables=TABLES
    )
    assert goal == NutritionGoal.maintain
    assert blocked is True


def test_effective_goal_for_bmi_keeps_lose_above_threshold() -> None:
    goal, blocked = effective_goal_for_bmi(
        goal=NutritionGoal.lose, weight_kg=90.0, height_cm=170.0, tables=TABLES
    )
    assert goal == NutritionGoal.lose
    assert blocked is False


def test_effective_goal_for_bmi_ignores_other_goals() -> None:
    goal, blocked = effective_goal_for_bmi(
        goal=NutritionGoal.gain, weight_kg=45.0, height_cm=170.0, tables=TABLES
    )
    assert goal == NutritionGoal.gain
    assert blocked is False


def test_kcal_floor_uses_bmr_when_higher_than_sex_floor() -> None:
    floor = kcal_floor(sex=Sex.female, bmr_kcal=1800.0, tables=TABLES)
    assert floor == 1800.0


def test_kcal_floor_uses_sex_floor_when_bmr_is_lower() -> None:
    floor = kcal_floor(sex=Sex.female, bmr_kcal=900.0, tables=TABLES)
    assert floor == TABLES.safety.kcal_floor[Sex.female]


def test_kcal_floor_can_ignore_bmr_if_table_says_so() -> None:
    permissive_tables = TABLES.model_copy(
        update={"safety": TABLES.safety.model_copy(update={"kcal_floor_not_below_bmr": False})}
    )
    floor = kcal_floor(sex=Sex.male, bmr_kcal=5000.0, tables=permissive_tables)
    assert floor == TABLES.safety.kcal_floor[Sex.male]
