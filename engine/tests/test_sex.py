"""§7.4: el sexo solo preselecciona y ajusta detalles; nunca excluye ejercicios ni limita cargas."""

import inspect

import pytest

from forja_engine import generate, progression
from forja_engine.models import (
    DemoSex,
    EquipmentPreset,
    ExerciseRole,
    Goal,
    Mechanic,
    Sex,
    SlotRef,
)
from forja_engine.normalize import normalize_input
from forja_engine.select import Selector, UsageState
from forja_engine.tables import default_tables
from tests.helpers import catalog, equipment_for, make_input


@pytest.mark.parametrize("preset", list(EquipmentPreset))
def test_candidate_pool_is_identical_for_every_sex(preset: EquipmentPreset) -> None:
    tables = default_tables()
    order = tables.engine_rules.relaxation_order
    pools: dict[Sex, list[list[str]]] = {}
    for sex in Sex:
        inp = normalize_input(make_input(sex=sex, equipment=equipment_for(preset)), tables)
        selector = Selector(catalog(), inp, tables)
        pools[sex] = [
            [c.id for c in selector.candidates(slot, order[:level], UsageState())]
            for template in tables.split_templates.day_templates.values()
            for slot in (
                SlotRef(
                    slot_index=i, pattern=s.pattern, role=s.role, group=s.group, priority=s.priority
                )
                for i, s in enumerate(template.slots)
            )
            for level in range(len(order) + 1)
        ]
    assert pools[Sex.MALE] == pools[Sex.FEMALE] == pools[Sex.UNSPECIFIED]


@pytest.mark.parametrize("goal", list(Goal))
def test_sex_does_not_change_structure_volume_or_sets(goal: Goal) -> None:
    plans = {
        sex: generate(make_input(goal=goal, sex=sex, session_minutes=120), catalog()) for sex in Sex
    }
    reference = plans[Sex.UNSPECIFIED]
    for plan in plans.values():
        assert plan.split == reference.split
        for week, ref_week in zip(plan.weeks, reference.weeks, strict=True):
            for day, ref_day in zip(week.days, ref_week.days, strict=True):
                slots = [(e.slot, e.sets) for b in day.blocks for e in b.exercises if e.slot]
                ref = [(e.slot, e.sets) for b in ref_day.blocks for e in b.exercises if e.slot]
                assert slots == ref


def test_female_modifiers_only_touch_rest_and_isolation_reps() -> None:
    tables = default_tables()
    cards = {c.id: c for c in catalog()}
    male = generate(make_input(sex=Sex.MALE, seed=7), catalog())
    female = generate(make_input(sex=Sex.FEMALE, seed=7), catalog())
    for m_day, f_day in zip(male.weeks[0].days, female.weeks[0].days, strict=True):
        m = {e.slot: e for b in m_day.blocks for e in b.exercises if e.slot}
        f = {e.slot: e for b in f_day.blocks for e in b.exercises if e.slot}
        for slot, f_ex in f.items():
            m_ex = m.get(slot)
            if m_ex is None or slot.role is not ExerciseRole.ACCESSORY:
                continue
            assert f_ex.rest_s <= m_ex.rest_s
            low = tables.prescription.table[Goal.HYPERTROPHY]["accessory"].rest_s[0]
            assert f_ex.rest_s >= low
            if cards[f_ex.exercise_id].mechanic is Mechanic.ISOLATION and f_ex.rep_max is not None:
                assert (
                    f_ex.rep_max
                    == tables.prescription.table[Goal.HYPERTROPHY]["accessory"].reps[1]
                    + tables.sex_modifiers.female.isolation_rep_max_delta
                )


def test_demonstrator_bonus_prefers_but_never_excludes() -> None:
    tables = default_tables()
    card = next(c for c in catalog() if c.demo_sex is DemoSex.FEMALE)
    slot = SlotRef(
        slot_index=0,
        pattern=card.movement_pattern,
        role=ExerciseRole.ACCESSORY,
        group=tables.muscle_group(card.target_muscle),
        priority=2,
    )
    scores = {}
    for sex in Sex:
        selector = Selector(catalog(), normalize_input(make_input(sex=sex), tables), tables)
        pool = selector.candidates(slot, tables.engine_rules.relaxation_order, UsageState())
        assert card in pool
        scores[sex] = selector.score(card, slot, UsageState())
    assert scores[Sex.FEMALE] == scores[Sex.MALE] + 5
    assert scores[Sex.UNSPECIFIED] == scores[Sex.MALE]


def test_load_functions_never_receive_sex() -> None:
    for function in (progression.suggest, progression.warmup_ramp, progression.estimate_1rm):
        assert "sex" not in inspect.signature(function).parameters
