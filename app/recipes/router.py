"""
Recipes 모듈 라우터

레시피, 요리사, 검색 엔드포인트를 정의합니다.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession
from app.recipes.schemas import (
    CategoryPopularListResponse,
    ChefDetail,
    ChefListItem,
    ChefListResponse,
    PaginationParams,
    RecipeDetail,
    RecipeListItem,
    RecipeListResponse,
    RelatedByTagsListResponse,
    SameChefRecipeListResponse,
    SearchQueryParams,
    SearchResult,
    SimilarRecipeListResponse,
)
from app.recipes.services import (
    ChefService,
    CursorError,
    RecipeService,
    SearchService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================================================
# 레시피 엔드포인트
# ==========================================================================


@router.get(
    "/recipes",
    response_model=RecipeListResponse,
    summary="레시피 목록 조회",
    description="레시피 목록을 커서 기반 페이지네이션으로 조회합니다.",
    tags=["recipes"],
    responses={
        200: {"description": "레시피 목록"},
        400: {"description": "잘못된 커서 값"},
    },
)
async def get_recipes(
    db: DbSession,
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
    service = RecipeService(db)
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await service.get_list(pagination, tag=tag, difficulty=difficulty)


@router.get(
    "/recipes/popular",
    response_model=list[RecipeListItem],
    summary="인기 레시피 조회",
    description="노출 점수와 조회수 기준으로 정렬된 인기 레시피 목록을 조회합니다.",
    tags=["recipes"],
    responses={
        200: {"description": "인기 레시피 목록"},
    },
)
async def get_popular_recipes(
    db: DbSession,
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
    service = RecipeService(db)
    return await service.get_popular(limit=limit, category=category)


@router.get(
    "/recipes/search",
    response_model=SearchResult,
    summary="레시피 검색",
    description="""
레시피를 검색합니다.

**검색 대상**:
- 레시피 제목
- 레시피 설명
- 재료명
- 요리사명

**필터**:
- `difficulty`: 난이도 (easy, medium, hard)
- `max_cook_time`: 최대 조리시간 (분)
- `tag`: 태그명
- `chef_id`: 요리사 ID

**정렬**:
- `relevance`: 관련도순 (기본값)
- `latest`: 최신순
- `cook_time`: 조리시간순
- `popularity`: 인기순

