"""
사용자 프로필 및 취향 설정 API 엔드포인트
SPEC-003: 사용자 프로필 및 취향 설정
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.api.deps import CurrentUser, DBSession
from user_service.db.session import get_db
from user_service.schemas.enums import (
    ALLERGY_LABELS,
    CUISINE_CATEGORY_LABELS,
    DIETARY_RESTRICTION_LABELS,
    Allergy,
    CuisineCategory,
    DietaryRestriction,
)
from user_service.schemas.preference import (
    OptionItem,
    OptionsResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
)
from user_service.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
)
from user_service.services.preference import PreferenceService
from user_service.services.profile import ProfileService

router = APIRouter()


# ============================================================
# User Story 1: 프로필 조회 (P1 MVP)
# ============================================================

@router.get(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="내 프로필 조회",
    description="현재 로그인한 사용자의 프로필 정보를 조회합니다.",
    responses={
        200: {"description": "프로필 조회 성공"},
        401: {"description": "인증 필요"},
        404: {"description": "사용자를 찾을 수 없음"},
    },
)
async def get_my_profile(
    current_user: CurrentUser,
    db: DBSession,
) -> ProfileResponse:
    """현재 사용자의 프로필 조회

    Requires valid access token in Authorization header.
    """
    profile_service = ProfileService(db)
    profile_data = await profile_service.get_profile(str(current_user.id))

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로필을 찾을 수 없습니다.",
        )

    return ProfileResponse(success=True, data=profile_data)


# ============================================================
# User Story 2: 프로필 수정 (P1 MVP)
# ============================================================

@router.put(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="내 프로필 수정",
    description="현재 로그인한 사용자의 프로필 정보를 수정합니다.",
    responses={
        200: {"description": "프로필 수정 성공"},
        401: {"description": "인증 필요"},
        404: {"description": "사용자를 찾을 수 없음"},
        422: {"description": "유효하지 않은 요청"},
    },
)
async def update_my_profile(
    data: ProfileUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ProfileResponse:
    """현재 사용자의 프로필 수정

    - **displayName**: 표시 이름 (1-50자)
    - **profileImageUrl**: 프로필 이미지 URL (http/https)

    제공된 필드만 업데이트됩니다 (partial update).
    """
    profile_service = ProfileService(db)
    profile_data = await profile_service.update_profile(
        str(current_user.id),
        data,
    )

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로필을 찾을 수 없습니다.",
        )

    return ProfileResponse(success=True, data=profile_data)


# ============================================================
# User Story 3: 식이 제한 및 알레르기 설정 (P1 MVP)
# ============================================================

@router.get(
    "/me/preferences",
    response_model=PreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="내 취향 설정 조회",
    description="현재 로그인한 사용자의 취향 설정을 조회합니다.",
    responses={
        200: {"description": "취향 설정 조회 성공"},
        401: {"description": "인증 필요"},
        404: {"description": "사용자를 찾을 수 없음"},
    },
)
async def get_my_preferences(
    current_user: CurrentUser,
    db: DBSession,
) -> PreferencesResponse:
    """현재 사용자의 취향 설정 조회

    식이 제한, 알레르기, 선호 요리 카테고리, 맛 취향 등을 조회합니다.
    """
    preference_service = PreferenceService(db)

    # Profile 존재 보장
    profile_service = ProfileService(db)
    await profile_service.ensure_profile_exists(str(current_user.id))

    preferences_data = await preference_service.get_preferences(str(current_user.id))

    if not preferences_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="취향 설정을 찾을 수 없습니다.",
        )

    return PreferencesResponse(success=True, data=preferences_data)


@router.put(
    "/me/preferences",
    response_model=PreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="내 취향 설정 수정",
    description="현재 로그인한 사용자의 취향 설정을 수정합니다.",
    responses={
        200: {"description": "취향 설정 수정 성공"},
        401: {"description": "인증 필요"},
        404: {"description": "사용자를 찾을 수 없음"},
        422: {"description": "유효하지 않은 요청"},
    },
)
async def update_my_preferences(
    data: PreferencesUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> PreferencesResponse:
    """현재 사용자의 취향 설정 수정

    - **dietaryRestrictions**: 식이 제한 목록
    - **allergies**: 알레르기 목록
    - **cuisinePreferences**: 선호 요리 카테고리 (최대 10개)
    - **skillLevel**: 요리 실력 (1-5)
    - **householdSize**: 가구 인원 (1-20)
    - **tastePreferences**: 맛 취향 (overall 또는 카테고리별)

    제공된 필드만 업데이트됩니다 (partial update).
    """
    preference_service = PreferenceService(db)

    # Profile 존재 보장
    profile_service = ProfileService(db)
    await profile_service.ensure_profile_exists(str(current_user.id))

    preferences_data = await preference_service.update_preferences(
        str(current_user.id),
        data,
    )

    if not preferences_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="취향 설정을 찾을 수 없습니다.",
        )

    return PreferencesResponse(success=True, data=preferences_data)


# ============================================================
# 옵션 조회 엔드포인트 (식이제한, 알레르기, 요리카테고리)
# ============================================================

@router.get(
    "/me/preferences/dietary-options",
    response_model=OptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="식이 제한 옵션 목록",
    description="설정 가능한 식이 제한 옵션 목록을 조회합니다.",
    responses={
        200: {"description": "옵션 목록 조회 성공"},
    },
)
async def get_dietary_options() -> OptionsResponse:
    """식이 제한 옵션 목록 조회

    프론트엔드에서 드롭다운/체크박스 등에 사용할 수 있는 옵션 목록입니다.
    """
    options = [
        OptionItem(value=d.value, label=DIETARY_RESTRICTION_LABELS[d])
        for d in DietaryRestriction
    ]
    return OptionsResponse(success=True, data=options)


@router.get(
    "/me/preferences/allergy-options",
    response_model=OptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="알레르기 옵션 목록",
    description="설정 가능한 알레르기 옵션 목록을 조회합니다.",
    responses={
        200: {"description": "옵션 목록 조회 성공"},
    },
)
async def get_allergy_options() -> OptionsResponse:
    """알레르기 옵션 목록 조회

    프론트엔드에서 드롭다운/체크박스 등에 사용할 수 있는 옵션 목록입니다.
    """
    options = [
        OptionItem(value=a.value, label=ALLERGY_LABELS[a])
        for a in Allergy
    ]
    return OptionsResponse(success=True, data=options)


@router.get(
    "/me/preferences/cuisine-options",
    response_model=OptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="요리 카테고리 옵션 목록",
    description="설정 가능한 요리 카테고리 옵션 목록을 조회합니다.",
    responses={
        200: {"description": "옵션 목록 조회 성공"},
    },
)
async def get_cuisine_options() -> OptionsResponse:
    """요리 카테고리 옵션 목록 조회

    프론트엔드에서 드롭다운/체크박스 등에 사용할 수 있는 옵션 목록입니다.
    """
    options = [
        OptionItem(value=c.value, label=CUISINE_CATEGORY_LABELS[c])
        for c in CuisineCategory
    ]
    return OptionsResponse(success=True, data=options)
