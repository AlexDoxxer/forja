"""Sesiones de entreno, series, récords personales y sincronización offline (ADR 0006)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, cast

from forja_engine import progression
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import encode_cursor
from app.core.errors import ProblemError, conflict, not_found, unprocessable
from app.core.ids import uuid7
from app.models.catalog import Exercise
from app.models.program import (
    PersonalRecord,
    Program,
    ProgramDay,
    ProgramWeek,
    SetLog,
    WorkoutSession,
)
from app.models.user import User
from app.schemas import api

RECORD_KINDS = ("e1rm", "heaviest_set", "volume")
FINISHED = "session_already_finished"


def _f(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _dec(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


# --------------------------------------------------------------------------- DTOs
def set_dto(row: SetLog, records: Sequence[str] = ()) -> api.SetLog:
    return api.SetLog(
        id=row.id,
        client_uuid=row.client_uuid,
        session_id=row.session_id,
        exercise_id=row.exercise_id,
        program_exercise_id=row.program_exercise_id,
        set_index=row.set_index,
        weight_kg=_f(row.weight_kg),
        reps=row.reps,
        rir=row.rir,
        duration_s=row.duration_s,
        is_warmup=row.is_warmup,
        completed_at=row.completed_at,
        updated_at=row.updated_at,
        records=cast("Any", list(records)),
    )


async def _totals(
    db: AsyncSession, session_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, float]]:
    if not session_ids:
        return {}
    rows = await db.execute(
        select(
            SetLog.session_id,
            func.count(),
            func.coalesce(
                func.sum(func.coalesce(SetLog.weight_kg, 0) * func.coalesce(SetLog.reps, 0)), 0
            ),
        )
        .where(
            SetLog.session_id.in_(session_ids),
            SetLog.deleted_at.is_(None),
            SetLog.is_warmup.is_(False),
        )
        .group_by(SetLog.session_id)
    )
    return {sid: (count, float(volume)) for sid, count, volume in rows}


def _summary(
    row: WorkoutSession, totals: dict[uuid.UUID, tuple[int, float]]
) -> api.WorkoutSessionSummary:
    count, volume = totals.get(row.id, (0, 0.0))
    return api.WorkoutSessionSummary(
        id=row.id,
        client_uuid=row.client_uuid,
        program_id=row.program_id,
        program_day_id=row.program_day_id,
        name=row.name,
        started_at=row.started_at,
        finished_at=row.finished_at,
        status=cast("Any", row.status),
        perceived_effort=row.perceived_effort,
        notes=row.notes,
        set_count=count,
        volume_kg=volume,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def session_dto(db: AsyncSession, row: WorkoutSession) -> api.WorkoutSession:
    totals = await _totals(db, [row.id])
    sets = (
        await db.execute(
            select(SetLog)
            .where(SetLog.session_id == row.id, SetLog.deleted_at.is_(None))
            .order_by(SetLog.completed_at, SetLog.set_index)
        )
    ).scalars()
    return api.WorkoutSession(**_summary(row, totals).model_dump(), sets=[set_dto(s) for s in sets])


async def get_owned_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> WorkoutSession:
    row = await db.get(WorkoutSession, session_id)
    if row is None or row.user_id != user.id:
        raise not_found("La sesión no existe.")
    return row


# ---------------------------------------------------------------------- sesiones
async def _day_context(db: AsyncSession, user: User, day_id: uuid.UUID) -> tuple[uuid.UUID, str]:
    found = (
        await db.execute(
            select(ProgramDay.name, Program.id)
            .join(ProgramWeek, ProgramWeek.id == ProgramDay.week_id)
            .join(Program, Program.id == ProgramWeek.program_id)
            .where(ProgramDay.id == day_id, Program.user_id == user.id)
        )
    ).first()
    if found is None:
        raise not_found("El día del programa no existe.")
    return found[1], found[0]


async def start_session(
    db: AsyncSession, user: User, body: api.WorkoutSessionCreate
) -> api.WorkoutSession:
    existing = (
        await db.execute(
            select(WorkoutSession).where(
                WorkoutSession.user_id == user.id, WorkoutSession.client_uuid == body.client_uuid
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return await session_dto(db, existing)
    program_id: uuid.UUID | None = None
    default_name = "Sesión libre"
    if body.program_day_id is not None:
        program_id, default_name = await _day_context(db, user, body.program_day_id)
    now = datetime.now(UTC)
    row = WorkoutSession(
        id=uuid7(),
        user_id=user.id,
        client_uuid=body.client_uuid,
        program_id=program_id,
        program_day_id=body.program_day_id,
        name=body.name or default_name,
        started_at=body.started_at,
        status="in_progress",
        notes=body.notes,
        client_updated_at=now,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise conflict("conflict", "La sesión ya existe.") from exc
    return await session_dto(db, row)


async def list_sessions(
    db: AsyncSession,
    user: User,
    *,
    from_date: date | None,
    to_date: date | None,
    status: str | None,
    cursor: dict[str, Any] | None,
    limit: int,
) -> api.WorkoutSessionPage:
    stmt = select(WorkoutSession).where(WorkoutSession.user_id == user.id)
    if from_date:
        stmt = stmt.where(WorkoutSession.started_at >= datetime.combine(from_date, time.min, UTC))
    if to_date:
        stmt = stmt.where(
            WorkoutSession.started_at < datetime.combine(to_date + timedelta(days=1), time.min, UTC)
        )
    if status:
        stmt = stmt.where(WorkoutSession.status == status)
    if cursor:
        started = datetime.fromisoformat(str(cursor["s"]))
        last = uuid.UUID(str(cursor["i"]))
        stmt = stmt.where(
            or_(
                WorkoutSession.started_at < started,
                and_(WorkoutSession.started_at == started, WorkoutSession.id < last),
            )
        )
    stmt = stmt.order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc())
    rows = list((await db.execute(stmt.limit(limit + 1))).scalars())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor({"s": rows[-1].started_at.isoformat(), "i": str(rows[-1].id)})
    totals = await _totals(db, [r.id for r in rows])
    return api.WorkoutSessionPage(
        items=[_summary(r, totals) for r in rows], next_cursor=next_cursor
    )


async def update_session(
    db: AsyncSession, user: User, session_id: uuid.UUID, body: api.WorkoutSessionUpdate
) -> api.WorkoutSession:
    row = await get_owned_session(db, user, session_id)
    if body.status == "abandoned":
        if row.status == "completed":
            raise conflict(FINISHED, "La sesión ya está terminada.")
        row.status = "abandoned"
        row.finished_at = row.finished_at or datetime.now(UTC)
    if body.name is not None:
        row.name = body.name
    if body.notes is not None:
        row.notes = body.notes
    if body.perceived_effort is not None:
        row.perceived_effort = body.perceived_effort
    row.client_updated_at = datetime.now(UTC)
    await db.commit()
    return await session_dto(db, row)


async def finish_session(
    db: AsyncSession, user: User, session_id: uuid.UUID, body: api.SessionFinishRequest
) -> api.SessionSummary:
    row = await get_owned_session(db, user, session_id)
    if row.status == "abandoned":
        raise conflict(FINISHED, "La sesión fue abandonada.")
    if row.status == "in_progress":
        if body.finished_at < row.started_at:
            raise unprocessable("validation_error", "finished_at es anterior al inicio.")
        row.status = "completed"
        row.finished_at = body.finished_at
        if body.perceived_effort is not None:
            row.perceived_effort = body.perceived_effort
        if body.notes is not None:
            row.notes = body.notes
        row.client_updated_at = datetime.now(UTC)
        await db.commit()
    totals = await _totals(db, [row.id])
    agg = (
        await db.execute(
            select(
                func.coalesce(func.sum(func.coalesce(SetLog.reps, 0)), 0),
                func.count(func.distinct(SetLog.exercise_id)),
            ).where(
                SetLog.session_id == row.id,
                SetLog.deleted_at.is_(None),
                SetLog.is_warmup.is_(False),
            )
        )
    ).one()
    count, volume = totals.get(row.id, (0, 0.0))
    records = await _records_dto(
        db, select(PersonalRecord).where(PersonalRecord.session_id == row.id)
    )
    finished = row.finished_at or row.started_at
    return api.SessionSummary(
        session=_summary(row, totals),
        duration_s=max(0, int((finished - row.started_at).total_seconds())),
        total_sets=count,
        total_reps=int(agg[0]),
        volume_kg=volume,
        exercises_completed=int(agg[1]),
        new_records=records,
    )


# ------------------------------------------------------------------------ series
async def _check_exercise(db: AsyncSession, exercise_id: str) -> None:
    if await db.get(Exercise, exercise_id) is None:
        raise unprocessable(
            "validation_error",
            "El ejercicio no existe.",
            errors=[
                {
                    "loc": ["body", "exercise_id"],
                    "msg": "Ejercicio inexistente",
                    "type": "not_found",
                }
            ],
        )


async def log_set(
    db: AsyncSession, user: User, session_id: uuid.UUID, body: api.SetLogCreate
) -> api.SetLog:
    session = await get_owned_session(db, user, session_id)
    if session.status != "in_progress":
        raise conflict(FINISHED, "La sesión ya está terminada.")
    existing = (
        await db.execute(select(SetLog).where(SetLog.client_uuid == body.client_uuid))
    ).scalar_one_or_none()
    if existing is not None:
        if existing.session_id != session.id:
            raise conflict("conflict", "Ese client_uuid ya pertenece a otra serie.")
        return set_dto(existing)
    await _check_exercise(db, body.exercise_id)
    before = await _current_records(db, user, body.exercise_id)
    row = SetLog(
        id=uuid7(),
        session_id=session.id,
        exercise_id=body.exercise_id,
        program_exercise_id=await _valid_program_exercise(db, user, body.program_exercise_id),
        set_index=body.set_index,
        weight_kg=_dec(body.weight_kg),
        reps=body.reps,
        rir=body.rir,
        duration_s=body.duration_s,
        is_warmup=body.is_warmup,
        completed_at=body.completed_at,
        client_uuid=body.client_uuid,
        client_updated_at=datetime.now(UTC),
    )
    db.add(row)
    await db.flush()
    after = await recompute_records(db, user, body.exercise_id)
    beaten = [
        kind
        for kind, rec in after.items()
        if _improved(before.get(kind), rec)
        and (rec.set_id == row.id or (kind == "volume" and rec.session_id == session.id))
    ]
    await db.commit()
    return set_dto(row, beaten)


def _improved(before: Decimal | None, after: PersonalRecord) -> bool:
    return before is None or after.value > before


async def _valid_program_exercise(
    db: AsyncSession, user: User, program_exercise_id: uuid.UUID | None
) -> uuid.UUID | None:
    if program_exercise_id is None:
        return None
    from app.models.program import ProgramBlock, ProgramExercise

    found = (
        await db.execute(
            select(ProgramExercise.id)
            .join(ProgramBlock, ProgramBlock.id == ProgramExercise.block_id)
            .join(ProgramDay, ProgramDay.id == ProgramBlock.day_id)
            .join(ProgramWeek, ProgramWeek.id == ProgramDay.week_id)
            .join(Program, Program.id == ProgramWeek.program_id)
            .where(ProgramExercise.id == program_exercise_id, Program.user_id == user.id)
        )
    ).scalar_one_or_none()
    return found


async def _owned_set(
    db: AsyncSession, user: User, session_id: uuid.UUID, set_id: uuid.UUID
) -> SetLog:
    await get_owned_session(db, user, session_id)
    row = await db.get(SetLog, set_id)
    if row is None or row.session_id != session_id or row.deleted_at is not None:
        raise not_found("La serie no existe.")
    return row


async def update_set(
    db: AsyncSession, user: User, session_id: uuid.UUID, set_id: uuid.UUID, body: api.SetLogUpdate
) -> api.SetLog:
    row = await _owned_set(db, user, session_id, set_id)
    fields = body.model_fields_set
    for name in ("weight_kg", "reps", "rir", "duration_s"):
        if name in fields:
            value = getattr(body, name)
            setattr(row, name, _dec(value) if name == "weight_kg" else value)
    if "is_warmup" in fields and body.is_warmup is not None:
        row.is_warmup = body.is_warmup
    row.client_updated_at = datetime.now(UTC)
    await db.flush()
    await recompute_records(db, user, row.exercise_id)
    await db.commit()
    return set_dto(row)


async def delete_set(
    db: AsyncSession, user: User, session_id: uuid.UUID, set_id: uuid.UUID
) -> None:
    row = await _owned_set(db, user, session_id, set_id)
    now = datetime.now(UTC)
    row.deleted_at = now
    row.client_updated_at = now
    await db.flush()
    await recompute_records(db, user, row.exercise_id)
    await db.commit()


# ---------------------------------------------------------------------- récords
def e1rm_of(weight: Decimal | None, reps: int | None, rir: int | None) -> float | None:
    if weight is None or reps is None or reps <= 0:
        return None
    return progression.estimate_1rm(float(weight), reps, rir or 0)


async def _current_records(db: AsyncSession, user: User, exercise_id: str) -> dict[str, Decimal]:
    rows = await db.execute(
        select(PersonalRecord.kind, PersonalRecord.value).where(
            PersonalRecord.user_id == user.id, PersonalRecord.exercise_id == exercise_id
        )
    )
    return {kind: value for kind, value in rows}


async def recompute_records(
    db: AsyncSession, user: User, exercise_id: str
) -> dict[str, PersonalRecord]:
    """Recalcula desde las series vigentes los tres récords del ejercicio (sin N+1)."""
    sets = (
        await db.execute(
            select(SetLog, WorkoutSession.started_at)
            .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
            .where(
                WorkoutSession.user_id == user.id,
                SetLog.exercise_id == exercise_id,
                SetLog.deleted_at.is_(None),
                SetLog.is_warmup.is_(False),
            )
        )
    ).all()
    best: dict[str, dict[str, Any]] = {}
    volumes: dict[uuid.UUID, tuple[float, SetLog]] = {}
    for row, _started in sets:
        if row.weight_kg is None or not row.reps:
            continue
        weight = float(row.weight_kg)
        estimate = e1rm_of(row.weight_kg, row.reps, row.rir)
        candidates: list[tuple[str, float]] = [("heaviest_set", weight)]
        if estimate is not None:
            candidates.append(("e1rm", round(estimate, 2)))
        for kind, value in candidates:
            current = best.get(kind)
            key = (value, row.reps)
            if current is None or key > (current["value"], current["row"].reps):
                best[kind] = {"value": value, "row": row}
        total, last = volumes.get(row.session_id, (0.0, row))
        volumes[row.session_id] = (
            total + weight * row.reps,
            row if row.completed_at >= last.completed_at else last,
        )
    if volumes:
        session_id, (total, row) = max(volumes.items(), key=lambda item: item[1][0])
        best["volume"] = {"value": round(total, 2), "row": row, "session": session_id}
    existing = {
        r.kind: r
        for r in (
            await db.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == user.id, PersonalRecord.exercise_id == exercise_id
                )
            )
        ).scalars()
    }
    result: dict[str, PersonalRecord] = {}
    for kind in RECORD_KINDS:
        entry = best.get(kind)
        stored = existing.get(kind)
        if entry is None:
            if stored is not None:
                await db.delete(stored)
            continue
        row = entry["row"]
        target = stored or PersonalRecord(
            id=uuid7(), user_id=user.id, exercise_id=exercise_id, kind=kind
        )
        target.value = Decimal(str(entry["value"]))
        target.weight_kg = row.weight_kg if kind != "volume" else None
        target.reps = row.reps if kind != "volume" else None
        target.achieved_at = row.completed_at
        target.session_id = entry.get("session", row.session_id)
        target.set_id = row.id if kind != "volume" else None
        if stored is None:
            db.add(target)
        result[kind] = target
    await db.flush()
    return result


async def _records_dto(db: AsyncSession, stmt: Any) -> list[api.PersonalRecord]:
    rows = (
        await db.execute(
            stmt.add_columns(Exercise.name_es)
            .join(Exercise, Exercise.id == PersonalRecord.exercise_id)
            .order_by(PersonalRecord.achieved_at.desc(), PersonalRecord.id)
        )
    ).all()
    return [record_dto(r, name) for r, name in rows]


def record_dto(r: PersonalRecord, name: str) -> api.PersonalRecord:
    return api.PersonalRecord(
        id=r.id,
        exercise_id=r.exercise_id,
        exercise_name_es=name,
        kind=cast("Any", r.kind),
        value=float(r.value),
        weight_kg=_f(r.weight_kg),
        reps=r.reps,
        achieved_at=r.achieved_at,
        session_id=r.session_id,
        set_id=r.set_id,
    )


async def list_records(
    db: AsyncSession,
    user: User,
    *,
    exercise_id: str | None,
    kind: str | None,
    cursor: dict[str, Any] | None,
    limit: int,
) -> api.PersonalRecordPage:
    stmt = select(PersonalRecord).where(PersonalRecord.user_id == user.id)
    if exercise_id:
        stmt = stmt.where(PersonalRecord.exercise_id == exercise_id)
    if kind:
        stmt = stmt.where(PersonalRecord.kind == kind)
    if cursor:
        at = datetime.fromisoformat(str(cursor["a"]))
        last = uuid.UUID(str(cursor["i"]))
        stmt = stmt.where(
            or_(
                PersonalRecord.achieved_at < at,
                and_(PersonalRecord.achieved_at == at, PersonalRecord.id > last),
            )
        )
    found = await _records_dto(db, stmt.limit(limit + 1))
    next_cursor = None
    if len(found) > limit:
        found = found[:limit]
        next_cursor = encode_cursor(
            {"a": found[-1].achieved_at.isoformat(), "i": str(found[-1].id)}
        )
    return api.PersonalRecordPage(items=found, next_cursor=next_cursor)


# -------------------------------------------------------------------------- sync
def _rejected(index: int, op: str, client_uuid: uuid.UUID, error: ProblemError) -> api.SyncResult:
    problem = api.Problem(
        type=f"/problems/{error.code.replace('_', '-')}",
        title=error.title,
        status=error.status,
        code=error.code,
        detail=error.detail,
    )
    return api.SyncResult(
        index=index,
        op=cast("Any", op),
        client_uuid=client_uuid,
        status="rejected",
        server_id=None,
        problem=problem,
    )


def _result(
    index: int, op: str, client_uuid: uuid.UUID, status: str, server_id: uuid.UUID | None
) -> api.SyncResult:
    return api.SyncResult(
        index=index,
        op=cast("Any", op),
        client_uuid=client_uuid,
        status=cast("Any", status),
        server_id=server_id,
        problem=None,
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def _sync_session(
    db: AsyncSession, user: User, index: int, op: api.SyncSessionUpsert
) -> api.SyncResult:
    row = (
        await db.execute(
            select(WorkoutSession).where(
                WorkoutSession.user_id == user.id, WorkoutSession.client_uuid == op.client_uuid
            )
        )
    ).scalar_one_or_none()
    if row is None:
        program_id: uuid.UUID | None = None
        default_name = "Sesión libre"
        if op.program_day_id is not None:
            program_id, default_name = await _day_context(db, user, op.program_day_id)
        row = WorkoutSession(
            id=uuid7(),
            user_id=user.id,
            client_uuid=op.client_uuid,
            program_id=program_id,
            program_day_id=op.program_day_id,
            name=op.name or default_name,
            started_at=op.started_at,
            finished_at=op.finished_at,
            status=op.status,
            perceived_effort=op.perceived_effort,
            notes=op.notes,
            client_updated_at=op.updated_at,
        )
        db.add(row)
        await db.flush()
        return _result(index, "session_upsert", op.client_uuid, "applied", row.id)
    known = _aware(row.client_updated_at)
    if op.updated_at == known:
        return _result(index, "session_upsert", op.client_uuid, "duplicate", row.id)
    if op.updated_at < known:
        return _result(index, "session_upsert", op.client_uuid, "superseded", row.id)
    if op.name:
        row.name = op.name
    row.started_at = op.started_at
    row.finished_at = op.finished_at
    row.status = op.status
    row.perceived_effort = op.perceived_effort
    row.notes = op.notes
    row.client_updated_at = op.updated_at
    await db.flush()
    return _result(index, "session_upsert", op.client_uuid, "applied", row.id)


async def _sync_set(
    db: AsyncSession, user: User, index: int, op: api.SyncSetUpsert, touched: set[str]
) -> api.SyncResult:
    session = (
        await db.execute(
            select(WorkoutSession).where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.client_uuid == op.session_client_uuid,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise not_found("La sesión de la serie no existe (envía antes su session_upsert).")
    data = op.set
    row = (
        await db.execute(select(SetLog).where(SetLog.client_uuid == data.client_uuid))
    ).scalar_one_or_none()
    if row is not None and row.session_id != session.id:
        raise conflict("conflict", "Ese client_uuid pertenece a otra sesión.")
    if row is None:
        await _check_exercise(db, data.exercise_id)
        row = SetLog(
            id=uuid7(),
            session_id=session.id,
            exercise_id=data.exercise_id,
            program_exercise_id=await _valid_program_exercise(db, user, data.program_exercise_id),
            set_index=data.set_index,
            weight_kg=_dec(data.weight_kg),
            reps=data.reps,
            rir=data.rir,
            duration_s=data.duration_s,
            is_warmup=data.is_warmup,
            completed_at=data.completed_at,
            client_uuid=data.client_uuid,
            client_updated_at=op.updated_at,
        )
        db.add(row)
        await db.flush()
        touched.add(data.exercise_id)
        return _result(index, "set_upsert", data.client_uuid, "applied", row.id)
    known = _aware(row.client_updated_at)
    if row.deleted_at is not None or op.updated_at < known:
        return _result(index, "set_upsert", data.client_uuid, "superseded", row.id)
    if op.updated_at == known:
        return _result(index, "set_upsert", data.client_uuid, "duplicate", row.id)
    row.set_index = data.set_index
    row.weight_kg = _dec(data.weight_kg)
    row.reps = data.reps
    row.rir = data.rir
    row.duration_s = data.duration_s
    row.is_warmup = data.is_warmup
    row.completed_at = data.completed_at
    row.client_updated_at = op.updated_at
    await db.flush()
    touched.add(row.exercise_id)
    return _result(index, "set_upsert", data.client_uuid, "applied", row.id)


async def _sync_delete(
    db: AsyncSession, user: User, index: int, op: api.SyncSetDelete, touched: set[str]
) -> api.SyncResult:
    row = (
        await db.execute(
            select(SetLog)
            .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
            .where(SetLog.client_uuid == op.client_uuid, WorkoutSession.user_id == user.id)
        )
    ).scalar_one_or_none()
    if row is None or row.deleted_at is not None:
        return _result(index, "set_delete", op.client_uuid, "duplicate", row.id if row else None)
    if op.deleted_at < _aware(row.client_updated_at):
        return _result(index, "set_delete", op.client_uuid, "superseded", row.id)
    row.deleted_at = op.deleted_at
    row.client_updated_at = op.deleted_at
    await db.flush()
    touched.add(row.exercise_id)
    return _result(index, "set_delete", op.client_uuid, "applied", row.id)


async def sync_batch(db: AsyncSession, user: User, body: api.SyncRequest) -> api.SyncResponse:
    """Aplica el lote en orden; cada operación va en un SAVEPOINT (un fallo no aborta el lote)."""
    results: list[api.SyncResult] = []
    touched: set[str] = set()
    for index, op in enumerate(body.operations):
        client_uuid = (
            op.client_uuid if not isinstance(op, api.SyncSetUpsert) else op.set.client_uuid
        )
        try:
            async with db.begin_nested():
                if isinstance(op, api.SyncSessionUpsert):
                    results.append(await _sync_session(db, user, index, op))
                elif isinstance(op, api.SyncSetUpsert):
                    results.append(await _sync_set(db, user, index, op, touched))
                else:
                    results.append(await _sync_delete(db, user, index, op, touched))
        except ProblemError as error:
            results.append(_rejected(index, op.op, client_uuid, error))
        except IntegrityError:
            results.append(
                _rejected(
                    index,
                    op.op,
                    client_uuid,
                    ProblemError(409, "conflict", "Conflicto de integridad."),
                )
            )
    for exercise_id in touched:
        await recompute_records(db, user, exercise_id)
    await db.commit()
    return api.SyncResponse(server_time=datetime.now(UTC), results=results)
