"""Programas guardados: persistencia del plan del motor, edición, activación y operaciones."""

import copy
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from forja_engine import Tables
from forja_engine import models as em
from forja_engine.normalize import normalize_input
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import encode_cursor
from app.core.errors import conflict, not_found
from app.core.ids import uuid7
from app.models.program import (
    Program,
    ProgramBlock,
    ProgramDay,
    ProgramExercise,
    ProgramWeek,
)
from app.models.user import User
from app.schemas import api
from app.services import catalog as catalog_service
from app.services import engine

MIN_ENGINE_WEEKS = 4
MANUAL_TEMPLATE = "manual"
MANUAL_TARGET_RIR = 2
WORKING_KINDS = frozenset({"main", "superset", "circuit"})


# ------------------------------------------------------------------ árbol persistido
@dataclass
class ProgramTree:
    program: Program
    weeks: list[ProgramWeek] = field(default_factory=list)
    days: dict[uuid.UUID, list[ProgramDay]] = field(default_factory=dict)
    blocks: dict[uuid.UUID, list[ProgramBlock]] = field(default_factory=dict)
    exercises: dict[uuid.UUID, list[ProgramExercise]] = field(default_factory=dict)

    def all_days(self) -> list[ProgramDay]:
        return [d for w in self.weeks for d in self.days.get(w.id, [])]

    def locate_day(self, day_id: uuid.UUID) -> tuple[ProgramWeek, ProgramDay] | None:
        for week in self.weeks:
            for day in self.days.get(week.id, []):
                if day.id == day_id:
                    return week, day
        return None

    def exercise_ids(self) -> list[str]:
        ids: list[str] = []
        for group in self.exercises.values():
            for ex in group:
                ids.append(ex.exercise_id)
                ids.extend(ex.alternatives)
        return ids


async def get_owned(db: AsyncSession, user: User, program_id: uuid.UUID) -> Program:
    program = await db.get(Program, program_id)
    if program is None or program.user_id != user.id:
        raise not_found("El programa no existe.")
    return program


async def load_tree(db: AsyncSession, program: Program) -> ProgramTree:
    tree = ProgramTree(program=program)
    tree.weeks = list(
        (
            await db.execute(
                select(ProgramWeek)
                .where(ProgramWeek.program_id == program.id)
                .order_by(ProgramWeek.index)
            )
        ).scalars()
    )
    week_ids = [w.id for w in tree.weeks]
    if not week_ids:
        return tree
    day_rows = await db.execute(
        select(ProgramDay)
        .where(ProgramDay.week_id.in_(week_ids))
        .order_by(ProgramDay.week_id, ProgramDay.index)
    )
    for day in day_rows.scalars():
        tree.days.setdefault(day.week_id, []).append(day)
    day_ids = [d.id for d in tree.all_days()]
    if not day_ids:
        return tree
    block_rows = await db.execute(
        select(ProgramBlock)
        .where(ProgramBlock.day_id.in_(day_ids))
        .order_by(ProgramBlock.day_id, ProgramBlock.order)
    )
    for block in block_rows.scalars():
        tree.blocks.setdefault(block.day_id, []).append(block)
    block_ids = [b.id for group in tree.blocks.values() for b in group]
    if not block_ids:
        return tree
    exercise_rows = await db.execute(
        select(ProgramExercise)
        .where(ProgramExercise.block_id.in_(block_ids))
        .order_by(ProgramExercise.block_id, ProgramExercise.order)
    )
    for ex in exercise_rows.scalars():
        tree.exercises.setdefault(ex.block_id, []).append(ex)
    return tree


