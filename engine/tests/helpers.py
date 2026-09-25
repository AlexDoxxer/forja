"""Utilidades compartidas por los tests del motor: catálogo de fixture e invariantes."""

import json
import math
from functools import cache
from pathlib import Path

from forja_engine import validate_plan
from forja_engine.models import (
    EquipmentPreset,
    EquipmentSelection,
    ExerciseCard,
    Experience,
    GeneratorInput,
    Goal,
    PlanWarningCode,
    ProgramPlan,
    Sex,
    WeekPhase,
)
from forja_engine.tables import Tables, default_tables
from forja_engine.volume import weekly_targets

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CUSTOM_ITEMS = ("dumbbell", "band", "kettlebell")


@cache
def catalog() -> tuple[ExerciseCard, ...]:
    raw = json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))
    return tuple(ExerciseCard.model_validate(card) for card in raw)


def make_input(**overrides: object) -> GeneratorInput:
    """Entrada de referencia (hipertrofia, 4 días, intermedio, gimnasio) con cambios."""
    data: dict[str, object] = {
        "goal": Goal.HYPERTROPHY,
        "days_per_week": 4,
        "sex": Sex.UNSPECIFIED,
        "experience": Experience.INTERMEDIATE,
        "session_minutes": 60,
        "equipment": EquipmentSelection(preset=EquipmentPreset.FULL_GYM),
        "seed": 42,
    }
    data.update(overrides)
    return GeneratorInput.model_validate(data)


def equipment_for(preset: EquipmentPreset) -> EquipmentSelection:
    items = CUSTOM_ITEMS if preset is EquipmentPreset.CUSTOM else ()
    return EquipmentSelection.model_validate({"preset": preset, "items": items})


def assert_plan_invariants(plan: ProgramPlan, tables: Tables | None = None) -> None:
    """Propiedades de §7.8 que debe cumplir cualquier plan generado."""
    tables = tables or default_tables()
    cards = {card.id: card for card in catalog()}
    inp = plan.input
    assert validate_plan(plan, catalog(), tables) == ()
    assert len(plan.weeks) == inp.weeks
    assert plan.weeks[-1].phase is WeekPhase.DELOAD
    assert len(plan.split) == inp.days_per_week
    limit = math.floor(inp.session_minutes * (1 + tables.prescription.time_model.budget_tolerance))
    over_days = {
        w.day_index for w in plan.warnings if w.code is PlanWarningCode.TIME_BUDGET_EXCEEDED
    }
    for week in plan.weeks:
        assert len(week.days) == inp.days_per_week
        for day in week.days:
            assert day.estimated_minutes <= limit or day.index in over_days
            for block in day.blocks:
                for exercise in block.exercises:
                    card = cards[exercise.exercise_id]
                    assert card.id not in inp.excluded_exercise_ids
                    assert card.target_muscle not in inp.avoid_muscles
                    assert card.movement_pattern not in inp.avoid_patterns
                    assert card.equipment_code in inp.equipment.items
                    assert not card.deprecated
    targets = weekly_targets(inp, tables)
    names = {g.value: n for g, n in tables.engine_rules.group_names_es.items()}
    ratio = tables.engine_rules.allocation.volume_warning_ratio
    volume_messages = " ".join(
        w.message_es for w in plan.warnings if w.code is PlanWarningCode.VOLUME_OUT_OF_RANGE
    )
    for entry in plan.weekly_volume:
        target = targets[entry.group].target
        within = abs(entry.planned_sets - target) <= ratio * target
        group_name = names[entry.group.value]
        assert within or f"Volumen semanal de {group_name}:" in volume_messages
