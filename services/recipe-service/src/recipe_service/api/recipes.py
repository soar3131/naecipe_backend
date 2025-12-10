"""
레시피 API 라우터

레시피 조회 엔드포인트를 정의합니다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.database import get_session
from recipe_service.schemas import (
    RecipeDetail,
    RecipeListItem,
    RecipeListResponse,
)
from recipe_service.schemas.pagination import PaginationParams
from recipe_service.services import RecipeService, get_recipe_service

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get(
    "",
    response_model=RecipeListResponse,
    summary="레시피 목록 조회",
    description="레시피 목록을 커서 기반 페이지네이션으로 조회합니다.",
    responses={
        200: {"description": "레시피 목록"},
        400: {"description": "잘못된 커서 값"},
    },
)
async def get_recipes(
    session: Annotated[AsyncSession, Depends(get_session)],
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="조회 개수")] = 20,
    tag: Annotated[str | None, Query(description="태그 필터")] = None,
    difficulty: Annotated[
        str | None,
        Query(description="난이도 필터 (easy, medium, hard)"),
    ] = None,
) -> RecipeListResponse:
    """
    레시피 목록 조회 (커서 기반 페이지네이션)

    - **cursor**: 다음 페이지를 위한 커서 (첫 페이지는 생략)
    - **limit**: 조회할 레시피 수 (기본 20, 최대 100)
    - **tag**: 태그로 필터링
    - **difficulty**: 난이도로 필터링 (easy, medium, hard)
    """
    service = await get_recipe_service(session)
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await service.get_list(pagination, tag=tag, difficulty=difficulty)


@router.get(
    "/popular",
    response_model=list[RecipeListItem],
    summary="인기 레시피 조회",
    description="노출 점수와 조회수 기준으로 정렬된 인기 레시피 목록을 조회합니다.",
    responses={
        200: {"description": "인기 레시피 목록"},
    },
)
async def get_popular_recipes(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
    category: Annotated[
        str | None,
        Query(description="카테고리 필터 (dish_type, cuisine, meal_type 등)"),
    ] = None,
) -> list[RecipeListItem]:
    """
    인기 레시피 조회

    - **limit**: 조회할 레시피 수 (기본 10, 최대 50)
    - **category**: 태그 카테고리로 필터링
    """
    service = await get_recipe_service(session)
    return await service.get_popular(limit=limit, category=category)


@router.get(
    "/{recipe_id}",
    response_model=RecipeDetail,
    summary="레시피 상세 조회",
    description="레시피 ID로 상세 정보를 조회합니다. 재료, 조리 단계, 태그 정보가 포함됩니다.",
    responses={
        200: {"description": "레시피 상세 정보"},
        404: {"description": "레시피를 찾을 수 없음"},
    },
)
async def get_recipe(
    recipe_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecipeDetail:
    """
    레시피 상세 조회

    - **recipe_id**: 레시피 UUID
    """
    service = await get_recipe_service(session)
    return await service.get_by_id(recipe_id)
