"""OAuth service for social login authentication"""

import secrets
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.core.config import settings
from user_service.core.exceptions import (
    OAuthAccountAlreadyLinkedError,
    OAuthProviderError,
    OAuthStateError,
)
from user_service.core.oauth_providers import OAuthProviders, parse_user_info
from user_service.core.security import create_access_token, create_refresh_token
from user_service.db.redis import get_redis
from user_service.models.oauth_account import OAuthAccount
from user_service.models.user import User, UserStatus
from user_service.schemas.oauth import (
    OAuthAuthorizationResponse,
    OAuthLoginResponse,
    OAuthProviderEnum,
    OAuthUserData,
    OAuthUserInfo,
)
from user_service.services.session import SessionService


class OAuthService:
    """Service for OAuth authentication operations"""

    # Redis key prefix for OAuth state
    OAUTH_STATE_PREFIX = "oauth_state:"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_authorization_url(
        self, provider: OAuthProviderEnum
    ) -> OAuthAuthorizationResponse:
        """Generate OAuth authorization URL with state for CSRF protection

        Args:
            provider: OAuth provider (kakao, google, naver)

        Returns:
            OAuthAuthorizationResponse with authorization URL and state
        """
        config = OAuthProviders.get(provider)

        # Generate random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in Redis with TTL
        redis = await get_redis()
        state_key = f"{self.OAUTH_STATE_PREFIX}{state}"
        await redis.set(
            state_key,
            provider.value,
            ex=settings.OAUTH_STATE_EXPIRE_SECONDS,
        )

        # Build authorization URL
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "state": state,
        }

        # Add scopes if present
        if config.scopes:
            params["scope"] = " ".join(config.scopes)

        # Naver uses different param name for redirect_uri
        if provider == OAuthProviderEnum.NAVER:
            params["redirect_uri"] = config.redirect_uri

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{config.authorization_url}?{query_string}"

        return OAuthAuthorizationResponse(
            authorization_url=authorization_url,
            state=state,
        )

    async def handle_callback(
        self, provider: OAuthProviderEnum, code: str, state: str
    ) -> OAuthLoginResponse:
        """Handle OAuth callback: validate state, exchange code, find/create user

        Args:
            provider: OAuth provider
            code: Authorization code from provider
            state: State token for CSRF validation

        Returns:
            OAuthLoginResponse with JWT tokens and user info

        Raises:
            OAuthStateError: If state is invalid or expired
            OAuthProviderError: If provider API call fails
        """
        # Validate state
        await self._validate_state(state, provider)

        # Exchange authorization code for access token
        oauth_token = await self._exchange_code_for_token(provider, code)

        # Get user info from provider
        oauth_user_data = await self._get_user_info(provider, oauth_token)

        # Find or create user
        user, oauth_account, is_new_user = await self._find_or_create_user(oauth_user_data)

        # Generate JWT tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id), jti=str(uuid4()))

        # Store refresh token in session
        await SessionService.store_refresh_token(str(user.id), refresh_token)

        return OAuthLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=OAuthUserInfo(
                id=str(user.id),
                email=user.email,
                provider=provider,
                created_at=user.created_at,
            ),
            is_new_user=is_new_user,
        )

    async def link_account(
        self, user_id: str, provider: OAuthProviderEnum, code: str, state: str
    ) -> OAuthAccount:
        """Link OAuth account to existing user

        Args:
            user_id: User ID to link account to
            provider: OAuth provider
            code: Authorization code from provider
            state: State token for CSRF validation

        Returns:
            Created OAuthAccount

        Raises:
            OAuthAccountAlreadyLinkedError: If OAuth account is already linked
        """
        # Validate state
        await self._validate_state(state, provider)

        # Exchange code for token
        oauth_token = await self._exchange_code_for_token(provider, code)

        # Get user info from provider
        oauth_user_data = await self._get_user_info(provider, oauth_token)

        # Check if OAuth account already exists
        existing_oauth = await self._get_oauth_account_by_provider_user_id(
            provider, oauth_user_data.provider_user_id
        )
        if existing_oauth:
            raise OAuthAccountAlreadyLinkedError(provider=provider.value)

        # Create new OAuth account link
        oauth_account = OAuthAccount(
            id=str(uuid4()),
            user_id=user_id,
            provider=provider.value,
            provider_user_id=oauth_user_data.provider_user_id,
            provider_email=oauth_user_data.email,
        )
        self.db.add(oauth_account)
        await self.db.flush()

        return oauth_account

    async def _validate_state(self, state: str, expected_provider: OAuthProviderEnum) -> None:
        """Validate OAuth state from Redis

        Args:
            state: State token to validate
            expected_provider: Expected provider from request

        Raises:
            OAuthStateError: If state is invalid, expired, or provider mismatch
        """
        redis = await get_redis()
        state_key = f"{self.OAUTH_STATE_PREFIX}{state}"

        # Get and delete state (one-time use)
        stored_provider = await redis.get(state_key)
        if not stored_provider:
            raise OAuthStateError()

        # Delete state after retrieval
        await redis.delete(state_key)

        # Verify provider matches
        if stored_provider != expected_provider.value:
            raise OAuthStateError()

    async def _exchange_code_for_token(
        self, provider: OAuthProviderEnum, code: str
    ) -> str:
        """Exchange authorization code for access token

        Args:
            provider: OAuth provider
            code: Authorization code

        Returns:
            Access token from provider

        Raises:
            OAuthProviderError: If token exchange fails
        """
        config = OAuthProviders.get(provider)

        data = {
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )
                response.raise_for_status()

                token_data = response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise OAuthProviderError(
                        provider=provider.value,
                        detail="액세스 토큰을 받지 못했습니다.",
                    )

                return access_token

            except httpx.HTTPStatusError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"토큰 교환 실패: {e.response.status_code}",
                )
            except httpx.RequestError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"네트워크 오류: {str(e)}",
                )

    async def _get_user_info(
        self, provider: OAuthProviderEnum, access_token: str
    ) -> OAuthUserData:
        """Get user info from OAuth provider

        Args:
            provider: OAuth provider
            access_token: Provider access token

        Returns:
            Parsed and normalized user data

        Raises:
            OAuthProviderError: If API call fails
        """
        config = OAuthProviders.get(provider)

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    config.user_info_url,
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()

                raw_data = response.json()
                parsed_data = parse_user_info(provider, raw_data)

                return OAuthUserData(
                    provider=provider,
                    provider_user_id=parsed_data["provider_user_id"],
                    email=parsed_data.get("email", ""),
                    name=parsed_data.get("name"),
                    profile_image=parsed_data.get("profile_image"),
                )

            except httpx.HTTPStatusError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"사용자 정보 조회 실패: {e.response.status_code}",
                )
            except httpx.RequestError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"네트워크 오류: {str(e)}",
                )

    async def _find_or_create_user(
        self, oauth_data: OAuthUserData
    ) -> tuple[User, OAuthAccount, bool]:
        """Find existing user or create new one from OAuth data

        Logic:
        1. Check if OAuth account already exists -> return linked user
        2. Check if user with same email exists -> link OAuth account
        3. Create new user and OAuth account

        Args:
            oauth_data: Normalized user data from OAuth provider

        Returns:
            Tuple of (User, OAuthAccount, is_new_user)
        """
        is_new_user = False

        # 1. Check if OAuth account already exists
        oauth_account = await self._get_oauth_account_by_provider_user_id(
            oauth_data.provider, oauth_data.provider_user_id
        )
        if oauth_account:
            user = await self._get_user_by_id(oauth_account.user_id)
            return user, oauth_account, is_new_user

        # 2. Check if user with same email exists (email-based linking)
        user = None
        if oauth_data.email:
            user = await self._get_user_by_email(oauth_data.email)

        # 3. Create new user if not found
        if not user:
            user = User(
                id=str(uuid4()),
                email=oauth_data.email or f"{oauth_data.provider_user_id}@{oauth_data.provider.value}.oauth",
                password_hash=None,  # Social-only user
                status=UserStatus.ACTIVE,
            )
            self.db.add(user)
            await self.db.flush()
            is_new_user = True

        # Create OAuth account link
        oauth_account = OAuthAccount(
            id=str(uuid4()),
            user_id=str(user.id),
            provider=oauth_data.provider.value,
            provider_user_id=oauth_data.provider_user_id,
            provider_email=oauth_data.email,
        )
        self.db.add(oauth_account)
        await self.db.flush()

        return user, oauth_account, is_new_user

    async def _get_oauth_account_by_provider_user_id(
        self, provider: OAuthProviderEnum, provider_user_id: str
    ) -> OAuthAccount | None:
        """Get OAuth account by provider and provider user ID"""
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider.value,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_user_by_email(self, email: str) -> User | None:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
