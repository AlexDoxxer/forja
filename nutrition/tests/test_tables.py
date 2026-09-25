"""Validación de `forja_nutrition/tables.py` (ADR 0005): carga real y cada rama de fallo."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from forja_nutrition.tables import NutritionTables, load_nutrition_tables


def _base_table_kwargs() -> dict[str, Any]:
    return {
        "version": 1,
        "activity_factors": {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "high": 1.725,
        },
        "training_days_adjustment": {
            "0": 0.0,
            "1-2": 0.05,
            "3-4": 0.1,
            "5-7": 0.15,
            "cap_factor": 1.9,
        },
        "goal_adjustment": {
            "lose": {"standard": -0.15, "gentle": -0.10, "max_deficit_kcal": 500},
            "gain": {"standard": 0.10, "gentle": 0.05},
            "recomp": {"standard": -0.05, "gentle": 0.0},
            "maintain": {"standard": 0.0, "gentle": 0.0},
        },
        "protein_g_per_kg": {
            "default": 1.8,
            "lose": 2.1,
            "recomp": 2.0,
            "gain": 1.8,
            "min": 1.6,
            "max": 2.2,
        },
        "fat": {"min_g_per_kg": 0.8, "min_pct_kcal": 0.20},
        "fiber_g_per_1000_kcal": 14,
        "safety": {
            "min_age": 18,
            "kcal_floor": {"female": 1200, "male": 1500, "unspecified": 1350},
            "kcal_floor_not_below_bmr": True,
            "block_lose_if_bmi_below": 18.5,
            "block_if": ["pregnant", "breastfeeding", "under_18"],
            "min_meals_per_day": 3,
        },
        "tolerances": {"kcal": 0.05, "macros": 0.10, "macro_sum_vs_kcal": 0.02},
        "rounding": {
            "grams_step": 5,
            "unit_foods": ["egg", "banana", "apple", "orange", "yogurt_unit", "bread_slice"],
        },
        "meal_templates": {
            3: ["breakfast", "lunch", "dinner"],
            4: ["breakfast", "lunch", "snack", "dinner"],
            5: ["breakfast", "mid_morning", "lunch", "snack", "dinner"],
        },
        "meal_kcal_split": {
            3: {"breakfast": 0.25, "lunch": 0.40, "dinner": 0.35},
            4: {"breakfast": 0.25, "lunch": 0.35, "snack": 0.10, "dinner": 0.30},
            5: {
                "breakfast": 0.20,
                "mid_morning": 0.10,
                "lunch": 0.35,
                "snack": 0.10,
                "dinner": 0.25,
            },
        },
    }


def test_base_kwargs_are_valid() -> None:
    NutritionTables.model_validate(_base_table_kwargs())


def test_load_nutrition_tables_loads_packaged_yaml() -> None:
    tables = load_nutrition_tables()
    assert tables.version == 1
    assert tables.meal_templates[3] == ("breakfast", "lunch", "dinner")
    assert tables.training_days_adjustment["cap_factor"] == pytest.approx(1.9)
    # memoized: same object on second call
    assert load_nutrition_tables() is tables


def test_training_days_adjustment_missing_bucket() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    del data["training_days_adjustment"]["5-7"]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_training_days_adjustment_extra_bucket() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    data["training_days_adjustment"]["8-10"] = 0.2
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_meal_templates_missing_size() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    del data["meal_templates"][3]
    del data["meal_kcal_split"][3]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_meal_templates_wrong_length() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    data["meal_templates"][3] = ["breakfast", "lunch"]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_meal_templates_duplicate_slot() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    data["meal_templates"][3] = ["breakfast", "breakfast", "dinner"]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_meal_kcal_split_does_not_sum_to_one() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    data["meal_kcal_split"][3]["dinner"] = 0.5
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_meal_kcal_split_mismatched_slots() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    data["meal_kcal_split"][3] = {"breakfast": 0.5, "lunch": 0.5}
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_goal_adjustment_missing_goal() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    del data["goal_adjustment"]["gain"]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_kcal_floor_missing_sex() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    del data["safety"]["kcal_floor"]["unspecified"]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_activity_factors_missing_level() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    del data["activity_factors"]["high"]
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)


def test_extra_field_is_forbidden() -> None:
    data = copy.deepcopy(_base_table_kwargs())
    data["unexpected_field"] = 1
    with pytest.raises(ValidationError):
        NutritionTables.model_validate(data)
