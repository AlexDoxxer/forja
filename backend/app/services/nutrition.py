"""Nutrición (opcional): ajustes, objetivo, planes semanales, intercambios y lista de la compra.

El backend calcula ``age_years`` con la fecha de la petición, usa la última ``body_metric``
como peso y emite ``missing_profile_data`` antes de llamar al motor (que no lee el reloj).
"""

import asyncio
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import forja_nutrition
from forja_nutrition import models as nm
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.common import encode_cursor
from app.core.config import Settings
from app.core.errors import ProblemError, forbidden, not_found, unprocessable
from app.models.nutrition import (
    Food,
    MealPlan,
    MealPlanItem,
    NutritionSettings,
    NutritionTarget,
)
from app.models.program import Program
from app.models.user import BodyMetric, Profile, User
from app.repositories.catalog import fold
from app.schemas import api
from app.services import settings as app_settings
from app.services.profile import load_profile

MISSING_DATA_MESSAGE = (
    "Para calcular tu objetivo necesitamos tu fecha de nacimiento, tu altura y tu peso. "
    "Complétalos en tu perfil."
)
DISCLAIMER = "Forja no sustituye el consejo de profesionales sanitarios ni de entrenamiento."

DEFAULT_SETTINGS = {
    "goal": "maintain",
    "pace": "gentle",
    "diet_type": "omnivore",
    "meals_per_day": 4,
    "allergens": [],
    "excluded_food_ids": [],
    "disliked_food_ids": [],
    "pregnant": False,
    "breastfeeding": False,
}


async def sync_foods(sessionmaker: async_sessionmaker[AsyncSession]) -> int:
    """Espeja ``foods.json`` en la tabla ``food`` (upsert idempotente al arrancar)."""
    foods = forja_nutrition.load_foods()
    rows = [
        {
            "id": f.id,
            "name_es": f.name_es,
            "category": f.category.value,
            "fdc_id": f.fdc_id,
            "per_100g": f.per_100g.model_dump(mode="json"),
            "diet_types": [d.value for d in f.diet_types],
            "allergens": [a.value for a in f.allergens],
            "macro_role": f.macro_role.value,
            "typical_portion_g": Decimal(str(f.typical_portion_g)),
            "unit_grams": Decimal(str(f.unit_grams)) if f.unit_grams is not None else None,
            "unit_name_es": f.unit_name_es,
        }
        for f in foods
    ]
    async with sessionmaker() as db:
        stmt = insert(Food).values(rows)
        columns = {c: stmt.excluded[c] for c in rows[0] if c != "id"}
        await db.execute(
            stmt.on_conflict_do_update(index_elements=[Food.id], set_={**columns, "updated_at": func.now()})
        )
        await db.commit()
    return len(rows)


# ---------------------------------------------------------------- disponibilidad
async def ensure_enabled(db: AsyncSession, settings: Settings, user: User) -> Profile:
    profile = await load_profile(db, user)
    if not await app_settings.diet_feature_enabled(db, settings) or not profile.diet_enabled:
        raise forbidden("diet_disabled", "El módulo de dieta no está activado.")
    return profile


# ------------------------------------------------------------------------ ajustes
async def _settings_row(db: AsyncSession, user: User) -> dict[str, Any]:
    row = await db.get(NutritionSettings, user.id)
    if row is None:
        return dict(DEFAULT_SETTINGS)
    return {k: getattr(row, k) for k in DEFAULT_SETTINGS}


def target_record_dto(row: NutritionTarget) -> api.NutritionTargetRecord:
    return api.NutritionTargetRecord(
        id=row.id,
        calculated_at=row.calculated_at,
        target=api.NutritionTarget.model_validate(row.result),
    )


