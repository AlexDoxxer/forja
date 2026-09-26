"""Exportar, importar y borrar la cuenta (``/me/export``, ``/me/import``, ``DELETE /me``)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict, forbidden
from app.core.ids import uuid7
from app.models.catalog import Exercise
from app.models.nutrition import MealPlan, NutritionSettings, NutritionTarget
from app.models.program import (
    PersonalRecord,
    Program,
    ProgramBlock,
    ProgramDay,
    ProgramExercise,
    ProgramWeek,
    SetLog,
    WorkoutSession,
)
from app.models.user import BodyMetric, FavoriteExercise, User
from app.schemas import api
from app.security import passwords
from app.services import admin as admin_service
from app.services import nutrition as nutrition_service
from app.services import profile as profile_service
from app.services import programs as programs_service
from app.services import training
from app.services.audit import audit

APP_VERSION_FALLBACK = "0.0.0"
IMPORT_NAMESPACE = uuid.UUID("6f0f7a3e-3c1c-5d0e-9a53-5b1a0b6f0c11")


# ------------------------------------------------------------------------ export
async def export_account(db: AsyncSession, user: User) -> api.UserExport:
    from app.api.routers.system import _app_version  # noqa: PLC0415

    profile = await profile_service.load_profile(db, user)
    metrics = (
        await db.execute(
            select(BodyMetric).where(BodyMetric.user_id == user.id).order_by(BodyMetric.date)
        )
    ).scalars()
    favorites = (
        await db.execute(
            select(FavoriteExercise.exercise_id)
            .where(FavoriteExercise.user_id == user.id)
            .order_by(FavoriteExercise.exercise_id)
        )
    ).scalars()
    programs = (
        await db.execute(
            select(Program).where(Program.user_id == user.id).order_by(Program.created_at)
        )
    ).scalars()
    program_dtos = [
        await programs_service.detail_dto(db, user, await programs_service.load_tree(db, p))
        for p in programs
    ]
    sessions = list(
        (
            await db.execute(
                select(WorkoutSession)
                .where(WorkoutSession.user_id == user.id)
                .order_by(WorkoutSession.started_at)
            )
        ).scalars()
    )
    sets: dict[uuid.UUID, list[SetLog]] = {}
    if sessions:
        rows = await db.execute(
            select(SetLog)
            .where(SetLog.session_id.in_([s.id for s in sessions]), SetLog.deleted_at.is_(None))
            .order_by(SetLog.completed_at, SetLog.set_index)
        )
        for row in rows.scalars():
            sets.setdefault(row.session_id, []).append(row)
    totals = await training._totals(db, [s.id for s in sessions])
    session_dtos = [
        api.WorkoutSession(
            **training._summary(s, totals).model_dump(),
            sets=[training.set_dto(x) for x in sets.get(s.id, [])],
        )
        for s in sessions
    ]
    records = await training._records_dto(
        db, select(PersonalRecord).where(PersonalRecord.user_id == user.id)
    )
    nutrition_settings = await db.get(NutritionSettings, user.id)
    targets = (
        await db.execute(
            select(NutritionTarget)
            .where(NutritionTarget.user_id == user.id)
            .order_by(NutritionTarget.calculated_at)
        )
    ).scalars()
    plans = (
        await db.execute(
            select(MealPlan).where(MealPlan.user_id == user.id).order_by(MealPlan.week_start)
        )
    ).scalars()
    stored = await nutrition_service._settings_row(db, user)
    profile_dto = profile_service.profile_dto(user, profile)
    return api.UserExport(
        format="forja-export",
        schema_version=1,
        exported_at=datetime.now(UTC),
        app_version=_app_version(),
        user=api.User(
            email=user.email,
            display_name=user.display_name,
            locale=cast("Any", user.locale),
            units=cast("Any", user.units),
            created_at=user.created_at,
        ),
        profile=profile_dto,
        parq_answers=api.ParqAnswers.model_validate(profile.parq_answers)
        if profile.parq_answers
        else None,
        body_metrics=[profile_service.metric_dto(m) for m in metrics],
        favorites=cast("Any", list(favorites)),
        programs=program_dtos,
        sessions=session_dtos,
        personal_records=records,
        nutrition=api.Nutrition(
            settings=api.NutritionSettingsUpdate(diet_enabled=profile.diet_enabled, **stored)
            if nutrition_settings
            else None,
            targets=[nutrition_service.target_record_dto(t) for t in targets],
            plans=[nutrition_service.plan_resource(p) for p in plans],
        ),
    )


# ------------------------------------------------------------------------ import
def _zero() -> dict[str, int]:
    return {
        "programs": 0,
        "sessions": 0,
        "sets": 0,
        "body_metrics": 0,
        "favorites": 0,
        "meal_plans": 0,
    }


def _derived(user: User, original: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(IMPORT_NAMESPACE, f"{user.id}:{original}")


async def import_account(
    db: AsyncSession, user: User, body: api.UserExport, known_exercises: set[str]
) -> api.ImportResult:
    """Importación idempotente: repetirla no duplica nada (ids derivados y ``client_uuid``)."""
    created, skipped = _zero(), _zero()
    warnings: list[str] = []
    profile = await profile_service.load_profile(db, user)
    fields = body.profile
    user.display_name = fields.display_name
    user.locale = fields.locale
    user.units = fields.units
    profile.sex = fields.sex
    profile.birth_date = fields.birth_date
    profile.height_cm = Decimal(str(fields.height_cm)) if fields.height_cm is not None else None
    profile.experience = fields.experience
    profile.activity_level = fields.activity_level
    profile.equipment_profile = fields.equipment.model_dump(mode="json")
    profile.limitations = fields.limitations.model_dump(mode="json")
    profile.diet_enabled = fields.diet_enabled
    profile.preferences = fields.preferences.model_dump(mode="json")
    if body.parq_answers is not None:
        profile.parq_answers = body.parq_answers.model_dump(mode="json")
        profile.parq_flagged = fields.parq_flagged
        profile.parq_completed_at = fields.parq_completed_at

    for metric in body.body_metrics:
        existing = (
            await db.execute(
                select(BodyMetric.id).where(
                    BodyMetric.user_id == user.id, BodyMetric.date == metric.date
                )
            )
        ).first()
        if existing:
            skipped["body_metrics"] += 1
            continue
        db.add(
            BodyMetric(
                user_id=user.id,
                date=metric.date,
                weight_kg=Decimal(str(metric.weight_kg)),
                body_fat_pct=Decimal(str(metric.body_fat_pct))
                if metric.body_fat_pct is not None
                else None,
                waist_cm=Decimal(str(metric.waist_cm)) if metric.waist_cm is not None else None,
            )
        )
        created["body_metrics"] += 1

    current = set(
        (
            await db.execute(
                select(FavoriteExercise.exercise_id).where(FavoriteExercise.user_id == user.id)
            )
        ).scalars()
    )
    for value in body.favorites:
        exercise_id = value.root
        if exercise_id in current:
            skipped["favorites"] += 1
        elif exercise_id not in known_exercises:
            warnings.append(f"Favorito ignorado: el ejercicio {exercise_id} no existe.")
            skipped["favorites"] += 1
        else:
            db.add(FavoriteExercise(user_id=user.id, exercise_id=exercise_id))
            current.add(exercise_id)
            created["favorites"] += 1
    await db.flush()

    day_map: dict[uuid.UUID, uuid.UUID] = {}
    program_map: dict[uuid.UUID, uuid.UUID] = {}
    for program in body.programs:
        await _import_program(
            db, user, program, known_exercises, day_map, program_map, created, skipped, warnings
        )
    await db.flush()

    touched: set[str] = set()
    for session in body.sessions:
        known_session = (
            await db.execute(
                select(WorkoutSession.id).where(
                    WorkoutSession.user_id == user.id,
                    WorkoutSession.client_uuid == session.client_uuid,
                )
            )
        ).scalar_one_or_none()
        session_id: uuid.UUID
        if known_session is not None:
            skipped["sessions"] += 1
            session_id = known_session
        else:
            session_id = uuid7()
            db.add(
                WorkoutSession(
                    id=session_id,
                    user_id=user.id,
                    client_uuid=session.client_uuid,
                    program_id=program_map.get(session.program_id) if session.program_id else None,
                    program_day_id=day_map.get(session.program_day_id)
                    if session.program_day_id
                    else None,
                    name=session.name,
                    started_at=session.started_at,
                    finished_at=session.finished_at,
                    status=session.status,
                    perceived_effort=session.perceived_effort,
                    notes=session.notes,
                    client_updated_at=session.updated_at,
                )
            )
            await db.flush()
            created["sessions"] += 1
        for item in session.sets:
            set_uuid = item.client_uuid
            owner = (
                await db.execute(
                    select(WorkoutSession.user_id)
                    .join(SetLog, SetLog.session_id == WorkoutSession.id)
                    .where(SetLog.client_uuid == set_uuid)
                )
            ).scalar_one_or_none()
            if owner is not None and owner != user.id:
                # ``set_log.client_uuid`` es único global: en otra cuenta se deriva uno estable.
                set_uuid = _derived(user, set_uuid)
                owner = (
                    await db.execute(select(SetLog.id).where(SetLog.client_uuid == set_uuid))
                ).scalar_one_or_none()
            if owner is not None:
                skipped["sets"] += 1
                continue
            if item.exercise_id not in known_exercises:
                warnings.append(f"Serie ignorada: el ejercicio {item.exercise_id} no existe.")
                skipped["sets"] += 1
                continue
            db.add(
                SetLog(
                    id=uuid7(),
                    session_id=session_id,
                    exercise_id=item.exercise_id,
                    program_exercise_id=None,
                    set_index=item.set_index,
                    weight_kg=Decimal(str(item.weight_kg)) if item.weight_kg is not None else None,
                    reps=item.reps,
                    rir=item.rir,
                    duration_s=item.duration_s,
                    is_warmup=item.is_warmup,
                    completed_at=item.completed_at,
                    client_uuid=set_uuid,
                    client_updated_at=item.updated_at,
                )
            )
            touched.add(item.exercise_id)
            created["sets"] += 1
    await db.flush()
    for exercise_id in touched:
        await training.recompute_records(db, user, exercise_id)

    await _import_nutrition(db, user, body, created, skipped)
    await audit(db, "user.import", actor=user.id, details={"created": created})
    await db.commit()
    return api.ImportResult(
        created=api.ImportCounts(**created), skipped=api.ImportCounts(**skipped), warnings=warnings
    )


async def _import_program(
    db: AsyncSession,
    user: User,
    program: api.ProgramDetail,
    known: set[str],
    day_map: dict[uuid.UUID, uuid.UUID],
    program_map: dict[uuid.UUID, uuid.UUID],
    created: dict[str, int],
    skipped: dict[str, int],
    warnings: list[str],
) -> None:
    own = await db.get(Program, program.id)
    if own is not None and own.user_id == user.id:
        skipped["programs"] += 1
        program_map[program.id] = own.id
        await _map_days(db, own, program, day_map)
        return
    new_id = _derived(user, program.id)
    if await db.get(Program, new_id) is not None:
        skipped["programs"] += 1
        program_map[program.id] = new_id
        existing = await db.get(Program, new_id)
        if existing:
            await _map_days(db, existing, program, day_map)
        return
    used = {
        ex.exercise_id
        for week in program.weeks
        for day in week.days
        for block in day.blocks
        for ex in block.exercises
    }
    if not used <= known:
        warnings.append(f"Programa «{program.name}» ignorado: usa ejercicios inexistentes.")
        skipped["programs"] += 1
        return
    row = Program(
        id=new_id,
        user_id=user.id,
        name=program.name,
        source="imported",
        generator_input=program.generator_input.model_dump(mode="json")
        if program.generator_input
        else None,
        generator_version=program.generator_version,
        tables_hash=program.tables_hash,
        seed=program.seed,
        goal=program.goal,
        days_per_week=program.days_per_week,
        weeks=program.weeks_count,
        is_active=False,
        archived_at=program.archived_at,
        weekly_volume=[v.model_dump(mode="json") for v in program.weekly_volume],
        warnings=[w.model_dump(mode="json") for w in program.warnings],
        rationale_es=list(program.rationale_es),
    )
    db.add(row)
    await db.flush()
    batch = programs_service.RowBatch()
    for week in program.weeks:
        week_row = ProgramWeek(
            id=uuid7(),
            program_id=row.id,
            index=week.index,
            phase=week.phase,
            target_rir=2,
            volume_ratio=Decimal("1.00"),
        )
        batch.weeks.append(week_row)
        for day in week.days:
            day_row = ProgramDay(
                id=uuid7(),
                week_id=week_row.id,
                index=day.index,
                template=None,
                name=day.name,
                focus=day.focus,
                weekday=day.weekday,
                is_recovery=day.is_recovery,
                estimated_minutes=day.estimated_minutes,
            )
            batch.days.append(day_row)
            day_map[day.id] = day_row.id
            for block in day.blocks:
                block_row = ProgramBlock(
                    id=uuid7(),
                    day_id=day_row.id,
                    order=block.order,
                    kind=block.kind,
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
                            slot=None,
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
                            alternatives=[a.root for a in ex.alternatives],
                        )
                    )
    await batch.flush(db)
    program_map[program.id] = row.id
    created["programs"] += 1


async def _map_days(
    db: AsyncSession, row: Program, program: api.ProgramDetail, day_map: dict[uuid.UUID, uuid.UUID]
) -> None:
    tree = await programs_service.load_tree(db, row)
    stored = {(w.index, d.index): d.id for w in tree.weeks for d in tree.days.get(w.id, [])}
    for week in program.weeks:
        for day in week.days:
            if (week.index, day.index) in stored:
                day_map[day.id] = stored[(week.index, day.index)]


async def _import_nutrition(
    db: AsyncSession,
    user: User,
    body: api.UserExport,
    created: dict[str, int],
    skipped: dict[str, int],
) -> None:
    if body.nutrition.settings is not None and await db.get(NutritionSettings, user.id) is None:
        values = body.nutrition.settings.model_dump(mode="json", exclude={"diet_enabled"})
        db.add(NutritionSettings(user_id=user.id, **values))
    for resource in body.nutrition.plans:
        plan_id = _derived(user, resource.id)
        own = await db.get(MealPlan, resource.id)
        derived = await db.get(MealPlan, plan_id)
        if (own is not None and own.user_id == user.id) or derived is not None:
            skipped["meal_plans"] += 1
            continue
        plan = resource.plan
        db.add(
            MealPlan(
                id=plan_id,
                user_id=user.id,
                week_start=plan.week_start,
                diet_type=plan.diet_type,
                meals_per_day=plan.meals_per_day,
                input={},
                seed=plan.seed,
                nutrition_version=plan.nutrition_version,
                foods_hash=plan.foods_hash,
                target=plan.target.model_dump(mode="json"),
                notices=[n.model_dump(mode="json") for n in plan.notices],
                snapshot=plan.model_dump(mode="json"),
            )
        )
        created["meal_plans"] += 1
    await db.flush()


async def known_exercise_ids(db: AsyncSession) -> set[str]:
    return set((await db.execute(select(Exercise.id))).scalars())


# ------------------------------------------------------------------------ borrado
async def delete_account(db: AsyncSession, user: User, body: api.AccountDeleteRequest) -> None:
    if not await passwords.verify_password_async(user.password_hash, body.password):
        raise forbidden("forbidden", "La contraseña no es correcta.")
    if user.role == "admin" and await admin_service.other_active_admins(db, user.id) == 0:
        raise conflict("last_admin", "No puedes borrar al último administrador.")
    user_id = user.id
    await db.delete(user)
    await audit(db, "user.delete", actor=None, target=str(user_id))
    await db.commit()
