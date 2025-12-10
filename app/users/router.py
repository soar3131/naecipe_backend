"""
Users 모듈 라우터

인증, 프로필, 취향 설정, OAuth 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUserId, DbSession
from app.core.exceptions import UnsupportedOAuthProviderError
from app.core.security import decode_token
from app.users.models import User
from app.users.oauth_providers import OAuthProviders
from app.users.schemas import (
    ALLERGY_LABELS,
    CUISINE_CATEGORY_LABELS,
    DIETARY_RESTRICTION_LABELS,
    Allergy,
    CuisineCategory,
    DietaryRestriction,
    LoginRequest,
    OAuthAuthorizationResponse,
    OAuthCallbackRequest,
    OAuthLoginResponse,
    OAuthProviderEnum,
    OptionItem,
    OptionsResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.users.services import (
    AuthService,
    OAuthService,
    PreferenceService,
    ProfileService,
    UserService,
)

router = APIRouter()
security = HTTPBearer()


# ==========================================================================
# 인증 엔드포인트 (Auth)
# ==========================================================================


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="사용자 회원가입",
    description="이메일과 비밀번호로 새 사용자 계정을 생성합니다.",
    responses={
        201: {"description": "회원가입 성공"},
        409: {"description": "이미 존재하는 이메일"},
        422: {"description": "유효하지 않은 요청"},
    },
)
async def register(
    request: RegisterRequest,
    db: DbSession,
) -> RegisterResponse:
    """이메일/비밀번호로 새 사용자 생성"""
    user_service = UserService(db)
    return await user_service.create_user(request)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="사용자 로그인",
    description="이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.",
    responses={
        200: {"description": "로그인 성공"},
        401: {"description": "인증 실패"},
        423: {"description": "계정 잠금"},
    },
)
async def login(
    request: LoginRequest,
    db: DbSession,
) -> TokenResponse:
    """이메일/비밀번호 로그인"""
    auth_service = AuthService(db)
    return await auth_service.login(request.email, request.password)


@router.get(
    "/auth/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="현재 사용자 정보",
    description="현재 로그인한 사용자의 정보를 조회합니다.",
    responses={
        200: {"description": "조회 성공"},
        401: {"description": "인증 필요"},
    },
)
async def get_me(
    current_user_id: CurrentUserId,
    db: DbSession,
) -> UserResponse:
    """현재 사용자 정보 조회"""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        status=user.status.value,
        created_at=user.created_at,
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="토큰 갱신",
    description="Refresh Token으로 새로운 Access Token을 발급받습니다.",
    responses={
        200: {"description": "갱신 성공"},
        401: {"description": "유효하지 않은 토큰"},
    },
)
async def refresh(
    request: RefreshRequest,
    db: DbSession,
) -> TokenResponse:
    """토큰 갱신"""
    auth_service = AuthService(db)
    return await auth_service.refresh_token(request.refresh_token)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="현재 세션을 종료하고 토큰을 무효화합니다.",
    responses={
        204: {"description": "로그아웃 성공"},
        401: {"description": "인증 필요"},
    },
)
async def logout(
    current_user_id: CurrentUserId,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DbSession = None,
) -> Response:
    """로그아웃 및 토큰 무효화"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload:
        auth_service = AuthService(db)
        await auth_service.logout(
            user_id=current_user_id,
            token_jti=payload.get("jti", ""),
            token_exp=payload.get("exp", 0),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================================================
# OAuth 엔드포인트
# ==========================================================================


@router.get(
    "/oauth/{provider}",
    response_model=OAuthAuthorizationResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth 인증 URL 생성",
    description="소셜 로그인을 위한 OAuth 인증 URL을 생성합니다.",
    responses={
        200: {"description": "인증 URL 생성 성공"},
        400: {"description": "지원하지 않는 OAuth 제공자"},
    },
)
async def get_authorization_url(
    provider: str,
    db: DbSession,
) -> OAuthAuthorizationResponse:
    """OAuth 인증 URL 생성"""
    if not OAuthProviders.is_supported(provider):
        raise UnsupportedOAuthProviderError(provider=provider)

    provider_enum = OAuthProviderEnum(provider)
    oauth_service = OAuthService(db)
    return await oauth_service.generate_authorization_url(provider_enum)


@router.post(
    "/oauth/{provider}/callback",
    response_model=OAuthLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth 콜백 처리",
    description="OAuth 인증 완료 후 콜백을 처리하여 JWT 토큰을 발급합니다.",
    responses={
        200: {"description": "로그인 성공"},
        400: {"description": "유효하지 않은 state 또는 지원하지 않는 제공자"},
        502: {"description": "OAuth 제공자 오류"},
    },
)
async def oauth_callback(
    provider: str,
    request: OAuthCallbackRequest,
    db: DbSession,
) -> OAuthLoginResponse:
    """OAuth 콜백 처리 및 JWT 발급"""
    if not OAuthProviders.is_supported(provider):
        raise UnsupportedOAuthProviderError(provider=provider)

    provider_enum = OAuthProviderEnum(provider)
    oauth_service = OAuthService(db)
    return await oauth_service.handle_callback(
        provider=provider_enum,
        code=request.code,
        state=request.state,
    )


@router.post(
    "/oauth/{provider}/link",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="OAuth 계정 연동",
    description="기존 사용자 계정에 소셜 로그인 계정을 연동합니다.",
    responses={
        200: {"description": "계정 연동 성공"},
        400: {"description": "유효하지 않은 state 또는 지원하지 않는 제공자"},
        401: {"description": "인증 필요"},
        409: {"description": "이미 다른 사용자에게 연동된 계정"},
        502: {"description": "OAuth 제공자 오류"},
    },
)
async def link_oauth_account(
    provider: str,
    request: OAuthCallbackRequest,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """OAuth 계정 연동"""
    if not OAuthProviders.is_supported(provider):
        raise UnsupportedOAuthProviderError(provider=provider)

    provider_enum = OAuthProviderEnum(provider)
    oauth_service = OAuthService(db)
    oauth_account = await oauth_service.link_account(
        user_id=current_user_id,
        provider=provider_enum,
        code=request.code,
        state=request.state,
    )

    return {
        "message": f"{provider} 계정이 연동되었습니다.",
        "provider": provider,
        "linked_email": oauth_account.provider_email,
    }


# ==========================================================================
# 프로필 엔드포인트
# ==========================================================================


@router.get(
    "/users/me",
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
    current_user_id: CurrentUserId,
    db: DbSession,
) -> ProfileResponse:
    """내 프로필 조회"""
    profile_service = ProfileService(db)
    profile_data = await profile_service.get_profile(current_user_id)

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로필을 찾을 수 없습니다.",
        )

    return ProfileResponse(success=True, data=profile_data)


@router.put(
    "/users/me",
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
    current_user_id: CurrentUserId,
    db: DbSession,
) -> ProfileResponse:
    """내 프로필 수정"""
    profile_service = ProfileService(db)
    profile_data = await profile_service.update_profile(current_user_id, data)

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로필을 찾을 수 없습니다.",
        )

    return ProfileResponse(success=True, data=profile_data)


