"""Generador (vista previa sin persistir) y programas guardados."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Query, Request, Response, status
from forja_engine import models as em

from app.api.common import decode_cursor, errors
from app.api.deps import (
    AppSettings,
    Catalog,
    CurrentUserDep,
    Db,
    EngineTables,
    get_rate_limiter,
)
from app.schemas import api
from app.services import catalog as catalog_service
from app.services import engine, exports
from app.services import programs as service

router = APIRouter(tags=["generator", "programs"])

ProgramId = Annotated[uuid.UUID, ...]


def _plan_exercise_ids(plan: api.ProgramPlan) -> list[str]:
    ids: list[str] = []
    for week in plan.weeks:
        for day in week.days:
            for block in day.blocks:
                for ex in block.exercises:
                    ids.append(ex.exercise_id)
                    ids.extend(a.root for a in ex.alternatives)
    return ids


async def _preview(db: Db, user: CurrentUserDep, plan: api.ProgramPlan) -> api.GeneratorPreview:
    exercises = await catalog_service.summaries_for(db, _plan_exercise_ids(plan), user.id)
    return api.GeneratorPreview(plan=plan, exercises=exercises)


# -------------------------------------------------------------------- generador
@router.post(
    "/generator/preview",
    operation_id="previewProgram",
    response_model=api.GeneratorPreview,
    responses=errors(401, 403, 422, 429),
)
async def preview_program(
    body: api.GeneratorInput,
    request: Request,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.GeneratorPreview:
    get_rate_limiter(request).check("generator", str(user.id))
    plan = await engine.generate(await catalog.cards(), tables, body)
    return await _preview(db, user, plan)


@router.post(
    "/generator/preview/regenerate-day",
    operation_id="previewRegenerateDay",
    response_model=api.GeneratorPreview,
    responses=errors(401, 403, 422, 429),
)
async def preview_regenerate_day(
    body: api.PreviewRegenerateDayRequest,
    request: Request,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.GeneratorPreview:
    get_rate_limiter(request).check("generator", str(user.id))
    plan = await engine.regenerate_day(
        await catalog.cards(), tables, engine.to_engine_plan(body.plan), body.day_index, body.seed
    )
    return await _preview(db, user, engine.to_api_plan(plan))


@router.post(
    "/generator/preview/swap",
    operation_id="previewSwapExercise",
    response_model=api.GeneratorPreview,
    responses=errors(401, 403, 422),
)
async def preview_swap(
    body: api.PreviewSwapRequest,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.GeneratorPreview:
    plan = await engine.swap_exercise(
        await catalog.cards(),
        tables,
        engine.to_engine_plan(body.plan),
        em.SlotAddress.model_validate(body.address.model_dump()),
        [value.root for value in body.exclude_ids],
        body.replacement_id.root if body.replacement_id else None,
        apply_to_all_weeks=body.apply_to_all_weeks,
    )
    return await _preview(db, user, engine.to_api_plan(plan))


# ---------------------------------------------------------------------- programas
@router.get(
    "/programs", operation_id="listPrograms", response_model=api.ProgramPage, responses=errors(401)
)
async def list_programs(
    user: CurrentUserDep,
    db: Db,
    archived: bool = False,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> api.ProgramPage:
    return await service.list_programs(
        db, user, archived=archived, cursor=decode_cursor(cursor), limit=limit
    )


@router.post(
    "/programs",
    operation_id="createProgram",
    status_code=status.HTTP_201_CREATED,
    response_model=api.ProgramDetail,
    responses=errors(401, 403, 422),
)
async def create_program(
    body: Annotated[api.ProgramCreate, Body()],
    response: Response,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.ProgramDetail:
    cards = await catalog.cards()
    payload = body.root
    if isinstance(payload, api.ProgramCreateFromPlan):
        created = await service.create_from_plan(db, user, payload, cards, tables)
    else:
        created = await service.create_manual(db, user, payload, cards, tables)
    response.headers["Location"] = f"/api/v1/programs/{created.id}"
    return created


@router.get(
    "/programs/{program_id}",
    operation_id="getProgram",
    response_model=api.ProgramDetail,
    responses=errors(401, 404),
)
async def get_program(program_id: uuid.UUID, user: CurrentUserDep, db: Db) -> api.ProgramDetail:
    return await service.get_detail(db, user, program_id)


@router.patch(
    "/programs/{program_id}",
    operation_id="updateProgram",
    response_model=api.ProgramSummary,
    responses=errors(401, 403, 404, 422),
)
async def update_program(
    program_id: uuid.UUID, body: api.ProgramUpdate, user: CurrentUserDep, db: Db
) -> api.ProgramSummary:
    return await service.rename_or_archive(db, user, program_id, body)


@router.delete(
    "/programs/{program_id}",
    operation_id="deleteProgram",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=errors(401, 403, 404),
)
async def delete_program(program_id: uuid.UUID, user: CurrentUserDep, db: Db) -> None:
    await service.delete_program(db, user, program_id)


@router.post(
    "/programs/{program_id}/activate",
    operation_id="activateProgram",
    response_model=api.ProgramSummary,
    responses=errors(401, 403, 404, 409),
)
async def activate_program(
    program_id: uuid.UUID, user: CurrentUserDep, db: Db
) -> api.ProgramSummary:
    return await service.activate(db, user, program_id)


@router.post(
    "/programs/{program_id}/duplicate",
    operation_id="duplicateProgram",
    status_code=status.HTTP_201_CREATED,
    response_model=api.ProgramDetail,
    responses=errors(401, 403, 404, 422),
)
async def duplicate_program(
    program_id: uuid.UUID,
    response: Response,
    user: CurrentUserDep,
    db: Db,
    body: Annotated[api.ProgramDuplicateRequest | None, Body()] = None,
) -> api.ProgramDetail:
    created = await service.duplicate(db, user, program_id, body)
    response.headers["Location"] = f"/api/v1/programs/{created.id}"
    return created


@router.post(
    "/programs/{program_id}/regenerate-day",
    operation_id="regenerateProgramDay",
    response_model=api.ProgramDetail,
    responses=errors(401, 403, 404, 409, 422, 429),
)
async def regenerate_program_day(
    program_id: uuid.UUID,
    body: api.RegenerateDayRequest,
    request: Request,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.ProgramDetail:
    get_rate_limiter(request).check("generator", str(user.id))
    return await service.regenerate_day(db, user, program_id, body, await catalog.cards(), tables)


@router.post(
    "/programs/{program_id}/swap",
    operation_id="swapProgramExercise",
    response_model=api.ProgramDetail,
    responses=errors(401, 403, 404, 422),
)
async def swap_program_exercise(
    program_id: uuid.UUID,
    body: api.SwapRequest,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.ProgramDetail:
    return await service.swap(db, user, program_id, body, await catalog.cards(), tables)


@router.put(
    "/programs/{program_id}/days/{day_id}",
    operation_id="replaceProgramDay",
    response_model=api.ProgramDetail,
    responses=errors(401, 403, 404, 422),
)
async def replace_program_day(
    program_id: uuid.UUID,
    day_id: uuid.UUID,
    body: api.DayEdit,
    user: CurrentUserDep,
    db: Db,
    catalog: Catalog,
    tables: EngineTables,
) -> api.ProgramDetail:
    return await service.replace_day(
        db, user, program_id, day_id, body, await catalog.cards(), tables
    )


@router.get(
    "/programs/{program_id}/export.pdf",
    operation_id="exportProgramPdf",
    responses={200: {"content": {"application/pdf": {}}}, **errors(401, 404)},
    response_class=Response,
)
async def export_program_pdf(
    program_id: uuid.UUID,
    user: CurrentUserDep,
    db: Db,
    settings: AppSettings,
    lang: Annotated[str | None, Query(pattern=r"^(es|en)$")] = None,
) -> Response:
    detail = await service.get_detail(db, user, program_id)
    document = await exports.render_pdf(detail, lang or user.locale, settings.media_root)
    return Response(
        document,
        media_type="application/pdf",
        headers={"Content-Disposition": exports.disposition(detail.name, "pdf")},
    )


@router.get(
    "/programs/{program_id}/calendar.ics",
    operation_id="exportProgramCalendar",
    responses={200: {"content": {"text/calendar": {}}}, **errors(401, 404, 422)},
    response_class=Response,
)
async def export_program_calendar(
    program_id: uuid.UUID,
    user: CurrentUserDep,
    db: Db,
    start_date: date | None = None,
) -> Response:
    detail = await service.get_detail(db, user, program_id)
    body = exports.render_ics(detail, start_date)
    return Response(
        body,
        media_type="text/calendar",
        headers={"Content-Disposition": exports.disposition(detail.name, "ics")},
    )