**페이지네이션**:
커서 기반 페이지네이션을 사용합니다.
`next_cursor`를 다음 요청의 `cursor` 파라미터로 전달하세요.
""",
    tags=["search"],
)
async def search_recipes(
    db: DbSession,
    q: Annotated[
        str | None,
        Query(max_length=100, description="검색 키워드"),
    ] = None,
    difficulty: Annotated[
        str | None,
        Query(
            pattern="^(easy|medium|hard)$",
            description="난이도 필터",
        ),
    ] = None,
    max_cook_time: Annotated[
        int | None,
        Query(ge=1, le=1440, description="최대 조리시간 (분)"),
    ] = None,
    tag: Annotated[
        str | None,
        Query(max_length=50, description="태그 필터"),
    ] = None,
    chef_id: Annotated[
        UUID | None,
        Query(description="요리사 ID 필터"),
    ] = None,
    sort: Annotated[
        str,
        Query(
            pattern="^(relevance|latest|cook_time|popularity)$",
            description="정렬 기준",
        ),
    ] = "relevance",
    cursor: Annotated[
        str | None,
        Query(max_length=200, description="페이지네이션 커서"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="결과 개수"),
    ] = 20,
) -> SearchResult:
    """레시피 검색 API"""
    params = SearchQueryParams(
        q=q,
        difficulty=difficulty,
        max_cook_time=max_cook_time,
        tag=tag,
        chef_id=chef_id,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )

    try:
        service = SearchService(db)
        return await service.search(params)
    except CursorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="검색 처리 중 오류가 발생했습니다",
        )


@router.get(
    "/recipes/{recipe_id}",
    response_model=RecipeDetail,
    summary="레시피 상세 조회",
    description="레시피 ID로 상세 정보를 조회합니다. 재료, 조리 단계, 태그 정보가 포함됩니다.",
    tags=["recipes"],
    responses={
        200: {"description": "레시피 상세 정보"},
        404: {"description": "레시피를 찾을 수 없음"},
    },
)
async def get_recipe(
    recipe_id: str,
    db: DbSession,
) -> RecipeDetail:
    """
    레시피 상세 조회

    - **recipe_id**: 레시피 UUID
    """
    service = RecipeService(db)
    return await service.get_by_id(recipe_id)


# ==========================================================================
# 요리사 엔드포인트
# ==========================================================================


@router.get(
    "/chefs",
    response_model=ChefListResponse,
    summary="요리사 목록 조회",
    description="요리사 목록을 커서 기반 페이지네이션으로 조회합니다.",
    tags=["chefs"],
    responses={
        200: {"description": "요리사 목록"},
        400: {"description": "잘못된 커서 값"},
    },
)
async def get_chefs(
    db: DbSession,
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
    service = ChefService(db)
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await service.get_list(
        pagination,
        specialty=specialty,
        is_verified=is_verified,
    )


@router.get(
    "/chefs/popular",
    response_model=list[ChefListItem],
    summary="인기 요리사 조회",
    description="레시피 수와 조회수 기준으로 정렬된 인기 요리사 목록을 조회합니다.",
    tags=["chefs"],
    responses={
        200: {"description": "인기 요리사 목록"},
    },
)
async def get_popular_chefs(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
) -> list[ChefListItem]:
    """
    인기 요리사 조회

    - **limit**: 조회할 요리사 수 (기본 10, 최대 50)
    """
    service = ChefService(db)
    return await service.get_popular(limit=limit)


@router.get(
    "/chefs/{chef_id}",
    response_model=ChefDetail,
    summary="요리사 상세 조회",
    description="요리사 ID로 상세 정보를 조회합니다. 플랫폼 정보가 포함됩니다.",
    tags=["chefs"],
    responses={
        200: {"description": "요리사 상세 정보"},
        404: {"description": "요리사를 찾을 수 없음"},
    },
)
async def get_chef(
    chef_id: str,
    db: DbSession,
) -> ChefDetail:
    """
    요리사 상세 조회

    - **chef_id**: 요리사 UUID
    """
    service = ChefService(db)
    return await service.get_by_id(chef_id)


@router.get(
    "/chefs/{chef_id}/recipes",
    response_model=RecipeListResponse,
    summary="요리사별 레시피 조회",
    description="특정 요리사의 레시피 목록을 조회합니다.",
    tags=["chefs"],
    responses={
        200: {"description": "요리사의 레시피 목록"},
        404: {"description": "요리사를 찾을 수 없음"},
    },
)
async def get_chef_recipes(
    chef_id: str,
    db: DbSession,
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
    chef_service = ChefService(db)
    await chef_service.get_by_id(chef_id)  # 404 if not found

    # 레시피 조회
    recipe_service = RecipeService(db)
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await recipe_service.get_by_chef(chef_id, pagination)


# =============================================================================
# 유사 레시피 추천 엔드포인트
# =============================================================================


@router.get(
    "/{recipe_id}/similar",
    response_model=SimilarRecipeListResponse,
    summary="유사 레시피 추천",
    description="태그, 재료, 조리방식 기반으로 유사한 레시피를 추천합니다.",
    tags=["similar-recipes"],
    responses={
        200: {"description": "유사 레시피 목록"},
        404: {"description": "레시피를 찾을 수 없음"},
    },
)
async def get_similar_recipes(
    recipe_id: str,
    db: DbSession,
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
) -> SimilarRecipeListResponse:
    """
    유사 레시피 추천

    태그(40%), 재료(40%), 조리방식(20%) 기반 복합 유사도로 추천

    - **recipe_id**: 기준 레시피 UUID
    - **cursor**: 다음 페이지를 위한 커서
    - **limit**: 조회할 레시피 수 (기본 10, 최대 50)
    """
    from app.recipes.services import SimilarRecipeService

    service = SimilarRecipeService(db)
    return await service.get_similar_recipes(recipe_id, cursor, limit)


@router.get(
    "/{recipe_id}/same-chef",
    response_model=SameChefRecipeListResponse,
    summary="같은 요리사 레시피",
    description="동일 요리사의 다른 레시피를 조회수 순으로 조회합니다.",
    tags=["similar-recipes"],
    responses={
        200: {"description": "같은 요리사 레시피 목록"},
        404: {"description": "레시피를 찾을 수 없음"},
    },
)
async def get_same_chef_recipes(
    recipe_id: str,
    db: DbSession,
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
) -> SameChefRecipeListResponse:
    """
    같은 요리사 레시피

    동일 요리사의 다른 레시피를 조회수 내림차순으로 조회

    - **recipe_id**: 기준 레시피 UUID
    - **cursor**: 다음 페이지를 위한 커서
    - **limit**: 조회할 레시피 수 (기본 10, 최대 50)
    """
    from app.recipes.services import SimilarRecipeService

    service = SimilarRecipeService(db)
    return await service.get_same_chef_recipes(recipe_id, cursor, limit)


@router.get(
    "/{recipe_id}/related-by-tags",
    response_model=RelatedByTagsListResponse,
    summary="관련 태그 레시피",
    description="공유 태그 기반으로 관련 레시피를 추천합니다.",
    tags=["similar-recipes"],
    responses={
        200: {"description": "관련 태그 레시피 목록"},
        404: {"description": "레시피를 찾을 수 없음"},
    },
)
async def get_related_by_tags(
    recipe_id: str,
    db: DbSession,
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
) -> RelatedByTagsListResponse:
    """
    관련 태그 레시피

    공유 태그 개수가 많은 순으로 관련 레시피 추천

    - **recipe_id**: 기준 레시피 UUID
    - **cursor**: 다음 페이지를 위한 커서
    - **limit**: 조회할 레시피 수 (기본 10, 최대 50)
    """
    from app.recipes.services import SimilarRecipeService

    service = SimilarRecipeService(db)
    return await service.get_related_by_tags(recipe_id, cursor, limit)


@router.get(
    "/{recipe_id}/category-popular",
    response_model=CategoryPopularListResponse,
    summary="카테고리 인기 레시피",
    description="동일 카테고리(난이도+조리시간) 내 인기 레시피를 조회합니다.",
    tags=["similar-recipes"],
    responses={
        200: {"description": "카테고리 인기 레시피 목록"},
        404: {"description": "레시피를 찾을 수 없음"},
    },
)
async def get_category_popular(
    recipe_id: str,
    db: DbSession,
    cursor: Annotated[str | None, Query(description="페이지네이션 커서")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="조회 개수")] = 10,
) -> CategoryPopularListResponse:
    """
    카테고리 인기 레시피

    기준 레시피와 동일 카테고리(난이도+조리시간 범위) 내 조회수 순 정렬

    - **recipe_id**: 기준 레시피 UUID
    - **cursor**: 다음 페이지를 위한 커서
    - **limit**: 조회할 레시피 수 (기본 10, 최대 50)
    """
    from app.recipes.services import SimilarRecipeService

    service = SimilarRecipeService(db)
    return await service.get_category_popular(recipe_id, cursor, limit)
