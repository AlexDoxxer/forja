"""Adaptadores entre los DTOs de la API y los motores (``forja_engine`` / ``forja_nutrition``).

Los esquemas de la API (generados desde ``contracts/openapi.yaml``) y los DTOs del motor
tienen la misma forma JSON, por lo que la conversión es ``model_dump`` → ``model_validate``.
Los errores del motor se convierten en 422 en ``app.core.errors``.
"""

import asyncio
from collections.abc import Callable, Sequence
from typing import Any, Final, TypeVar

import forja_engine
from forja_engine import PlanOperationError, Tables
from forja_engine import models as em

from app.core.errors import ProblemError
from app.schemas import api

T = TypeVar("T")

ENGINE_VERSION: Final = forja_engine.ENGINE_VERSION


def to_engine_input(body: api.GeneratorInput) -> em.GeneratorInput:
    """``GeneratorInput`` de la API → motor (los ``null`` opcionales toman el defecto)."""
    return em.GeneratorInput.model_validate(body.model_dump(mode="json", exclude_none=True))


def to_engine_plan(plan: api.ProgramPlan) -> em.ProgramPlan:
    return em.ProgramPlan.model_validate(plan.model_dump(mode="json"))


def to_api_plan(plan: em.ProgramPlan) -> api.ProgramPlan:
    return api.ProgramPlan.model_validate(plan.model_dump(mode="json"))


def to_api_warnings(warnings: Sequence[em.PlanWarning]) -> list[api.PlanWarning]:
    return [api.PlanWarning.model_validate(w.model_dump(mode="json")) for w in warnings]


async def run_engine(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Ejecuta una operación pura del motor fuera del bucle de eventos.

    ``PlanOperationError`` (dirección o reemplazo imposible) ⇒ 422; ``ValidationError`` de
    pydantic (entrada inválida) lo convierte el manejador global.
    """
    try:
        return await asyncio.to_thread(func, *args, **kwargs)
    except PlanOperationError as exc:
        raise ProblemError(422, "validation_error", str(exc)) from exc


async def generate(
    catalog: Sequence[em.ExerciseCard], tables: Tables, body: api.GeneratorInput
) -> api.ProgramPlan:
    plan = await run_engine(forja_engine.generate, to_engine_input(body), catalog, tables)
    return to_api_plan(plan)


async def regenerate_day(
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
    plan: em.ProgramPlan,
    day_index: int,
    seed: int | None,
) -> em.ProgramPlan:
    return await run_engine(forja_engine.regenerate_day, plan, catalog, day_index, seed, tables)


async def swap_exercise(
    catalog: Sequence[em.ExerciseCard],
    tables: Tables,
    plan: em.ProgramPlan,
    address: em.SlotAddress,
    exclude_ids: Sequence[str],
    replacement_id: str | None,
    *,
    apply_to_all_weeks: bool,
) -> em.ProgramPlan:
    return await run_engine(
        forja_engine.swap_exercise,
        plan,
        catalog,
        address,
        exclude_ids,
        replacement_id,
        apply_to_all_weeks,
        tables,
    )


async def rebalance(
    catalog: Sequence[em.ExerciseCard], tables: Tables, plan: em.ProgramPlan
) -> em.ProgramPlan:
    return await run_engine(forja_engine.rebalance_after_edit, plan, catalog, tables)


async def validate(
    catalog: Sequence[em.ExerciseCard], tables: Tables, plan: em.ProgramPlan
) -> tuple[em.PlanWarning, ...]:
    return await run_engine(forja_engine.validate_plan, plan, catalog, tables)


def plan_invalid(violations: Sequence[em.PlanWarning]) -> ProblemError:
    """422 ``plan_invalid`` con la lista de reglas duras incumplidas."""
    return ProblemError(
        422,
        "plan_invalid",
        "El programa incumple reglas de seguridad o de coherencia del motor.",
        extra={"violations": [v.model_dump(mode="json") for v in violations]},
    )
