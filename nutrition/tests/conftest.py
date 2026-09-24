"""Fixtures y factorías compartidas por los tests del motor de nutrición."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from forja_nutrition.models import (
    ActivityLevel,
    DietType,
    NutritionGoal,
    NutritionInput,
    NutritionPace,
    Sex,
)

MONDAY = date(2026, 9, 28)
assert MONDAY.weekday() == 0


def make_input(**overrides: Any) -> NutritionInput:
    base: dict[str, Any] = {
        "sex": Sex.male,
        "age_years": 30,
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "activity_level": ActivityLevel.moderate,
        "training_days_per_week": 3,
        "goal": NutritionGoal.maintain,
        "pace": NutritionPace.standard,
        "diet_type": DietType.omnivore,
        "meals_per_day": 3,
    }
    base.update(overrides)
    return NutritionInput(**base)


@pytest.fixture
def monday() -> date:
    return MONDAY
