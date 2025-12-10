"""Authentication service for login and token management"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.core.config import settings
from user_service.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    InvalidTokenError,
    TokenRevokedError,
    UserNotFoundError,
)
from user_service.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_refresh_token,
)
from user_service.models.user import User, UserStatus
from user_service.schemas.auth import TokenResponse
from user_service.services.session import SessionService


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate user and issue tokens

        Args:
            email: User email
            password: User password

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            AccountLockedError: If account is locked
            AuthenticationError: If credentials are invalid
        """
        email = email.lower()

        # Check if account is locked (via Redis failure counter)
        failure_count = await SessionService.get_login_failure_count(email)
        if failure_count >= settings.LOGIN_FAILURE_LIMIT:
            raise AccountLockedError(
                locked_until=datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
            )

        # Get user
        user = await self._get_user_by_email(email)
        if not user:
            await self._handle_login_failure(email)
            raise AuthenticationError()

        # Check user status
        if user.status == UserStatus.LOCKED:
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                raise AccountLockedError(locked_until=user.locked_until)
            # Lock expired, reset status
            user.status = UserStatus.ACTIVE
            user.locked_until = None

        if user.status != UserStatus.ACTIVE:
            await self._handle_login_failure(email)
            raise AuthenticationError()

        # Verify password
        if not verify_password(password, user.password_hash):
            await self._handle_login_failure(email)
            raise AuthenticationError()

        # Reset failure counter on success
        await SessionService.reset_login_failure(email)

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Store refresh token in session
        await SessionService.store_refresh_token(str(user.id), refresh_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            TokenResponse with new access and refresh tokens

        Raises:
            InvalidTokenError: If refresh token is invalid
            TokenRevokedError: If refresh token is revoked
            UserNotFoundError: If user no longer exists
        """
        # Verify refresh token
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise InvalidTokenError()

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        # Verify session exists
        stored_token = await SessionService.get_refresh_token(user_id)
        if not stored_token or stored_token != refresh_token:
            raise TokenRevokedError()

        # Verify user exists
        user = await self._get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError()

        # Generate new tokens (token rotation)
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)

        # Update session with new refresh token
        await SessionService.store_refresh_token(user_id, new_refresh_token)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, user_id: str, token_jti: str, token_exp: int) -> None:
        """Logout user and invalidate tokens

        Args:
            user_id: User UUID
            token_jti: Access token JTI for blacklisting
            token_exp: Token expiry timestamp
        """
        # Delete session (invalidates refresh token)
        await SessionService.delete_session(user_id)

        # Blacklist current access token
        expires_in = max(0, token_exp - int(datetime.now(timezone.utc).timestamp()))
        if expires_in > 0:
            await SessionService.blacklist_token(token_jti, expires_in)

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

    async def _handle_login_failure(self, email: str) -> None:
        """Handle login failure - increment counter and lock if needed"""
        failure_count = await SessionService.increment_login_failure(email)

        # Lock account in database if threshold reached
        if failure_count >= settings.LOGIN_FAILURE_LIMIT:
            user = await self._get_user_by_email(email)
            if user:
                user.status = UserStatus.LOCKED
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.ACCOUNT_LOCK_MINUTES
                )
                await self.db.flush()
