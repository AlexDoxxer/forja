"""Salud, disponibilidad y créditos (``/health``, ``/ready``, ``/about``)."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from app.api.deps import AppSettings, Db
from app.models.catalog import Exercise, IngestRun
from app.schemas import api

router = APIRouter(tags=["health", "meta"])

API_VERSION: Final = "1.2.0"
HEALTH_DISCLAIMER: Final = (
    "Forja no sustituye el consejo de profesionales sanitarios ni de entrenamiento."
)
FALLBACK_MEDIA_NOTICE: Final = (
    "Los GIF y miniaturas de ejercicios son © Gym visual — https://gymvisual.com/ y se sirven "
    "sin modificar. No están cubiertos por la licencia MIT del dataset."
)


def _app_version() -> str:
    try:
        return version("forja-backend")
    except PackageNotFoundError:  # pragma: no cover - solo sin instalar el paquete
        return "0.0.0"


def _read(path: Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


@router.get("/health", operation_id="getHealth", response_model=api.HealthStatus)
async def get_health() -> api.HealthStatus:
    return api.HealthStatus(status="ok")


@router.get(
    "/ready",
    operation_id="getReadiness",
    response_model=api.ReadinessStatus,
    responses={503: {"model": api.ReadinessStatus, "description": "No listo"}},
)
async def get_readiness(db: Db, settings: AppSettings) -> JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
        database = True
    except Exception:
        database = False
    media = (settings.media_root / "manifest.json").is_file()
    ready = database and media
    body = api.ReadinessStatus(
        status="ready" if ready else "not_ready",
        checks=api.Checks(database=database, media=media),
    )
    return JSONResponse(body.model_dump(mode="json"), status_code=200 if ready else 503)


@router.get("/about", operation_id="getAbout", response_model=api.AboutInfo)
async def get_about(db: Db, settings: AppSettings) -> api.AboutInfo:
    from forja_engine import ENGINE_VERSION  # noqa: PLC0415
    from forja_nutrition import NUTRITION_VERSION  # noqa: PLC0415

    last = (
        await db.execute(
            select(IngestRun)
            .where(IngestRun.status == "succeeded", IngestRun.dry_run.is_(False))
            .order_by(IngestRun.finished_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    count = (await db.execute(select(func.count()).select_from(Exercise))).scalar_one()
    licenses = settings.media_root / "LICENSES"
    return api.AboutInfo(
        app_version=_app_version(),
        api_version=API_VERSION,
        engine_version=ENGINE_VERSION,
        nutrition_version=NUTRITION_VERSION,
        dataset=api.Dataset(
            repo=str(settings.dataset_repo),  # type: ignore[arg-type]  # AnyUrl acepta str
            commit=last.commit if last else settings.dataset_commit,
            ingested_at=last.finished_at if last else None,
            exercise_count=count,
        ),
        licenses=api.Licenses(
            dataset_mit=_read(licenses / "LICENSE", "MIT License — hasaneyldrm/exercises-dataset"),
            media_notice=_read(licenses / "NOTICE.md", FALLBACK_MEDIA_NOTICE),
        ),
        media_attribution=api.MediaAttribution(text="© Gym visual", url="https://gymvisual.com/"),
        health_disclaimer_es=HEALTH_DISCLAIMER,
    )
