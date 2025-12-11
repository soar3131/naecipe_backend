"""
Cookbooks 모듈 라우터

레시피북 및 저장된 레시피 CRUD 엔드포인트를 정의합니다.
"""

import logging

from fastapi import APIRouter, Query, status

from app.cookbooks.exceptions import (
    CannotDeleteDefaultCookbookError,
    CookbookNotFoundError,
    RecipeAlreadySavedError,
    SavedRecipeNotFoundError,
)
from app.cookbooks.schemas import (
    CookbookCreateRequest,
    CookbookListResponse,
    CookbookReorderRequest,
    CookbookResponse,
    CookbookUpdateRequest,
    SavedRecipeDetailResponse,
    SavedRecipeListResponse,
    SavedRecipeResponse,
    SaveRecipeRequest,
    UpdateSavedRecipeRequest,
)
from app.cookbooks.services import CookbookService, SavedRecipeService
from app.core.dependencies import CurrentUserId, DbSession

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================================================
# 레시피북 CRUD 엔드포인트
# ==========================================================================


@router.get(
    "/cookbooks",
    response_model=CookbookListResponse,
    summary="레시피북 목록 조회",
    description="사용자의 모든 레시피북 목록을 조회합니다. 기본 레시피북이 없으면 자동 생성됩니다.",
    tags=["cookbooks"],
    responses={
        200: {"description": "레시피북 목록"},
        401: {"description": "인증 필요"},
    },
)
async def get_cookbooks(
    db: DbSession,
    user_id: CurrentUserId,
) -> CookbookListResponse:
    """
    레시피북 목록 조회

    - 기본 레시피북이 없으면 자동 생성
    - sort_order 오름차순 정렬
    - saved_recipe_count 포함
    """
    service = CookbookService(db)
    return await service.get_cookbooks(user_id)


@router.post(
    "/cookbooks",
    response_model=CookbookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="레시피북 생성",
    description="새로운 레시피북을 생성합니다. 이름은 필수입니다.",
    tags=["cookbooks"],
    responses={
        201: {"description": "레시피북 생성됨"},
        401: {"description": "인증 필요"},
        422: {"description": "유효성 검증 실패"},
    },
)
async def create_cookbook(
    db: DbSession,
    user_id: CurrentUserId,
    data: CookbookCreateRequest,
) -> CookbookResponse:
    """
    레시피북 생성

    - **name**: 레시피북 이름 (1-100자, 필수)
    - **description**: 설명 (최대 500자, 선택)
    - **cover_image_url**: 커버 이미지 URL (선택)
    """
    service = CookbookService(db)
    return await service.create_cookbook(user_id, data)


