"""Módulo de nutrición (tras ``diet_enabled`` y ``DIET_FEATURE_ENABLED``)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Query, Request, status
from forja_nutrition.models import DietType, FoodCategory

from app.api.common import decode_cursor, errors
from app.api.deps import AppSettings, CurrentUserDep, Db, get_rate_limiter
from app.schemas import api
from app.services import nutrition as service

router = APIRouter(tags=["nutrition"])


@router.get(
    "/nutrition/settings",
    operation_id="getNutritionSettings",
    response_model=api.NutritionSettings,
    responses=errors(401),
)
async def get_nutrition_settings(user: CurrentUserDep, db: Db, settings: AppSettings) -> api.NutritionSettings:
    return await service.get_settings(db, settings, user)


@router.put(
    "/nutrition/settings",
    operation_id="updateNutritionSettings",
    response_model=api.NutritionSettings,
    responses=errors(401, 403, 422),
)
async def update_nutrition_settings(
    body: api.NutritionSettingsUpdate, user: CurrentUserDep, db: Db, settings: AppSettings
) -> api.NutritionSettings:
    return await service.update_settings(db, settings, user, body)


@router.post(
    "/nutrition/targets/calculate",
    operation_id="calculateNutritionTarget",
    response_model=api.NutritionTargetRecord,
    responses=errors(401, 403, 422),
)
async def calculate_nutrition_target(
    user: CurrentUserDep,
    db: Db,
    settings: AppSettings,
    body: Annotated[api.NutritionTargetRequest | None, Body()] = None,
) -> api.NutritionTargetRecord:
    return await service.calculate_target(db, settings, user, body)


@router.get(
    "/nutrition/plans",
    operation_id="listMealPlans",
    response_model=api.MealPlanPage,
    responses=errors(401, 403),
)
async def list_meal_plans(
    user: CurrentUserDep,
    db: Db,
    settings: AppSettings,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> api.MealPlanPage:
    return await service.list_plans(db, settings, user, cursor=decode_cursor(cursor), limit=limit)


@router.post(
    "/nutrition/plans",
    operation_id="generateMealPlan",
    status_code=status.HTTP_201_CREATED,
    response_model=api.MealPlanResource,
    responses=errors(401, 403, 422, 429),
)
async def generate_meal_plan(
    body: api.MealPlanCreate,
    request: Request,
    user: CurrentUserDep,
    db: Db,
    settings: AppSettings,
) -> api.MealPlanResource:
    get_rate_limiter(request).check("generator", f"nutrition:{user.id}")
    return await service.create_plan(db, settings, user, body)


@router.get(
    "/nutrition/plans/{plan_id}",
    operation_id="getMealPlan",
    response_model=api.MealPlanResource,
    responses=errors(401, 403, 404),
)
async def get_meal_plan(
    plan_id: uuid.UUID, user: CurrentUserDep, db: Db, settings: AppSettings
) -> api.MealPlanResource:
    return await service.get_plan(db, settings, user, plan_id)


@router.post(
    "/nutrition/plans/{plan_id}/swap",
    operation_id="swapMealPlanFood",
    response_model=api.MealPlanResource,
    responses=errors(401, 403, 404, 422),
)
async def swap_meal_plan_food(
    plan_id: uuid.UUID,
    body: api.MealSwapRequest,
    user: CurrentUserDep,
    db: Db,
    settings: AppSettings,
) -> api.MealPlanResource:
    return await service.swap_food(db, settings, user, plan_id, body)


@router.get(
    "/nutrition/plans/{plan_id}/shopping-list",
    operation_id="getShoppingList",
    response_model=api.ShoppingList,
    responses=errors(401, 403, 404),
)
async def get_shopping_list(
    plan_id: uuid.UUID, user: CurrentUserDep, db: Db, settings: AppSettings
) -> api.ShoppingList:
    return await service.shopping_list(db, settings, user, plan_id)


@router.get(
    "/foods",
    operation_id="listFoods",
    response_model=api.FoodPage,
    responses=errors(401, 403, 422),
)
async def list_foods(
    user: CurrentUserDep,
    db: Db,
    settings: AppSettings,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category: FoodCategory | None = None,
    diet_type: DietType | None = None,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> api.FoodPage:
    return await service.list_foods(
        db,
        settings,
        user,
        q=q,
        category=str(category) if category else None,
        diet_type=str(diet_type) if diet_type else None,
        cursor=decode_cursor(cursor),
        limit=limit,
    )
