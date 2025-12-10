"""OAuth API endpoints for social login"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.api.deps import CurrentUser
from user_service.core.exceptions import UnsupportedOAuthProviderError
from user_service.core.oauth_providers import OAuthProviders
from user_service.db.session import get_db
from user_service.schemas.oauth import (
    OAuthAuthorizationResponse,
    OAuthCallbackRequest,
    OAuthLoginResponse,
    OAuthProviderEnum,
)
from user_service.services.oauth import OAuthService

router = APIRouter()


@router.get(
    "/{provider}",
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
    db: AsyncSession = Depends(get_db),
) -> OAuthAuthorizationResponse:
    """Generate OAuth authorization URL for social login

    - **provider**: OAuth provider (kakao, google, naver)

    Returns authorization URL with CSRF state token.
    Redirect user to this URL to start OAuth flow.
    """
    # Validate provider
    if not OAuthProviders.is_supported(provider):
        raise UnsupportedOAuthProviderError(provider=provider)

    provider_enum = OAuthProviderEnum(provider)
    oauth_service = OAuthService(db)
    return await oauth_service.generate_authorization_url(provider_enum)


@router.post(
    "/{provider}/callback",
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
    db: AsyncSession = Depends(get_db),
) -> OAuthLoginResponse:
    """Handle OAuth callback and issue JWT tokens

    - **provider**: OAuth provider (kakao, google, naver)
    - **code**: Authorization code from OAuth provider
    - **state**: CSRF state token (must match generated state)

    Returns JWT access/refresh tokens and user info.
    Creates new user if first-time login, or links to existing user by email.
    """
    # Validate provider
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
    "/{provider}/link",
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
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Link OAuth account to existing user

    - **provider**: OAuth provider (kakao, google, naver)
    - **code**: Authorization code from OAuth provider
    - **state**: CSRF state token (must match generated state)

    Requires authentication. Links the OAuth account to current user.
    """
    # Validate provider
    if not OAuthProviders.is_supported(provider):
        raise UnsupportedOAuthProviderError(provider=provider)

    provider_enum = OAuthProviderEnum(provider)
    oauth_service = OAuthService(db)
    oauth_account = await oauth_service.link_account(
        user_id=str(current_user.id),
        provider=provider_enum,
        code=request.code,
        state=request.state,
    )

    return {
        "message": f"{provider} 계정이 연동되었습니다.",
        "provider": provider,
        "linked_email": oauth_account.provider_email,
    }