async def get_settings(
    db: AsyncSession, settings: Settings, user: User
) -> api.NutritionSettings:
    profile = await load_profile(db, user)
    latest = (
        await db.execute(
            select(NutritionTarget)
            .where(NutritionTarget.user_id == user.id)
            .order_by(NutritionTarget.calculated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return api.NutritionSettings(
        diet_enabled=profile.diet_enabled,
        **await _settings_row(db, user),
        feature_available=await app_settings.diet_feature_enabled(db, settings),
        current_target=target_record_dto(latest) if latest else None,
    )


async def update_settings(
    db: AsyncSession, settings: Settings, user: User, body: api.NutritionSettingsUpdate
) -> api.NutritionSettings:
    profile = await load_profile(db, user)
    profile.diet_enabled = body.diet_enabled
    values = body.model_dump(mode="json", exclude={"diet_enabled"})
    row = await db.get(NutritionSettings, user.id)
    if row is None:
        db.add(NutritionSettings(user_id=user.id, **values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
    await db.commit()
    return await get_settings(db, settings, user)


# ------------------------------------------------------------------ entrada motor
def age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def missing_data_target(goal: str, pace: str) -> api.NutritionTarget:
    return api.NutritionTarget(
        method="mifflin_average",
        age_years=0,
        bmr_kcal=0,
        activity_factor=1.0,
        tdee_kcal=0,
        requested_goal=cast("Any", goal),
        effective_goal=cast("Any", goal),
        pace=cast("Any", pace),
        target_kcal=None,
        protein_g=None,
        fat_g=None,
        carbs_g=None,
        fiber_g=None,
        blocked=True,
        block=api.NutritionBlock(reason_code="missing_profile_data", message_es=MISSING_DATA_MESSAGE),
        notices=[api.NutritionNotice(code="health_disclaimer", message_es=DISCLAIMER)],
    )


async def build_input(
    db: AsyncSession,
    user: User,
    profile: Profile,
    *,
    weight_override: float | None = None,
    goal: str | None = None,
    pace: str | None = None,
    seed: int | None = None,
) -> tuple[nm.NutritionInput | None, dict[str, Any]]:
    """``NutritionInput`` del motor, o ``None`` si faltan datos (``missing_profile_data``)."""
    stored = await _settings_row(db, user)
    if goal:
        stored["goal"] = goal
    if pace:
        stored["pace"] = pace
    weight = weight_override
    if weight is None:
        latest = (
            await db.execute(
                select(BodyMetric.weight_kg)
                .where(BodyMetric.user_id == user.id)
                .order_by(BodyMetric.date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        weight = float(latest) if latest is not None else None
    if profile.birth_date is None or profile.height_cm is None or weight is None:
        return None, stored
    days = (
        await db.execute(
            select(Program.days_per_week).where(Program.user_id == user.id, Program.is_active.is_(True))
        )
    ).scalar_one_or_none()
    payload = {
        "sex": profile.sex,
        "age_years": age_on(profile.birth_date, datetime.now(UTC).date()),
        "height_cm": float(profile.height_cm),
        "weight_kg": weight,
        "activity_level": profile.activity_level,
        "training_days_per_week": int(days or 0),
        "goal": stored["goal"],
        "pace": stored["pace"],
        "diet_type": stored["diet_type"],
        "meals_per_day": stored["meals_per_day"],
        "allergens": stored["allergens"],
        "excluded_food_ids": stored["excluded_food_ids"],
        "disliked_food_ids": stored["disliked_food_ids"],
        "pregnant": stored["pregnant"],
        "breastfeeding": stored["breastfeeding"],
        "seed": seed,
    }
    return nm.NutritionInput.model_validate(payload), stored


# ----------------------------------------------------------------------- objetivo
async def calculate_target(
    db: AsyncSession,
    settings: Settings,
    user: User,
    body: api.NutritionTargetRequest | None,
) -> api.NutritionTargetRecord:
    profile = await ensure_enabled(db, settings, user)
    request = body or api.NutritionTargetRequest()
    engine_input, stored = await build_input(
        db, user, profile, weight_override=request.weight_kg, goal=request.goal, pace=request.pace
    )
    now = datetime.now(UTC)
    if engine_input is None:
        return api.NutritionTargetRecord(
            id=uuid.uuid4(), calculated_at=now, target=missing_data_target(stored["goal"], stored["pace"])
        )
    target = await asyncio.to_thread(forja_nutrition.calculate_target, engine_input)
    result = target.model_dump(mode="json")
    row = NutritionTarget(
        user_id=user.id,
        calculated_at=now,
        input=engine_input.model_dump(mode="json"),
        result=result,
        kcal=_dec(target.target_kcal),
        protein_g=_dec(target.protein_g),
        fat_g=_dec(target.fat_g),
        carbs_g=_dec(target.carbs_g),
        fiber_g=_dec(target.fiber_g),
        method=target.method.value,
    )
    db.add(row)
    await db.commit()
    return target_record_dto(row)


def _dec(value: float | None) -> Decimal | None:
    return Decimal(str(round(value, 1))) if value is not None else None


# ------------------------------------------------------------------------- planes
def plan_resource(row: MealPlan) -> api.MealPlanResource:
    return api.MealPlanResource(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        plan=api.MealPlan.model_validate(row.snapshot),
    )


async def _owned_plan(db: AsyncSession, user: User, plan_id: uuid.UUID) -> MealPlan:
    row = await db.get(MealPlan, plan_id)
    if row is None or row.user_id != user.id:
        raise not_found("El plan no existe.")
    return row


def _item_rows(plan_id: uuid.UUID, plan: nm.MealPlan) -> list[MealPlanItem]:
    return [
        MealPlanItem(
            plan_id=plan_id,
            day=day.day_index,
            meal=meal.slot.value,
            position=position,
            food_id=item.food_id,
            grams=Decimal(str(item.grams)),
            units=item.units,
        )
        for day in plan.days
        for meal in day.meals
        for position, item in enumerate(meal.items)
    ]


async def create_plan(
    db: AsyncSession, settings: Settings, user: User, body: api.MealPlanCreate
) -> api.MealPlanResource:
    profile = await ensure_enabled(db, settings, user)
    if body.week_start.weekday() != 0:
        raise unprocessable(
            "validation_error",
            "week_start debe ser un lunes.",
            errors=[{"loc": ["body", "week_start"], "msg": "Debe ser lunes", "type": "value_error"}],
        )
    engine_input, stored = await build_input(db, user, profile, seed=body.seed)
    if engine_input is None:
        raise ProblemError(
            422,
            "nutrition_blocked",
            MISSING_DATA_MESSAGE,
            extra={"block": {"reason_code": "missing_profile_data", "message_es": MISSING_DATA_MESSAGE}},
        )
    outcome = await asyncio.to_thread(forja_nutrition.plan_week, engine_input, body.week_start)
    if outcome.plan is None or outcome.block is not None:
        block = outcome.block
        assert block is not None  # noqa: S101 - invariante de MealPlanOutcome
        raise ProblemError(
            422, "nutrition_blocked", block.message_es, extra={"block": block.model_dump(mode="json")}
        )
    plan = outcome.plan
    row = MealPlan(
        id=uuid.uuid4(),
        user_id=user.id,
        week_start=plan.week_start,
        diet_type=plan.diet_type.value,
        meals_per_day=plan.meals_per_day,
        input=engine_input.model_dump(mode="json"),
        seed=plan.seed,
        nutrition_version=plan.nutrition_version,
        foods_hash=plan.foods_hash,
        target=plan.target.model_dump(mode="json"),
        notices=[n.model_dump(mode="json") for n in plan.notices],
        snapshot=plan.model_dump(mode="json"),
    )
    db.add(row)
    await db.flush()
    db.add_all(_item_rows(row.id, plan))
    await db.commit()
    return plan_resource(row)


async def get_plan(db: AsyncSession, settings: Settings, user: User, plan_id: uuid.UUID) -> api.MealPlanResource:
    await ensure_enabled(db, settings, user)
    return plan_resource(await _owned_plan(db, user, plan_id))


async def list_plans(
    db: AsyncSession, settings: Settings, user: User, *, cursor: dict[str, Any] | None, limit: int
) -> api.MealPlanPage:
    await ensure_enabled(db, settings, user)
    stmt = select(MealPlan).where(MealPlan.user_id == user.id)
    if cursor:
        week = date.fromisoformat(str(cursor["w"]))
        created = datetime.fromisoformat(str(cursor["c"]))
        stmt = stmt.where(
            or_(
                MealPlan.week_start < week,
                (MealPlan.week_start == week) & (MealPlan.created_at < created),
            )
        )
    rows = list(
        (
            await db.execute(
                stmt.order_by(MealPlan.week_start.desc(), MealPlan.created_at.desc()).limit(limit + 1)
            )
        ).scalars()
    )
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor(
            {"w": rows[-1].week_start.isoformat(), "c": rows[-1].created_at.isoformat()}
        )
    return api.MealPlanPage(
        items=[
            api.MealPlanSummary(
                id=r.id,
                week_start=r.week_start,
                diet_type=cast("Any", r.diet_type),
                meals_per_day=r.meals_per_day,
                target_kcal=float(r.target.get("target_kcal") or 0),
                created_at=r.created_at,
            )
            for r in rows
        ],
        next_cursor=next_cursor,
    )


async def swap_food(
    db: AsyncSession,
    settings: Settings,
    user: User,
    plan_id: uuid.UUID,
    body: api.MealSwapRequest,
) -> api.MealPlanResource:
    await ensure_enabled(db, settings, user)
    row = await _owned_plan(db, user, plan_id)
    plan = nm.MealPlan.model_validate(row.snapshot)
    engine_input = nm.NutritionInput.model_validate(row.input)
    try:
        updated = await asyncio.to_thread(
            forja_nutrition.swap_food,
            plan,
            engine_input,
            body.day_index,
            nm.MealSlot(body.meal),
            body.food_id,
            body.replacement_food_id.root if body.replacement_food_id else None,
        )
    except ValueError as exc:
        raise unprocessable("validation_error", str(exc)) from exc
    row.snapshot = updated.model_dump(mode="json")
    row.notices = [n.model_dump(mode="json") for n in updated.notices]
    row.updated_at = datetime.now(UTC)
    await db.execute(delete(MealPlanItem).where(MealPlanItem.plan_id == row.id))
    db.add_all(_item_rows(row.id, updated))
    await db.commit()
    return plan_resource(row)


async def shopping_list(
    db: AsyncSession, settings: Settings, user: User, plan_id: uuid.UUID
) -> api.ShoppingList:
    await ensure_enabled(db, settings, user)
    row = await _owned_plan(db, user, plan_id)
    plan = nm.MealPlan.model_validate(row.snapshot)
    result = forja_nutrition.shopping_list(plan)
    return api.ShoppingList(plan_id=row.id, **result.model_dump(mode="json"))


# ---------------------------------------------------------------------- alimentos
async def list_foods(
    db: AsyncSession,
    settings: Settings,
    user: User,
    *,
    q: str | None,
    category: str | None,
    diet_type: str | None,
    cursor: dict[str, Any] | None,
    limit: int,
) -> api.FoodPage:
    await ensure_enabled(db, settings, user)
    stmt = select(Food)
    if q:
        stmt = stmt.where(func.unaccent(Food.name_es).ilike(f"%{fold(q)}%"))
    if category:
        stmt = stmt.where(Food.category == category)
    if diet_type:
        stmt = stmt.where(Food.diet_types.contains([diet_type]))
    if cursor:
        name, last = str(cursor["n"]), str(cursor["i"])
        stmt = stmt.where(or_(Food.name_es > name, (Food.name_es == name) & (Food.id > last)))
    rows = list((await db.execute(stmt.order_by(Food.name_es, Food.id).limit(limit + 1))).scalars())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor({"n": rows[-1].name_es, "i": rows[-1].id})
    catalog = {f.id: f for f in forja_nutrition.load_foods()}
    return api.FoodPage(
        items=[api.Food.model_validate(catalog[r.id].model_dump(mode="json")) for r in rows],
        next_cursor=next_cursor,
    )

