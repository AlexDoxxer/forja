"""Snapshots (golden files) de 6 perfiles representativos.

El motor es puro y determinista, así que la salida completa de `plan_week` para una entrada
y semilla fijas queda congelada en `tests/golden/*.json`. Para regenerarlos tras un cambio
intencionado (que debe subir `NUTRITION_VERSION`): `UPDATE_GOLDEN=1 uv run pytest
tests/test_snapshots.py` y revisar el diff.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from forja_nutrition.models import (
    ActivityLevel,
    Allergen,
    DietType,
    NutritionGoal,
    NutritionInput,
    NutritionNoticeCode,
    NutritionPace,
    Sex,
)
from forja_nutrition.planner import plan_week
from tests.conftest import MONDAY

GOLDEN_DIR = Path(__file__).parent / "golden"
_FLOAT_DIGITS = 6

PROFILES: dict[str, NutritionInput] = {
    "hombre_mantenimiento_omnivoro": NutritionInput(
        sex=Sex.male,
        age_years=34,
        height_cm=178.0,
        weight_kg=80.0,
        activity_level=ActivityLevel.moderate,
        training_days_per_week=4,
        goal=NutritionGoal.maintain,
        pace=NutritionPace.standard,
        diet_type=DietType.omnivore,
        meals_per_day=3,
        seed=101,
    ),
    "mujer_lose_cerca_del_suelo": NutritionInput(
        sex=Sex.female,
        age_years=45,
        height_cm=155.0,
        weight_kg=52.0,
        activity_level=ActivityLevel.sedentary,
        training_days_per_week=0,
        goal=NutritionGoal.lose,
        pace=NutritionPace.standard,
        diet_type=DietType.omnivore,
        meals_per_day=4,
        seed=102,
    ),
    "vegana_alergia_frutos_secos": NutritionInput(
        sex=Sex.female,
        age_years=29,
        height_cm=166.0,
        weight_kg=60.0,
        activity_level=ActivityLevel.light,
        training_days_per_week=3,
        goal=NutritionGoal.maintain,
        pace=NutritionPace.gentle,
        diet_type=DietType.vegan,
        meals_per_day=4,
        allergens=(Allergen.tree_nuts,),
        seed=103,
    ),
    "vegetariano_ganancia_5_comidas": NutritionInput(
        sex=Sex.male,
        age_years=24,
        height_cm=182.0,
        weight_kg=72.0,
        activity_level=ActivityLevel.high,
        training_days_per_week=5,
        goal=NutritionGoal.gain,
        pace=NutritionPace.standard,
        diet_type=DietType.vegetarian,
        meals_per_day=5,
        seed=104,
    ),
    "pescetariana_recomposicion_sin_sexo": NutritionInput(
        sex=Sex.unspecified,
        age_years=38,
        height_cm=170.0,
        weight_kg=68.0,
        activity_level=ActivityLevel.moderate,
        training_days_per_week=3,
        goal=NutritionGoal.recomp,
        pace=NutritionPace.standard,
        diet_type=DietType.pescatarian,
        meals_per_day=4,
        excluded_food_ids=("atun_lata",),
        seed=105,
    ),
    "mujer_imc_bajo_lose_pasa_a_mantener": NutritionInput(
        sex=Sex.female,
        age_years=26,
        height_cm=175.0,
        weight_kg=54.0,
        activity_level=ActivityLevel.light,
        training_days_per_week=2,
        goal=NutritionGoal.lose,
        pace=NutritionPace.standard,
        diet_type=DietType.omnivore,
        meals_per_day=3,
        seed=106,
    ),
}


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, _FLOAT_DIGITS)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    return value


def _snapshot_of(nutrition_input: NutritionInput) -> Any:
    outcome = plan_week(nutrition_input, MONDAY)
    assert outcome.plan is not None
    return _round_floats(outcome.plan.model_dump(mode="json"))


@pytest.mark.parametrize("name", sorted(PROFILES))
def test_plan_matches_golden_snapshot(name: str) -> None:
    snapshot = _snapshot_of(PROFILES[name])
    golden_path = GOLDEN_DIR / f"{name}.json"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        golden_path.write_text(
            json.dumps(snapshot, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert snapshot == expected


def test_snapshot_profiles_cover_the_required_cases() -> None:
    assert len(PROFILES) == 6
    vegan = PROFILES["vegana_alergia_frutos_secos"]
    assert vegan.diet_type == DietType.vegan
    assert Allergen.tree_nuts in vegan.allergens
    near_floor = _snapshot_of(PROFILES["mujer_lose_cerca_del_suelo"])
    target = near_floor["target"]
    assert target["target_kcal"] >= 1200.0
    low_bmi = _snapshot_of(PROFILES["mujer_imc_bajo_lose_pasa_a_mantener"])
    assert low_bmi["target"]["requested_goal"] == "lose"
    assert low_bmi["target"]["effective_goal"] == "maintain"
    codes = {n["code"] for n in low_bmi["notices"]}
    assert NutritionNoticeCode.lose_blocked_low_bmi.value in codes