# ==========================================================================
# 취향 설정 엔드포인트
# ==========================================================================


@router.get(
    "/users/me/preferences",
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
    current_user_id: CurrentUserId,
    db: DbSession,
) -> PreferencesResponse:
    """내 취향 설정 조회"""
    profile_service = ProfileService(db)
    await profile_service.ensure_profile_exists(current_user_id)

    preference_service = PreferenceService(db)
    preferences_data = await preference_service.get_preferences(current_user_id)

    if not preferences_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="취향 설정을 찾을 수 없습니다.",
        )

    return PreferencesResponse(success=True, data=preferences_data)


@router.put(
    "/users/me/preferences",
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
    current_user_id: CurrentUserId,
    db: DbSession,
) -> PreferencesResponse:
    """내 취향 설정 수정"""
    profile_service = ProfileService(db)
    await profile_service.ensure_profile_exists(current_user_id)

    preference_service = PreferenceService(db)
    preferences_data = await preference_service.update_preferences(current_user_id, data)

    if not preferences_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="취향 설정을 찾을 수 없습니다.",
        )

    return PreferencesResponse(success=True, data=preferences_data)


# ==========================================================================
# 옵션 조회 엔드포인트
# ==========================================================================


@router.get(
    "/users/me/preferences/dietary-options",
    response_model=OptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="식이 제한 옵션 목록",
    description="설정 가능한 식이 제한 옵션 목록을 조회합니다.",
)
async def get_dietary_options() -> OptionsResponse:
    """식이 제한 옵션 목록 조회"""
    options = [
        OptionItem(value=d.value, label=DIETARY_RESTRICTION_LABELS[d])
        for d in DietaryRestriction
    ]
    return OptionsResponse(success=True, data=options)


@router.get(
    "/users/me/preferences/allergy-options",
    response_model=OptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="알레르기 옵션 목록",
    description="설정 가능한 알레르기 옵션 목록을 조회합니다.",
)
async def get_allergy_options() -> OptionsResponse:
    """알레르기 옵션 목록 조회"""
    options = [
        OptionItem(value=a.value, label=ALLERGY_LABELS[a])
        for a in Allergy
    ]
    return OptionsResponse(success=True, data=options)


@router.get(
    "/users/me/preferences/cuisine-options",
    response_model=OptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="요리 카테고리 옵션 목록",
    description="설정 가능한 요리 카테고리 옵션 목록을 조회합니다.",
)
async def get_cuisine_options() -> OptionsResponse:
    """요리 카테고리 옵션 목록 조회"""
    options = [
        OptionItem(value=c.value, label=CUISINE_CATEGORY_LABELS[c])
        for c in CuisineCategory
    ]
    return OptionsResponse(success=True, data=options)