@router.get(
    "/cookbooks/{cookbook_id}",
    response_model=CookbookResponse,
    summary="레시피북 상세 조회",
    description="레시피북 ID로 상세 정보를 조회합니다.",
    tags=["cookbooks"],
    responses={
        200: {"description": "레시피북 상세 정보"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북을 찾을 수 없음"},
    },
)
async def get_cookbook(
    cookbook_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> CookbookResponse:
    """
    레시피북 상세 조회

    - **cookbook_id**: 레시피북 UUID
    """
    service = CookbookService(db)
    return await service.get_cookbook_by_id(cookbook_id, user_id)


@router.put(
    "/cookbooks/{cookbook_id}",
    response_model=CookbookResponse,
    summary="레시피북 수정",
    description="레시피북 정보를 수정합니다. 기본 레시피북도 수정 가능합니다.",
    tags=["cookbooks"],
    responses={
        200: {"description": "레시피북 수정됨"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북을 찾을 수 없음"},
        422: {"description": "유효성 검증 실패"},
    },
)
async def update_cookbook(
    cookbook_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    data: CookbookUpdateRequest,
) -> CookbookResponse:
    """
    레시피북 수정

    - **cookbook_id**: 레시피북 UUID
    - 전달된 필드만 업데이트됨 (부분 수정)
    """
    service = CookbookService(db)
    return await service.update_cookbook(cookbook_id, user_id, data)


@router.delete(
    "/cookbooks/{cookbook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="레시피북 삭제",
    description="레시피북을 삭제합니다. 기본 레시피북은 삭제할 수 없습니다.",
    tags=["cookbooks"],
    responses={
        204: {"description": "레시피북 삭제됨"},
        400: {"description": "기본 레시피북 삭제 불가"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북을 찾을 수 없음"},
    },
)
async def delete_cookbook(
    cookbook_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> None:
    """
    레시피북 삭제

    - **cookbook_id**: 레시피북 UUID
    - 기본 레시피북(is_default=True)은 삭제 불가
    - 삭제 시 저장된 레시피도 함께 삭제됨 (CASCADE)
    """
    service = CookbookService(db)
    await service.delete_cookbook(cookbook_id, user_id)


@router.patch(
    "/cookbooks/reorder",
    response_model=CookbookListResponse,
    summary="레시피북 순서 변경",
    description="레시피북 순서를 변경합니다. 전달된 ID 목록 순서대로 정렬됩니다.",
    tags=["cookbooks"],
    responses={
        200: {"description": "순서 변경 후 레시피북 목록"},
        401: {"description": "인증 필요"},
        422: {"description": "유효성 검증 실패"},
    },
)
async def reorder_cookbooks(
    db: DbSession,
    user_id: CurrentUserId,
    data: CookbookReorderRequest,
) -> CookbookListResponse:
    """
    레시피북 순서 변경

    - **cookbook_ids**: 새로운 순서의 레시피북 ID 목록
    - 목록에 있는 ID만 순서 변경됨
    - 본인 소유가 아닌 ID는 무시됨
    """
    service = CookbookService(db)
    return await service.reorder_cookbooks(user_id, data.cookbook_ids)


# ==========================================================================
# 저장된 레시피 CRUD 엔드포인트 (SPEC-008)
# ==========================================================================


@router.post(
    "/cookbooks/{cookbook_id}/recipes",
    response_model=SavedRecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="레시피 저장",
    description="원본 레시피를 레시피북에 저장합니다.",
    tags=["saved-recipes"],
    responses={
        201: {"description": "레시피 저장됨"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북 또는 레시피를 찾을 수 없음"},
        409: {"description": "이미 저장된 레시피"},
        422: {"description": "유효성 검증 실패"},
    },
)
async def save_recipe(
    cookbook_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    data: SaveRecipeRequest,
) -> SavedRecipeResponse:
    """
    레시피 저장 (User Story 1)

    - **cookbook_id**: 레시피북 UUID
    - **recipe_id**: 저장할 원본 레시피 UUID
    - **memo**: 개인 메모 (최대 1000자, 선택)
    - 동일 레시피 중복 저장 시 409 Conflict 반환
    """
    service = SavedRecipeService(db)
    return await service.save_recipe(cookbook_id, user_id, data)


@router.get(
    "/cookbooks/{cookbook_id}/recipes",
    response_model=SavedRecipeListResponse,
    summary="저장된 레시피 목록 조회",
    description="레시피북에 저장된 레시피 목록을 조회합니다.",
    tags=["saved-recipes"],
    responses={
        200: {"description": "저장된 레시피 목록"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북을 찾을 수 없음"},
    },
)
async def list_saved_recipes(
    cookbook_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    limit: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 항목 수"),
) -> SavedRecipeListResponse:
    """
    저장된 레시피 목록 조회 (User Story 2)

    - **cookbook_id**: 레시피북 UUID
    - **limit**: 페이지당 항목 수 (기본 20, 최대 100)
    - **offset**: 건너뛸 항목 수
    - 저장 시간 내림차순 정렬 (최신순)
    """
    service = SavedRecipeService(db)
    return await service.list_saved_recipes(cookbook_id, user_id, limit, offset)


@router.get(
    "/cookbooks/{cookbook_id}/recipes/{saved_recipe_id}",
    response_model=SavedRecipeDetailResponse,
    summary="저장된 레시피 상세 조회",
    description="저장된 레시피의 상세 정보를 조회합니다.",
    tags=["saved-recipes"],
    responses={
        200: {"description": "저장된 레시피 상세 정보"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북 또는 저장된 레시피를 찾을 수 없음"},
    },
)
async def get_saved_recipe(
    cookbook_id: str,
    saved_recipe_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> SavedRecipeDetailResponse:
    """
    저장된 레시피 상세 조회 (User Story 3)

    - **cookbook_id**: 레시피북 UUID
    - **saved_recipe_id**: 저장된 레시피 UUID
    - 원본 레시피 상세 정보 포함
    """
    service = SavedRecipeService(db)
    return await service.get_saved_recipe(cookbook_id, saved_recipe_id, user_id)


@router.patch(
    "/cookbooks/{cookbook_id}/recipes/{saved_recipe_id}",
    response_model=SavedRecipeResponse,
    summary="저장된 레시피 수정",
    description="저장된 레시피의 메모를 수정합니다.",
    tags=["saved-recipes"],
    responses={
        200: {"description": "저장된 레시피 수정됨"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북 또는 저장된 레시피를 찾을 수 없음"},
        422: {"description": "유효성 검증 실패"},
    },
)
async def update_saved_recipe(
    cookbook_id: str,
    saved_recipe_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    data: UpdateSavedRecipeRequest,
) -> SavedRecipeResponse:
    """
    저장된 레시피 수정 (User Story 4)

    - **cookbook_id**: 레시피북 UUID
    - **saved_recipe_id**: 저장된 레시피 UUID
    - **memo**: 새로운 메모 (null로 삭제 가능)
    """
    service = SavedRecipeService(db)
    return await service.update_saved_recipe(
        cookbook_id, saved_recipe_id, user_id, data
    )


@router.delete(
    "/cookbooks/{cookbook_id}/recipes/{saved_recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="저장된 레시피 삭제",
    description="저장된 레시피를 삭제합니다.",
    tags=["saved-recipes"],
    responses={
        204: {"description": "저장된 레시피 삭제됨"},
        401: {"description": "인증 필요"},
        404: {"description": "레시피북 또는 저장된 레시피를 찾을 수 없음"},
    },
)
async def delete_saved_recipe(
    cookbook_id: str,
    saved_recipe_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> None:
    """
    저장된 레시피 삭제 (User Story 5)

    - **cookbook_id**: 레시피북 UUID
    - **saved_recipe_id**: 저장된 레시피 UUID
    - 삭제 시 연관된 RecipeVariation도 함께 삭제됨 (CASCADE)
    """
    service = SavedRecipeService(db)
    await service.delete_saved_recipe(cookbook_id, saved_recipe_id, user_id)