# ------------------------------------------------------------------------- DTOs
def summary_dto(p: Program) -> api.ProgramSummary:
    return api.ProgramSummary(
        id=p.id,
        name=p.name,
        source=cast("Any", p.source),
        goal=cast("Any", p.goal),
        days_per_week=p.days_per_week,
        weeks_count=p.weeks,
        is_active=p.is_active,
        archived_at=p.archived_at,
        generator_version=p.generator_version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _exercise_dto(ex: ProgramExercise) -> api.ProgramExercise:
    return api.ProgramExercise(
        id=ex.id,
        order=ex.order,
        exercise_id=ex.exercise_id,
        sets=ex.sets,
        rep_min=ex.rep_min,
        rep_max=ex.rep_max,
        duration_s=ex.duration_s,
        per_side=ex.per_side,
        target_rir=ex.target_rir,
        tempo=ex.tempo,
        rest_s=ex.rest_s,
        load_hint=ex.load_hint,
        notes_es=ex.notes_es,
        alternatives=cast("Any", list(ex.alternatives)),
    )


def day_dto(tree: ProgramTree, day: ProgramDay) -> api.ProgramDay:
    return api.ProgramDay(
        id=day.id,
        index=day.index,
        name=day.name,
        focus=day.focus,
        weekday=cast("Any", day.weekday),
        is_recovery=day.is_recovery,
        estimated_minutes=day.estimated_minutes,
        blocks=[
            api.ProgramBlock(
                id=block.id,
                order=block.order,
                kind=cast("Any", block.kind),
                rounds=block.rounds,
                rest_between_rounds_s=block.rest_between_rounds_s,
                exercises=[_exercise_dto(ex) for ex in tree.exercises.get(block.id, [])],
            )
            for block in tree.blocks.get(day.id, [])
        ],
    )


async def detail_dto(db: AsyncSession, user: User, tree: ProgramTree) -> api.ProgramDetail:
    p = tree.program
    summaries = await catalog_service.summaries_for(db, tree.exercise_ids(), user.id)
    return api.ProgramDetail(
        **summary_dto(p).model_dump(),
        seed=p.seed,
        tables_hash=p.tables_hash,
        generator_input=api.GeneratorInput.model_validate(p.generator_input)
        if p.generator_input
        else None,
        weeks=[
            api.ProgramWeek(
                id=w.id,
                index=w.index,
                phase=cast("Any", w.phase),
                days=[day_dto(tree, d) for d in tree.days.get(w.id, [])],
            )
            for w in tree.weeks
        ],
        weekly_volume=[api.GroupVolume.model_validate(v) for v in p.weekly_volume],
        warnings=[api.PlanWarning.model_validate(w) for w in p.warnings],
        rationale_es=list(p.rationale_es),
        exercises=summaries,
    )


async def get_detail(db: AsyncSession, user: User, program_id: uuid.UUID) -> api.ProgramDetail:
    program = await get_owned(db, user, program_id)
    return await detail_dto(db, user, await load_tree(db, program))


# ---------------------------------------------------- plan del motor ⇄ filas de BD
def _json(value: Any) -> Any:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


@dataclass
class RowBatch:
    """Filas nuevas por nivel; sin ``relationship()`` el ORM no ordena las inserciones por FK."""

    weeks: list[ProgramWeek] = field(default_factory=list)
    days: list[ProgramDay] = field(default_factory=list)
    blocks: list[ProgramBlock] = field(default_factory=list)
    exercises: list[ProgramExercise] = field(default_factory=list)

    async def flush(self, db: AsyncSession) -> None:
        for group in (self.weeks, self.days, self.blocks, self.exercises):
            db.add_all(group)
            await db.flush()


def _plan_rows(program: Program, plan: em.ProgramPlan) -> RowBatch:
    batch = RowBatch()
    for week in plan.weeks:
        week_row = ProgramWeek(
            id=uuid7(),
            program_id=program.id,
            index=week.index,
            phase=week.phase.value,
            target_rir=week.target_rir,
            volume_ratio=Decimal(str(round(week.volume_ratio, 2))),
        )
        batch.weeks.append(week_row)
        for day in week.days:
            day_row = ProgramDay(
                id=uuid7(),
                week_id=week_row.id,
                index=day.index,
                template=day.template,
                name=day.name_es,
                focus=day.focus_es or None,
                weekday=day.weekday.value if day.weekday else None,
                is_recovery=day.is_recovery,
                estimated_minutes=day.estimated_minutes,
            )
            batch.days.append(day_row)
            _add_block_rows(batch, day_row.id, day)
    return batch


def _add_block_rows(batch: RowBatch, day_id: uuid.UUID, day: em.PlanDay) -> None:
    for block in day.blocks:
        block_row = ProgramBlock(
            id=uuid7(),
            day_id=day_id,
            order=block.order,
            kind=block.kind.value,
            rounds=block.rounds,
            rest_between_rounds_s=block.rest_between_rounds_s,
        )
        batch.blocks.append(block_row)
        for ex in block.exercises:
            batch.exercises.append(
                ProgramExercise(
                    id=uuid7(),
                    block_id=block_row.id,
                    order=ex.order,
                    exercise_id=ex.exercise_id,
                    slot=_json(ex.slot),
                    sets=ex.sets,
                    rep_min=ex.rep_min,
                    rep_max=ex.rep_max,
                    target_rir=ex.target_rir,
                    tempo=ex.tempo,
                    rest_s=ex.rest_s,
                    duration_s=ex.duration_s,
                    per_side=ex.per_side,
                    load_hint=ex.load_hint,
                    notes_es=ex.notes_es,
                    alternatives=list(ex.alternatives),
                )
            )


def _program_fields(plan: em.ProgramPlan) -> dict[str, Any]:
    return {
        "weekly_volume": [_json(v) for v in plan.weekly_volume],
        "warnings": [_json(w) for w in plan.warnings],
        "rationale_es": list(plan.rationale_es),
    }


async def _deactivate_others(db: AsyncSession, user: User, keep: uuid.UUID | None) -> None:
    stmt = update(Program).where(Program.user_id == user.id, Program.is_active.is_(True))
    if keep is not None:
        stmt = stmt.where(Program.id != keep)
    await db.execute(stmt.values(is_active=False))


async def save_generated(
    db: AsyncSession, user: User, plan: em.ProgramPlan, name: str, *, activate: bool
) -> Program:
    program = Program(
        id=uuid7(),
        user_id=user.id,
        name=name,
        source="generated",
        generator_input=plan.input.model_dump(mode="json"),
        generator_version=plan.engine_version,
        tables_hash=plan.tables_hash,
        seed=plan.seed,
        goal=plan.input.goal.value,
        days_per_week=len(plan.weeks[0].days),
        weeks=len(plan.weeks),
        is_active=False,
        **_program_fields(plan),
    )
    if activate:
        await _deactivate_others(db, user, None)
        program.is_active = True
    db.add(program)
    await db.flush()
    await _plan_rows(program, plan).flush(db)
    return program


def _tree_plan_dict(tree: ProgramTree, tables: Tables) -> dict[str, Any]:
    p = tree.program
    if p.generator_input:
        input_dict = p.generator_input
    else:
        raw = em.GeneratorInput(
            goal=em.Goal(p.goal or "general_fitness"),
            days_per_week=p.days_per_week,
            sex=em.Sex.UNSPECIFIED,
            experience=em.Experience.INTERMEDIATE,
            session_minutes=60,
            equipment=em.EquipmentSelection(preset=em.EquipmentPreset.FULL_GYM, items=()),
            weeks=max(MIN_ENGINE_WEEKS, p.weeks),
        )
        input_dict = normalize_input(raw, tables).model_dump(mode="json")
    weeks: list[dict[str, Any]] = []
    for w in tree.weeks:
        days: list[dict[str, Any]] = []
        for d in tree.days.get(w.id, []):
            blocks = [
                {
                    "order": b.order,
                    "kind": b.kind,
                    "rounds": b.rounds,
                    "rest_between_rounds_s": b.rest_between_rounds_s,
                    "exercises": [
                        {
                            "order": ex.order,
                            "slot": ex.slot,
                            "exercise_id": ex.exercise_id,
                            "sets": ex.sets,
                            "rep_min": ex.rep_min,
                            "rep_max": ex.rep_max,
                            "duration_s": ex.duration_s,
                            "per_side": ex.per_side,
                            "target_rir": ex.target_rir,
                            "tempo": ex.tempo,
                            "rest_s": ex.rest_s,
                            "load_hint": ex.load_hint,
                            "notes_es": ex.notes_es,
                            "alternatives": list(ex.alternatives),
                        }
                        for ex in tree.exercises.get(b.id, [])
                    ],
                }
                for b in tree.blocks.get(d.id, [])
            ]
            days.append(
                {
                    "index": d.index,
                    "template": d.template or MANUAL_TEMPLATE,
                    "name_es": d.name,
                    "focus_es": d.focus or "",
                    "weekday": d.weekday,
                    "is_recovery": d.is_recovery,
                    "estimated_minutes": d.estimated_minutes,
                    "blocks": blocks,
                    "volume": [],
                }
            )
        weeks.append(
            {
                "index": w.index,
                "phase": w.phase,
                "target_rir": w.target_rir,
                "volume_ratio": float(w.volume_ratio),
                "days": days,
            }
        )
    weeks = _pad_weeks(weeks)
    return {
        "engine_version": p.generator_version or engine.ENGINE_VERSION,
        "tables_hash": p.tables_hash or "0" * 64,
        "seed": p.seed or 0,
        "input": input_dict,
        "split": [d["template"] for d in weeks[0]["days"]],
        "weeks": weeks,
        "weekly_volume": p.weekly_volume,
        "warnings": p.warnings,
        "rationale_es": list(p.rationale_es),
    }


def _pad_weeks(weeks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """El motor exige ≥ 4 semanas: un programa manual más corto se rellena solo para validar."""
    padded = list(weeks)
    while len(padded) < MIN_ENGINE_WEEKS:
        clone = copy.deepcopy(weeks[0])
        clone["index"] = len(padded)
        padded.append(clone)
    return padded


def tree_to_plan(tree: ProgramTree, tables: Tables) -> em.ProgramPlan:
    return em.ProgramPlan.model_validate(_tree_plan_dict(tree, tables))


# --------------------------------------------------------------- listado y ciclo de vida
async def list_programs(
    db: AsyncSession, user: User, *, archived: bool, cursor: dict[str, Any] | None, limit: int
) -> api.ProgramPage:
    stmt = select(Program).where(Program.user_id == user.id)
    stmt = stmt.where(
        Program.archived_at.is_not(None) if archived else Program.archived_at.is_(None)
    )
    if cursor:
        active = bool(cursor["a"])
        created = datetime.fromisoformat(str(cursor["c"]))
        last = uuid.UUID(str(cursor["i"]))
        older = (Program.created_at < created) | (
            (Program.created_at == created) & (Program.id < last)
        )
        stmt = stmt.where(
            (Program.is_active.is_(True) & older) | Program.is_active.is_(False)
            if active
            else Program.is_active.is_(False) & older
        )
    stmt = stmt.order_by(Program.is_active.desc(), Program.created_at.desc(), Program.id.desc())
    rows = list((await db.execute(stmt.limit(limit + 1))).scalars())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        tail = rows[-1]
        next_cursor = encode_cursor(
            {"a": int(tail.is_active), "c": tail.created_at.isoformat(), "i": str(tail.id)}
        )
    return api.ProgramPage(items=[summary_dto(p) for p in rows], next_cursor=next_cursor)


async def rename_or_archive(
    db: AsyncSession, user: User, program_id: uuid.UUID, body: api.ProgramUpdate
) -> api.ProgramSummary:
    program = await get_owned(db, user, program_id)
    if body.name is not None:
        program.name = body.name
    if body.archived is True:
        program.archived_at = program.archived_at or datetime.now(UTC)
        program.is_active = False
    elif body.archived is False:
        program.archived_at = None
    program.updated_at = datetime.now(UTC)
    await db.commit()
    return summary_dto(program)


async def delete_program(db: AsyncSession, user: User, program_id: uuid.UUID) -> None:
    program = await get_owned(db, user, program_id)
    await db.delete(program)
    await db.commit()


async def activate(db: AsyncSession, user: User, program_id: uuid.UUID) -> api.ProgramSummary:
    program = await get_owned(db, user, program_id)
    if program.archived_at is not None:
        raise conflict("conflict", "Un programa archivado no se puede activar.")
    await _deactivate_others(db, user, program.id)
    program.is_active = True
    program.updated_at = datetime.now(UTC)
    await db.commit()
    return summary_dto(program)


async def duplicate(
    db: AsyncSession, user: User, program_id: uuid.UUID, body: api.ProgramDuplicateRequest | None
) -> api.ProgramDetail:
    source = await get_owned(db, user, program_id)
    tree = await load_tree(db, source)
    copy_row = Program(
        id=uuid7(),
        user_id=user.id,
        name=(body.name if body and body.name else f"{source.name} (copia)")[:80],
        source=source.source,
        generator_input=source.generator_input,
        generator_version=source.generator_version,
        tables_hash=source.tables_hash,
        seed=source.seed,
        goal=source.goal,
        days_per_week=source.days_per_week,
        weeks=source.weeks,
        is_active=False,
        weekly_volume=source.weekly_volume,
        warnings=source.warnings,
        rationale_es=source.rationale_es,
    )
    db.add(copy_row)
    await db.flush()
    batch = RowBatch()
    for week in tree.weeks:
        new_week = ProgramWeek(
            id=uuid7(),
            program_id=copy_row.id,
            index=week.index,
            phase=week.phase,
            target_rir=week.target_rir,
            volume_ratio=week.volume_ratio,
        )
        batch.weeks.append(new_week)
        for day in tree.days.get(week.id, []):
            new_day = ProgramDay(
                id=uuid7(),
                week_id=new_week.id,
                index=day.index,
                template=day.template,
                name=day.name,
                focus=day.focus,
                weekday=day.weekday,
                is_recovery=day.is_recovery,
                estimated_minutes=day.estimated_minutes,
            )
            batch.days.append(new_day)
            for block in tree.blocks.get(day.id, []):
                new_block = ProgramBlock(
                    id=uuid7(),
                    day_id=new_day.id,
                    order=block.order,
                    kind=block.kind,
                    rounds=block.rounds,
                    rest_between_rounds_s=block.rest_between_rounds_s,
                )
                batch.blocks.append(new_block)
                for ex in tree.exercises.get(block.id, []):
                    batch.exercises.append(
                        ProgramExercise(
                            id=uuid7(),
                            block_id=new_block.id,
                            order=ex.order,
                            exercise_id=ex.exercise_id,
                            slot=ex.slot,
                            sets=ex.sets,
                            rep_min=ex.rep_min,
                            rep_max=ex.rep_max,
                            target_rir=ex.target_rir,
                            tempo=ex.tempo,
                            rest_s=ex.rest_s,
                            duration_s=ex.duration_s,
                            per_side=ex.per_side,
                            load_hint=ex.load_hint,
                            notes_es=ex.notes_es,
                            alternatives=list(ex.alternatives),
                        )
                    )
    await batch.flush(db)
    await db.commit()
    return await get_detail(db, user, copy_row.id)


# ------------------------------------------------------------- creación desde plan
async def create_from_plan(
    db: AsyncSession,
    user: User,
    body: api.ProgramCreateFromPlan,
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
) -> api.ProgramDetail:
    plan = engine.to_engine_plan(body.plan)
    violations = await engine.validate(catalog, tables, plan)
    if violations:
        raise engine.plan_invalid(violations)
    program = await save_generated(db, user, plan, body.name, activate=body.activate)
    await db.commit()
    return await get_detail(db, user, program.id)


def _edit_block_dicts(
    blocks: Sequence[api.BlockEdit], old_slots: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for b_index, block in enumerate(blocks):
        result.append(
            {
                "order": b_index,
                "kind": block.kind,
                "rounds": block.rounds,
                "rest_between_rounds_s": block.rest_between_rounds_s,
                "exercises": [
                    {
                        **ex.model_dump(mode="json"),
                        "order": e_index,
                        "slot": old_slots.get(ex.exercise_id),
                    }
                    for e_index, ex in enumerate(block.exercises)
                ],
            }
        )
    return result


def _manual_day_dict(index: int, day: api.DayEdit, old_slots: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": index,
        "template": MANUAL_TEMPLATE,
        "name_es": day.name,
        "focus_es": day.focus or "",
        "weekday": day.weekday,
        "is_recovery": False,
        "estimated_minutes": 1,
        "blocks": _edit_block_dicts(day.blocks, old_slots),
        "volume": [],
    }


async def create_manual(
    db: AsyncSession,
    user: User,
    body: api.ProgramCreateManual,
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
) -> api.ProgramDetail:
    days = [_manual_day_dict(i, d, {}) for i, d in enumerate(body.days)]
    weeks = [
        {
            "index": w,
            "phase": "accumulation",
            "target_rir": MANUAL_TARGET_RIR,
            "volume_ratio": 1.0,
            "days": copy.deepcopy(days),
        }
        for w in range(body.weeks)
    ]
    raw = em.GeneratorInput(
        goal=em.Goal(body.goal or "general_fitness"),
        days_per_week=len(body.days),
        sex=em.Sex.UNSPECIFIED,
        experience=em.Experience.INTERMEDIATE,
        session_minutes=60,
        equipment=em.EquipmentSelection(preset=em.EquipmentPreset.FULL_GYM, items=()),
        weeks=max(MIN_ENGINE_WEEKS, body.weeks),
    )
    plan = em.ProgramPlan.model_validate(
        {
            "engine_version": engine.ENGINE_VERSION,
            "tables_hash": "0" * 64,
            "seed": 0,
            "input": normalize_input(raw, tables).model_dump(mode="json"),
            "split": [MANUAL_TEMPLATE] * len(days),
            "weeks": _pad_weeks(weeks),
            "weekly_volume": [],
            "warnings": [],
            "rationale_es": [],
        }
    )
    violations = await engine.validate(catalog, tables, plan)
    if violations:
        raise engine.plan_invalid(violations)
    plan = await engine.rebalance(catalog, tables, plan)
    plan = plan.model_copy(update={"weeks": plan.weeks[: body.weeks]})
    program = Program(
        id=uuid7(),
        user_id=user.id,
        name=body.name,
        source="manual",
        generator_input=None,
        generator_version=None,
        tables_hash=None,
        seed=None,
        goal=body.goal,
        days_per_week=len(body.days),
        weeks=body.weeks,
        is_active=False,
        **_program_fields(plan),
    )
    if body.activate:
        await _deactivate_others(db, user, None)
        program.is_active = True
    db.add(program)
    await db.flush()
    await _plan_rows(program, plan).flush(db)
    await db.commit()
    return await get_detail(db, user, program.id)


# ------------------------------------------------------------- sincronizar cambios
async def sync_tree(
    db: AsyncSession,
    tree: ProgramTree,
    new_plan: em.ProgramPlan,
    changed: set[tuple[int, int]],
) -> None:
    """Escribe en BD el plan resultante de una operación del motor.

    Solo se reescriben bloques y ejercicios de los días en ``changed`` (semana, día): así los
    demás conservan sus ids y las series registradas siguen vinculadas.
    """
    program = tree.program
    program.weekly_volume = [_json(v) for v in new_plan.weekly_volume]
    program.warnings = [_json(w) for w in new_plan.warnings]
    program.updated_at = datetime.now(UTC)
    rows = {w.index: w for w in tree.weeks}
    batch = RowBatch()
    for week in new_plan.weeks:
        week_row = rows.get(week.index)
        if week_row is None:  # semanas de relleno de programas manuales cortos
            continue
        week_row.volume_ratio = Decimal(str(round(week.volume_ratio, 2)))
        day_rows = {d.index: d for d in tree.days.get(week_row.id, [])}
        for day in week.days:
            day_row = day_rows[day.index]
            day_row.name = day.name_es
            day_row.focus = day.focus_es or None
            day_row.weekday = day.weekday.value if day.weekday else None
            day_row.estimated_minutes = day.estimated_minutes
            if (week.index, day.index) in changed:
                await db.execute(delete(ProgramBlock).where(ProgramBlock.day_id == day_row.id))
                _add_block_rows(batch, day_row.id, day)
    await batch.flush(db)


# ---------------------------------------------------------------- operaciones de motor
async def regenerate_day(
    db: AsyncSession,
    user: User,
    program_id: uuid.UUID,
    body: api.RegenerateDayRequest,
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
) -> api.ProgramDetail:
    program = await get_owned(db, user, program_id)
    if program.generator_input is None:
        raise conflict("program_not_generated", "Solo los programas generados se pueden regenerar.")
    tree = await load_tree(db, program)
    plan = await engine.rebalance(catalog, tables, tree_to_plan(tree, tables))
    result = await engine.regenerate_day(catalog, tables, plan, body.day_index, body.seed)
    changed = {(w.index, body.day_index) for w in result.weeks}
    await sync_tree(db, tree, result, changed)
    await db.commit()
    return await get_detail(db, user, program_id)


async def swap(
    db: AsyncSession,
    user: User,
    program_id: uuid.UUID,
    body: api.SwapRequest,
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
) -> api.ProgramDetail:
    program = await get_owned(db, user, program_id)
    if program.generator_input is None:
        raise conflict(
            "program_not_generated", "Solo los programas generados admiten cambios automáticos."
        )
    tree = await load_tree(db, program)
    address = _address_of(tree, body.program_exercise_id)
    plan = await engine.rebalance(catalog, tables, tree_to_plan(tree, tables))
    result = await engine.swap_exercise(
        catalog,
        tables,
        plan,
        address,
        [value.root for value in body.exclude_ids],
        body.replacement_id.root if body.replacement_id else None,
        apply_to_all_weeks=body.apply_to_all_weeks,
    )
    changed = (
        {(w.index, address.day_index) for w in result.weeks}
        if body.apply_to_all_weeks
        else {(address.week_index, address.day_index)}
    )
    await sync_tree(db, tree, result, changed)
    await db.commit()
    return await get_detail(db, user, program_id)


def _address_of(tree: ProgramTree, program_exercise_id: uuid.UUID) -> em.SlotAddress:
    for day in tree.all_days():
        for block in tree.blocks.get(day.id, []):
            for ex in tree.exercises.get(block.id, []):
                if ex.id == program_exercise_id:
                    week = next(w for w in tree.weeks if day in tree.days.get(w.id, []))
                    return em.SlotAddress(
                        week_index=week.index,
                        day_index=day.index,
                        block_order=block.order,
                        exercise_order=ex.order,
                    )
    raise not_found("El ejercicio del programa no existe.")


def _adapt_for_week(
    blocks: list[dict[str, Any]], source_week: ProgramWeek, target_week: ProgramWeek
) -> list[dict[str, Any]]:
    """Copia la estructura de un día a otra semana re-periodizando series y RIR."""
    ratio = float(target_week.volume_ratio) / max(float(source_week.volume_ratio), 0.01)
    adapted = copy.deepcopy(blocks)
    for block in adapted:
        working = block["kind"] in WORKING_KINDS
        for ex in block["exercises"]:
            if working:
                ex["sets"] = max(1, min(10, round(ex["sets"] * ratio)))
                if ex["target_rir"] is not None:
                    ex["target_rir"] = target_week.target_rir
    return adapted


async def replace_day(
    db: AsyncSession,
    user: User,
    program_id: uuid.UUID,
    day_id: uuid.UUID,
    body: api.DayEdit,
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
) -> api.ProgramDetail:
    program = await get_owned(db, user, program_id)
    tree = await load_tree(db, program)
    located = tree.locate_day(day_id)
    if located is None:
        raise not_found("El día no existe.")
    week_row, day_row = located
    old_plan = tree_to_plan(tree, tables)
    old_day = next(
        d
        for w in old_plan.weeks
        if w.index == week_row.index
        for d in w.days
        if d.index == day_row.index
    )
    old_slots = {
        ex.exercise_id: ex.slot.model_dump(mode="json")
        for block in old_day.blocks
        for ex in block.exercises
        if ex.slot is not None
    }
    blocks = _edit_block_dicts(body.blocks, old_slots)
    changed: set[tuple[int, int]] = {(week_row.index, day_row.index)}
    weeks_by_index = {w.index: w for w in tree.weeks}
    new_weeks: list[dict[str, Any]] = []
    for week in old_plan.weeks:
        week_dict = week.model_dump(mode="json")
        for day in week_dict["days"]:
            if day["index"] != day_row.index:
                continue
            if week.index == week_row.index:
                target_blocks = blocks
            elif body.apply_to_all_weeks and week.index in weeks_by_index:
                target_blocks = _adapt_for_week(blocks, week_row, weeks_by_index[week.index])
                changed.add((week.index, day_row.index))
            else:
                continue
            day["blocks"] = target_blocks
            day["name_es"] = body.name
            day["focus_es"] = body.focus or ""
            day["weekday"] = body.weekday
        new_weeks.append(week_dict)
    edited = em.ProgramPlan.model_validate({**old_plan.model_dump(mode="json"), "weeks": new_weeks})
    violations = await engine.validate(catalog, tables, edited)
    if violations:
        raise engine.plan_invalid(violations)
    result = await engine.rebalance(catalog, tables, edited)
    await sync_tree(db, tree, result, changed)
    await db.commit()
    return await get_detail(db, user, program_id)
