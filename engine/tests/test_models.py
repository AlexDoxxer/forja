"""F1-ENG-02: DTOs inmutables compatibles con ``contracts/openapi.yaml`` y sus invariantes."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from forja_engine import models
from forja_engine.models import (
    EquipmentPreset,
    EquipmentSelection,
    ExercisePrescription,
    GeneratorInput,
)
from tests.helpers import catalog, make_input

OPENAPI = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"
DTOS = [
    "ExerciseCard",
    "EquipmentSelection",
    "GeneratorInput",
    "ExercisePrescription",
    "SlotRef",
    "PlanExercise",
    "PlanBlock",
    "GroupSets",
    "PlanDay",
    "PlanWeek",
    "GroupVolume",
    "PlanWarning",
    "SlotAddress",
    "ProgramPlan",
    "WarmupSet",
]
ENUMS = [
    "Sex",
    "Experience",
    "Goal",
    "Emphasis",
    "EquipmentPreset",
    "EquipmentCode",
    "EquipmentGroup",
    "MuscleCode",
    "VolumeGroup",
    "MuscleGroup",
    "BodyPart",
    "MovementPattern",
    "Mechanic",
    "ExerciseRole",
    "Laterality",
    "DemoSex",
    "LoadType",
    "Weekday",
    "WeekPhase",
    "BlockKind",
    "PlanWarningCode",
    "SuggestionKind",
]


def _schemas() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    return dict(data["components"]["schemas"])


def _flatten(schema: dict[str, Any], schemas: dict[str, Any]) -> tuple[set[str], set[str]]:
    properties: set[str] = set(schema.get("properties", {}))
    required: set[str] = set(schema.get("required", []))
    for part in schema.get("allOf", []):
        if "$ref" in part:
            part = schemas[part["$ref"].rsplit("/", 1)[-1]]  # noqa: PLW2901
        sub_properties, sub_required = _flatten(part, schemas)
        properties |= sub_properties
        required |= sub_required
    return properties, required


@pytest.mark.parametrize("name", DTOS)
def test_dto_fields_match_openapi(name: str) -> None:
    schemas = _schemas()
    properties, required = _flatten(schemas[name], schemas)
    model: type[BaseModel] = getattr(models, name)
    assert set(model.model_fields) == properties
    assert required <= set(model.model_fields)


@pytest.mark.parametrize("name", ENUMS)
def test_enums_match_openapi(name: str) -> None:
    enum = getattr(models, name)
    assert [member.value for member in enum] == _schemas()[name]["enum"]


def test_dtos_are_frozen() -> None:
    card = catalog()[0]
    with pytest.raises(ValidationError):
        card.id = "9999"  # type: ignore[misc]


def test_fixture_catalog_is_realistic() -> None:
    cards = catalog()
    assert len(cards) >= 150
    assert [c.id for c in cards] == sorted(c.id for c in cards)
    patterns = {c.movement_pattern for c in cards}
    codes = {c.equipment_code for c in cards}
    assert len(patterns) >= 28
    assert codes == set(models.EquipmentCode)


@pytest.mark.parametrize(
    "overrides",
    [
        {"session_minutes": 33},
        {"avoid_muscles": ("chest", "chest")},
        {"preferred_days": ("mon", "tue")},
        {"days_per_week": 8},
        {"equipment": {"preset": "custom", "items": []}},
        {"equipment": {"preset": "full_gym", "items": ["band", "band"]}},
        {"seed": -1},
    ],
)
def test_generator_input_rejects_invalid_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make_input(**overrides)


def test_generator_input_accepts_preferred_days_of_the_right_length() -> None:
    inp = make_input(days_per_week=2, preferred_days=("wed", "mon"))
    assert inp.preferred_days == ("wed", "mon")
    assert EquipmentSelection(preset=EquipmentPreset.BODYWEIGHT).items == ()


def _rx(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "exercise_id": "0001",
        "sets": 3,
        "rep_min": 8,
        "rep_max": 12,
        "duration_s": None,
        "per_side": False,
        "target_rir": 2,
        "tempo": "3-0-1-0",
        "rest_s": 90,
        "load_hint": None,
        "notes_es": None,
        "alternatives": (),
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "overrides",
    [
        {"rep_max": None},
        {"duration_s": 30},
        {"rep_min": None, "rep_max": None},
        {"rep_min": 12, "rep_max": 8},
        {"alternatives": ("0002", "0002")},
        {"tempo": "3-0-1"},
    ],
)
def test_prescription_invariants(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ExercisePrescription.model_validate(_rx(**overrides))


def test_prescription_by_duration_is_valid() -> None:
    rx = ExercisePrescription.model_validate(_rx(rep_min=None, rep_max=None, duration_s=30))
    assert rx.duration_s == 30


def test_card_rejects_duplicate_secondaries() -> None:
    data = catalog()[0].model_dump()
    data["secondary_muscles"] = ("abs", "abs")
    with pytest.raises(ValidationError):
        models.ExerciseCard.model_validate(data)


def test_generator_input_round_trips_through_json() -> None:
    inp = make_input()
    assert GeneratorInput.model_validate_json(inp.model_dump_json()) == inp
