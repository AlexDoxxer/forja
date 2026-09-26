"""Administración: ajustes globales, usuarios e ingesta en segundo plano (con ``audit_log``)."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.common import encode_cursor
from app.core.config import Settings
from app.core.errors import conflict, not_found
from app.core.ids import uuid7
from app.core.logging import get_logger
from app.models.catalog import IngestRun
from app.models.user import AuthSession, User
from app.schemas import api
from app.services import settings as app_settings
from app.services.audit import audit
from app.services.catalog_cache import CatalogCache

STALE_RUN = timedelta(hours=1)
# Exige el dataset completo (1.324 nombres ES); los tests lo desactivan con un dataset reducido.
FULL_DATASET = True
_log = get_logger("forja.ingest")


# ---------------------------------------------------------------------- ajustes
async def get_admin_settings(db: AsyncSession, settings: Settings) -> api.AdminSettings:
    last = (
        await db.execute(
            select(IngestRun.commit)
            .where(IngestRun.status == "succeeded", IngestRun.dry_run.is_(False))
            .order_by(IngestRun.finished_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return api.AdminSettings(
        registration_open=await app_settings.registration_open(db, settings),
        diet_feature_enabled=await app_settings.diet_feature_enabled(db, settings),
        media_require_auth=settings.media_require_auth,
        dataset_commit=last or settings.dataset_commit,
    )


async def update_admin_settings(
    db: AsyncSession, settings: Settings, actor: User, body: api.AdminSettingsUpdate
) -> api.AdminSettings:
    await app_settings.set_bool(db, app_settings.REGISTRATION_OPEN, body.registration_open)
    await app_settings.set_bool(db, app_settings.DIET_FEATURE_ENABLED, body.diet_feature_enabled)
    await audit(
        db,
        "admin.settings.update",
        actor=actor.id,
        details={
            "registration_open": body.registration_open,
            "diet_feature_enabled": body.diet_feature_enabled,
        },
    )
    await db.commit()
    return await get_admin_settings(db, settings)


# --------------------------------------------------------------------- usuarios
def user_dto(u: User) -> api.AdminUser:
    return api.AdminUser(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        role=cast("Any", u.role),
        is_active=u.is_active,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


async def list_users(
    db: AsyncSession, *, q: str | None, cursor: dict[str, Any] | None, limit: int
) -> api.AdminUserPage:
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.display_name.ilike(like)))
    if cursor:
        created = datetime.fromisoformat(str(cursor["c"]))
        last = uuid.UUID(str(cursor["i"]))
        stmt = stmt.where(
            or_(User.created_at > created, (User.created_at == created) & (User.id > last))
        )
    rows = list(
        (await db.execute(stmt.order_by(User.created_at, User.id).limit(limit + 1))).scalars()
    )
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor({"c": rows[-1].created_at.isoformat(), "i": str(rows[-1].id)})
    return api.AdminUserPage(items=[user_dto(u) for u in rows], next_cursor=next_cursor)


async def other_active_admins(db: AsyncSession, excluding: uuid.UUID) -> int:
    return (
        await db.execute(
            select(func.count()).where(
                User.role == "admin", User.is_active.is_(True), User.id != excluding
            )
        )
    ).scalar_one()


async def update_user(
    db: AsyncSession, actor: User, user_id: uuid.UUID, body: api.AdminUserUpdate
) -> api.AdminUser:
    target = await db.get(User, user_id)
    if target is None:
        raise not_found("El usuario no existe.")
    new_role = body.role or target.role
    new_active = target.is_active if body.is_active is None else body.is_active
    demoting = (
        target.role == "admin" and target.is_active and (new_role != "admin" or not new_active)
    )
    if demoting and await other_active_admins(db, target.id) == 0:
        raise conflict("last_admin", "No se puede degradar ni desactivar al último administrador.")
    target.role = new_role
    target.is_active = new_active
    if not new_active:
        await db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
    await audit(
        db,
        "admin.user.update",
        actor=actor.id,
        target=str(target.id),
        details={"role": new_role, "is_active": new_active},
    )
    await db.commit()
    return user_dto(target)


# ----------------------------------------------------------------------- ingesta
def run_dto(r: IngestRun) -> api.IngestRun:
    return api.IngestRun(
        id=r.id,
        status=cast("Any", r.status),
        dry_run=r.dry_run,
        commit=r.commit,
        started_at=r.started_at,
        finished_at=r.finished_at,
        triggered_by=r.triggered_by,
        counts=api.IngestCounts.model_validate(r.counts) if r.counts else None,
        diff=api.IngestDiff.model_validate(r.diff) if r.diff else None,
        errors=list(r.errors or []),
        warnings=list(r.warnings or []),
    )


async def start_ingest(
    db: AsyncSession, settings: Settings, actor: User, body: api.IngestRequest
) -> IngestRun:
    active = (
        await db.execute(
            select(IngestRun.id).where(
                IngestRun.status.in_(("queued", "running")),
                IngestRun.created_at > datetime.now(UTC) - STALE_RUN,
            )
        )
    ).first()
    if active is not None:
        raise conflict("ingest_running", "Ya hay una ingesta en curso.")
    run = IngestRun(
        id=uuid7(),
        commit=settings.dataset_commit,
        status="queued",
        dry_run=body.dry_run,
        triggered_by=actor.id,
        errors=[],
        warnings=[],
    )
    db.add(run)
    await audit(
        db,
        "admin.ingest.start",
        actor=actor.id,
        target=str(run.id),
        details={"dry_run": body.dry_run},
    )
    await db.commit()
    return run


async def list_runs(
    db: AsyncSession, *, cursor: dict[str, Any] | None, limit: int
) -> api.IngestRunPage:
    stmt = select(IngestRun)
    if cursor:
        created = datetime.fromisoformat(str(cursor["c"]))
        last = uuid.UUID(str(cursor["i"]))
        stmt = stmt.where(
            or_(
                IngestRun.created_at < created,
                (IngestRun.created_at == created) & (IngestRun.id < last),
            )
        )
    rows = list(
        (
            await db.execute(
                stmt.order_by(IngestRun.created_at.desc(), IngestRun.id.desc()).limit(limit + 1)
            )
        ).scalars()
    )
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = encode_cursor({"c": rows[-1].created_at.isoformat(), "i": str(rows[-1].id)})
    return api.IngestRunPage(items=[run_dto(r) for r in rows], next_cursor=next_cursor)


def _pipeline(
    settings: Settings, database_url: str, actor: uuid.UUID | None, dry_run: bool
) -> uuid.UUID:
    """Fetch + enriquecimiento + carga (bloqueante, en un hilo). Devuelve el id de la corrida
    que crea ``load_catalog``."""
    from ingest.catalog import build_catalog
    from ingest.load import load_catalog
    from ingest.media import SOURCE_DIR, fetch, read_manifest, verify_media
    from ingest.source import load_dataset
    from ingest.specs import load_specs

    fetch(str(settings.dataset_repo), settings.dataset_commit, settings.media_root, dry_run=dry_run)
    manifest = read_manifest(settings.media_root)
    if manifest is None:
        msg = "No existe manifest.json tras el fetch"
        raise RuntimeError(msg)
    verified = verify_media(settings.media_root, manifest)
    if not verified.ok:
        raise RuntimeError("; ".join(verified.errors[:20]))
    specs = load_specs()
    catalog = build_catalog(
        load_dataset(settings.media_root / SOURCE_DIR), specs, full_dataset=FULL_DATASET
    )
    result = asyncio.run(
        load_catalog(
            database_url,
            catalog,
            manifest,
            specs,
            media_verified=verified.verified,
            dry_run=dry_run,
            triggered_by=actor,
        )
    )
    return result.run_id


async def run_ingest_task(
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    cache: CatalogCache,
    run_id: uuid.UUID,
) -> None:
    """Tarea de fondo: ejecuta la ingesta y refleja el resultado en la corrida encolada."""
    async with sessionmaker() as db:
        run = await db.get(IngestRun, run_id)
        if run is None:
            return
        run.status = "running"
        run.started_at = datetime.now(UTC)
        dry_run, actor = run.dry_run, run.triggered_by
        await db.commit()
    try:
        inner_id = await asyncio.to_thread(
            _pipeline, settings, str(settings.database_url), actor, dry_run
        )
    except Exception as exc:
        _log.warning("ingest_failed", extra={"error_type": type(exc).__name__})
        async with sessionmaker() as db:
            await db.execute(
                update(IngestRun)
                .where(IngestRun.id == run_id)
                .values(
                    status="failed",
                    finished_at=datetime.now(UTC),
                    errors=[
                        f"{type(exc).__name__}: {str(exc).splitlines()[0][:500] if str(exc) else ''}"
                    ],
                )
            )
            await db.commit()
        return
    async with sessionmaker() as db:
        inner = await db.get(IngestRun, inner_id)
        outer = await db.get(IngestRun, run_id)
        if inner is not None and outer is not None:
            outer.status = inner.status
            outer.finished_at = inner.finished_at
            outer.counts = inner.counts
            outer.diff = inner.diff
            outer.commit = inner.commit
            outer.checksums_sha256 = inner.checksums_sha256
            outer.errors = inner.errors
            outer.warnings = inner.warnings
            await db.execute(delete(IngestRun).where(IngestRun.id == inner_id))
        await db.commit()
    cache.invalidate()
