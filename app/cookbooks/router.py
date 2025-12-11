"""
Cookbooks 모듈 라우터

레시피북 CRUD 엔드포인트를 정의합니다.
"""

import logging

from fastapi import APIRouter, status

from app.cookbooks.exceptions import (
    CannotDeleteDefaultCookbookError,
    CookbookNotFoundError,
)
from app.cookbooks.schemas import (
    CookbookCreateRequest,
    CookbookListResponse,
    CookbookReorderRequest,
    CookbookResponse,
    CookbookUpdateRequest,
)
from app.cookbooks.services import CookbookService
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
