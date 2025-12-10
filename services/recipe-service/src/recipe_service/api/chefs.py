"""
요리사 API 라우터

요리사 조회 엔드포인트를 정의합니다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.database import get_session
from recipe_service.schemas import (
    ChefDetail,
    ChefListItem,
    ChefListResponse,
    RecipeListResponse,
)
from recipe_service.schemas.pagination import PaginationParams
from recipe_service.services import ChefService, get_chef_service, RecipeService, get_recipe_service

router = APIRouter(prefix="/chefs", tags=["chefs"])


@router.get(
    "/popular",
    response_model=list[ChefListItem],
    summary="인기 요리사 조회",
    description="레시피 수와 조회수 기준으로 정렬된 인기 요리사 목록을 조회합니다.",
    responses={
        200: {"description": "인기 요리사 목록"},
    },
)
async def get_popular_chefs(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
) -> list[ChefListItem]:
    """
    인기 요리사 조회

    - **limit**: 조회할 요리사 수 (기본 10, 최대 50)
    """
    service = await get_chef_service(session)
    return await service.get_popular(limit=limit)


@router.get(
    "/{chef_id}",
    response_model=ChefDetail,
    summary="요리사 상세 조회",
    description="요리사 ID로 상세 정보를 조회합니다. 플랫폼 정보가 포함됩니다.",
    responses={
        200: {"description": "요리사 상세 정보"},
        404: {"description": "요리사를 찾을 수 없음"},
    },
)
async def get_chef(
    chef_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChefDetail:
    """
    요리사 상세 조회

    - **chef_id**: 요리사 UUID
    """
    service = await get_chef_service(session)
    return await service.get_by_id(chef_id)


@router.get(
    "/{chef_id}/recipes",
    response_model=RecipeListResponse,
    summary="요리사별 레시피 조회",
    description="특정 요리사의 레시피 목록을 조회합니다.",
    responses={
        200: {"description": "요리사의 레시피 목록"},
        404: {"description": "요리사를 찾을 수 없음"},
    },
)
async def get_chef_recipes(
    chef_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="조회 개수")] = 20,
) -> RecipeListResponse:
    """
    요리사별 레시피 조회

    - **chef_id**: 요리사 UUID
    - **cursor**: 다음 페이지를 위한 커서 (첫 페이지는 생략)
    - **limit**: 조회할 레시피 수 (기본 20, 최대 100)
    """
    # 요리사 존재 확인
    chef_service = await get_chef_service(session)
    await chef_service.get_by_id(chef_id)  # 404 if not found

    # 레시피 조회
    recipe_service = await get_recipe_service(session)
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await recipe_service.get_by_chef(chef_id, pagination)


@router.get(
    "",
    response_model=ChefListResponse,
    summary="요리사 목록 조회",
    description="요리사 목록을 커서 기반 페이지네이션으로 조회합니다.",
    responses={
        200: {"description": "요리사 목록"},
        400: {"description": "잘못된 커서 값"},
    },
)
async def get_chefs(
    session: Annotated[AsyncSession, Depends(get_session)],
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="조회 개수")] = 20,
    specialty: Annotated[str | None, Query(description="전문 분야 필터")] = None,
    is_verified: Annotated[bool | None, Query(description="인증 여부 필터")] = None,
) -> ChefListResponse:
    """
    요리사 목록 조회 (커서 기반 페이지네이션)

    - **cursor**: 다음 페이지를 위한 커서 (첫 페이지는 생략)
    - **limit**: 조회할 요리사 수 (기본 20, 최대 100)
    - **specialty**: 전문 분야로 필터링
    - **is_verified**: 인증 여부로 필터링
    """
    service = await get_chef_service(session)
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await service.get_list(
        pagination,
        specialty=specialty,
        is_verified=is_verified,
    )
