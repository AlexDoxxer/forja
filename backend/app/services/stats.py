"""Estadísticas de progreso y próxima sesión con cargas sugeridas por progresión."""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, cast

from forja_engine import Tables, progression
from forja_engine import models as em
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.models.catalog import Exercise, Muscle
from app.models.program import (
    PersonalRecord,
    Program,
    SetLog,
    WorkoutSession,
)
from app.models.user import BodyMetric, User
from app.schemas import api
from app.services import catalog as catalog_service
from app.services import programs as programs_service
from app.services import training

VOLUME_GROUPS = (
    "chest",
    "back",
    "shoulders",
    "arms",
    "quads",
    "hamstrings",
    "glutes",
    "calves",
    "core",
)
EFFECTIVE_RIR = 4
SECONDARY_CREDIT = 0.5
HISTORY_SESSIONS = 3
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _start(day: date) -> datetime:
    return datetime.combine(day, time.min, UTC)


# --------------------------------------------------------------------- resumen
async def overview(db: AsyncSession, user: User) -> api.StatsOverview:
    today = datetime.now(UTC).date()
    week = monday_of(today)
    week_sessions = (
        await db.execute(
            select(func.count()).where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.status == "completed",
                WorkoutSession.started_at >= _start(week),
            )
        )
    ).scalar_one()
    sets_row = (
        await db.execute(
            select(
                func.count(),
                func.coalesce(
                    func.sum(func.coalesce(SetLog.weight_kg, 0) * func.coalesce(SetLog.reps, 0)), 0
                ),
            )
            .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
            .where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.started_at >= _start(week),
                SetLog.deleted_at.is_(None),
                SetLog.is_warmup.is_(False),
            )
        )
    ).one()
    active = (
        await db.execute(
            select(Program.days_per_week).where(
                Program.user_id == user.id, Program.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    planned = int(active or 0)
    week_col = func.date_trunc("week", WorkoutSession.started_at)
    per_week = {
        d: c
        for d, c in (
            await db.execute(
                select(week_col, func.count())
                .where(
                    WorkoutSession.user_id == user.id,
                    WorkoutSession.status == "completed",
                    WorkoutSession.started_at >= _start(week - timedelta(weeks=60)),
                )
                .group_by(week_col)
            )
        )
    }
    counts = {d.date(): c for d, c in per_week.items()}
    needed = max(planned, 1)
    cursor = week if counts.get(week, 0) >= needed else week - timedelta(weeks=1)
    streak = 0
    while counts.get(cursor, 0) >= needed:
        streak += 1
        cursor -= timedelta(weeks=1)
    last = (
        await db.execute(
            select(PersonalRecord, Exercise.name_es)
            .join(Exercise, Exercise.id == PersonalRecord.exercise_id)
            .where(PersonalRecord.user_id == user.id)
            .order_by(PersonalRecord.achieved_at.desc())
            .limit(1)
        )
    ).first()
    latest = (
        await db.execute(
            select(BodyMetric)
            .where(BodyMetric.user_id == user.id)
            .order_by(BodyMetric.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    average = None
    if latest is not None:
        average = (
            await db.execute(
                select(func.avg(BodyMetric.weight_kg)).where(
                    BodyMetric.user_id == user.id,
                    BodyMetric.date > latest.date - timedelta(days=7),
                    BodyMetric.date <= latest.date,
                )
            )
        ).scalar_one()
    day_col = func.date(WorkoutSession.started_at)
    activity_rows = await db.execute(
        select(
            day_col,
            func.count(func.distinct(WorkoutSession.id)),
            func.coalesce(
                func.sum(func.coalesce(SetLog.weight_kg, 0) * func.coalesce(SetLog.reps, 0)), 0
            ),
        )
        .join(SetLog, SetLog.session_id == WorkoutSession.id, isouter=True)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.status == "completed",
            WorkoutSession.started_at >= _start(today - timedelta(days=365)),
        )
        .group_by(day_col)
        .order_by(day_col)
    )
    return api.StatsOverview(
        week_start=week,
        sessions_completed=week_sessions,
        sessions_planned=planned,
        sets_completed=sets_row[0],
        volume_kg=float(sets_row[1]),
        streak_weeks=streak,
        last_record=training.record_dto(last[0], last[1]) if last else None,
        body_weight=api.BodyWeight(
            latest=None if latest is None else _metric(latest),
            moving_average_7d_kg=round(float(average), 2) if average is not None else None,
        ),
        activity=[
            api.ActivityDay(date=d, session_count=c, volume_kg=float(v))
            for d, c, v in activity_rows
        ],
    )


def _metric(row: BodyMetric) -> api.BodyMetric:
    from app.services.profile import metric_dto  # noqa: PLC0415

    return metric_dto(row)


# ------------------------------------------------------------------------ volumen
async def volume(
    db: AsyncSession, user: User, cards: dict[str, em.ExerciseCard], weeks: int
) -> api.VolumeStats:
    this_week = monday_of(datetime.now(UTC).date())
    first = this_week - timedelta(weeks=weeks - 1)
    groups = {
        code: group for code, group in await db.execute(select(Muscle.code, Muscle.volume_group))
    }
    rows = await db.execute(
        select(
            SetLog.exercise_id, SetLog.rir, SetLog.weight_kg, SetLog.reps, WorkoutSession.started_at
        )
        .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.started_at >= _start(first),
            SetLog.deleted_at.is_(None),
            SetLog.is_warmup.is_(False),
        )
    )
    sets: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    kilos: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for exercise_id, rir, weight, reps, started in rows:
        card = cards.get(exercise_id)
        if card is None:
            continue
        week = monday_of(started.date())
        effective = rir is None or rir <= EFFECTIVE_RIR
        primary = groups.get(card.primary_group_muscle.value)
        tonnage = float(weight or 0) * (reps or 0)
        if primary in VOLUME_GROUPS:
            if effective:
                sets[week][primary] += 1.0
            kilos[week][primary] += tonnage
        for muscle in card.secondary_muscles:
            group = groups.get(muscle.value)
            if group in VOLUME_GROUPS and group != primary and effective:
                sets[week][group] += SECONDARY_CREDIT
    result: list[api.VolumeWeek] = []
    for offset in range(weeks):
        week = first + timedelta(weeks=offset)
        result.append(
            api.VolumeWeek(
                week_start=week,
                groups=[
                    api.GroupWeekVolume(
                        group=cast("Any", g),
                        effective_sets=sets[week][g],
                        volume_kg=kilos[week][g],
                    )
                    for g in VOLUME_GROUPS
                ],
            )
        )
    return api.VolumeStats(weeks=result)


# ---------------------------------------------------------------- por ejercicio
async def exercise_stats(
    db: AsyncSession, user: User, exercise_id: str, from_date: date | None, to_date: date | None
) -> api.ExerciseStats:
    if await db.get(Exercise, exercise_id) is None:
        raise not_found("El ejercicio no existe.")
    stmt = (
        select(SetLog, WorkoutSession.started_at)
        .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
        .where(
            WorkoutSession.user_id == user.id,
            SetLog.exercise_id == exercise_id,
            SetLog.deleted_at.is_(None),
            SetLog.is_warmup.is_(False),
        )
        .order_by(WorkoutSession.started_at, SetLog.set_index)
    )
    if from_date:
        stmt = stmt.where(WorkoutSession.started_at >= _start(from_date))
    if to_date:
        stmt = stmt.where(WorkoutSession.started_at < _start(to_date + timedelta(days=1)))
    per_session: dict[uuid.UUID, dict[str, Any]] = {}
    best_set: api.BestSet | None = None
    best_key: tuple[float, int] = (-1.0, -1)
    for row, started in (await db.execute(stmt)).all():
        point = per_session.setdefault(
            row.session_id,
            {"date": started.date(), "e1rm": None, "weight": None, "reps": None, "volume": 0.0},
        )
        weight = float(row.weight_kg) if row.weight_kg is not None else None
        if weight is not None and row.reps:
            point["volume"] += weight * row.reps
            estimate = training.e1rm_of(row.weight_kg, row.reps, row.rir)
            if estimate is not None and (point["e1rm"] is None or estimate > point["e1rm"]):
                point["e1rm"] = estimate
            if point["weight"] is None or (weight, row.reps) > (point["weight"], point["reps"]):
                point["weight"], point["reps"] = weight, row.reps
            if (weight, row.reps) > best_key:
                best_key = (weight, row.reps)
                best_set = api.BestSet(
                    weight_kg=weight, reps=row.reps, rir=row.rir, date=started.date()
                )
    points = [
        api.ExerciseStatPoint(
            date=p["date"],
            session_id=sid,
            e1rm_kg=round(p["e1rm"], 2) if p["e1rm"] is not None else None,
            best_weight_kg=p["weight"],
            best_reps=p["reps"],
            volume_kg=p["volume"],
        )
        for sid, p in per_session.items()
    ]
    estimates = [p.e1rm_kg for p in points if p.e1rm_kg is not None]
    return api.ExerciseStats(
        exercise_id=exercise_id,
        best_e1rm_kg=max(estimates) if estimates else None,
        best_set=best_set,
        points=points,
    )


# ----------------------------------------------------------------- próxima sesión
def _weekday_offset(weekday: str | None, position: int, count: int) -> int:
    if weekday:
        return WEEKDAYS.index(weekday)
    return round(position * 7 / max(count, 1))


def _bare(status: str, program: Program | None) -> api.NextSession:
    return api.NextSession(
        status=cast("Any", status),
        program_id=program.id if program else None,
        program_name=program.name if program else None,
        week_index=None,
        day=None,
        scheduled_date=None,
        suggestions=[],
        exercises=[],
    )


async def next_session(
    db: AsyncSession,
    user: User,
    cards: dict[str, em.ExerciseCard],
    all_cards: Sequence[em.ExerciseCard],
    tables: Tables,
) -> api.NextSession:
    program = (
        await db.execute(
            select(Program).where(Program.user_id == user.id, Program.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if program is None:
        return _bare("no_active_program", None)
    tree = await programs_service.load_tree(db, program)
    done = {
        d
        for (d,) in await db.execute(
            select(WorkoutSession.program_day_id).where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.program_id == program.id,
                WorkoutSession.status == "completed",
                WorkoutSession.program_day_id.is_not(None),
            )
        )
    }
    ordered = [(w, d) for w in tree.weeks for d in tree.days.get(w.id, [])]
    nxt = next(((w, d) for w, d in ordered if d.id not in done), None)
    if nxt is None:
        return _bare("program_completed", program)
    week, day = nxt
    today = datetime.now(UTC).date()
    trained_today = (
        await db.execute(
            select(func.count()).where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.status == "completed",
                WorkoutSession.started_at >= _start(today),
            )
        )
    ).scalar_one() > 0
    count = len(tree.days.get(week.id, []))
    position = next(i for i, d in enumerate(tree.days.get(week.id, [])) if d.id == day.id)
    target = _weekday_offset(day.weekday, position, count)
    delta = (target - today.weekday()) % 7
    if trained_today and delta == 0:
        delta = 7
    scheduled = (
        today + timedelta(days=delta)
        if day.weekday
        else today + timedelta(days=1 if trained_today else 0)
    )
    day_dto = programs_service.day_dto(tree, day)
    exercise_rows = [
        (b, ex) for b in tree.blocks.get(day.id, []) for ex in tree.exercises.get(b.id, [])
    ]
    history = await _history(db, user, {ex.exercise_id for _, ex in exercise_rows})
    suggestions: list[api.LoadSuggestion] = []
    extra: list[str] = []
    for block, ex in exercise_rows:
        if block.kind in {"warmup", "cooldown"}:
            continue
        card = cards.get(ex.exercise_id)
        if card is None:
            continue
        prescription = em.ExercisePrescription.model_validate(
            programs_service._exercise_dto(ex).model_dump(mode="json", exclude={"id", "order"})
        )
        entries = history.get(ex.exercise_id, [])
        suggestion = progression.suggest(
            prescription, card, [e for e, _ in entries], all_cards, tables
        )
        last = entries[-1] if entries else None
        suggestions.append(
            api.LoadSuggestion(
                program_exercise_id=ex.id,
                exercise_id=ex.exercise_id,
                **{k: v for k, v in suggestion.model_dump(mode="json").items()},
                last_performance=None
                if last is None
                else api.LastPerformance(
                    session_id=last[1],
                    date=last[0].session_date,
                    sets=[
                        api.SetPerformance(
                            weight_kg=s.weight_kg, reps=s.reps, rir=s.rir, duration_s=s.duration_s
                        )
                        for s in last[0].sets
                    ],
                ),
            )
        )
        if suggestion.suggested_exercise_id:
            extra.append(suggestion.suggested_exercise_id)
    ids = (
        [ex.exercise_id for _, ex in exercise_rows]
        + [a for _, ex in exercise_rows for a in ex.alternatives]
        + extra
    )
    return api.NextSession(
        status="rest_day" if trained_today else "scheduled",
        program_id=program.id,
        program_name=program.name,
        week_index=week.index,
        day=day_dto,
        scheduled_date=scheduled,
        suggestions=suggestions,
        exercises=await catalog_service.summaries_for(db, ids, user.id),
    )


async def _history(
    db: AsyncSession, user: User, exercise_ids: set[str]
) -> dict[str, list[tuple[em.ExerciseHistoryEntry, uuid.UUID]]]:
    """Últimas ``HISTORY_SESSIONS`` sesiones con series de trabajo por ejercicio (1 consulta)."""
    if not exercise_ids:
        return {}
    rows = await db.execute(
        select(SetLog, WorkoutSession.started_at)
        .join(WorkoutSession, WorkoutSession.id == SetLog.session_id)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.status == "completed",
            SetLog.exercise_id.in_(exercise_ids),
            SetLog.deleted_at.is_(None),
            SetLog.is_warmup.is_(False),
        )
        .order_by(WorkoutSession.started_at.desc(), SetLog.set_index)
        .limit(5000)
    )
    grouped: dict[str, dict[uuid.UUID, tuple[date, list[em.PerformedSet]]]] = defaultdict(dict)
    for row, started in rows:
        entry = grouped[row.exercise_id].setdefault(row.session_id, (started.date(), []))
        entry[1].append(
            em.PerformedSet(
                weight_kg=float(row.weight_kg) if row.weight_kg is not None else None,
                reps=row.reps,
                rir=row.rir,
                duration_s=row.duration_s,
                is_warmup=False,
            )
        )
    result: dict[str, list[tuple[em.ExerciseHistoryEntry, uuid.UUID]]] = {}
    for exercise_id, sessions in grouped.items():
        recent = list(sessions.items())[:HISTORY_SESSIONS]
        result[exercise_id] = [
            (em.ExerciseHistoryEntry(session_date=d, sets=tuple(sets)), sid)
            for sid, (d, sets) in reversed(recent)
        ]
    return result
