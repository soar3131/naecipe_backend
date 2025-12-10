"""Session service for Redis session management"""

from typing import Any

from user_service.core.config import settings
from user_service.db.redis import get_redis


class SessionService:
    """Service for session management using Redis"""

    # Key prefixes
    SESSION_PREFIX = "session:"
    BLACKLIST_PREFIX = "blacklist:"
    LOGIN_FAILURE_PREFIX = "login_failure:"

    @classmethod
    async def store_refresh_token(cls, user_id: str, refresh_token: str) -> None:
        """Store refresh token in Redis

        Args:
            user_id: User UUID
            refresh_token: Refresh token to store
        """
        redis = await get_redis()
        key = f"{cls.SESSION_PREFIX}{user_id}"
        expire_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        await redis.set(key, refresh_token, ex=expire_seconds)

    @classmethod
    async def get_refresh_token(cls, user_id: str) -> str | None:
        """Get stored refresh token for user

        Args:
            user_id: User UUID

        Returns:
            Stored refresh token or None
        """
        redis = await get_redis()
        key = f"{cls.SESSION_PREFIX}{user_id}"

        return await redis.get(key)

    @classmethod
    async def delete_session(cls, user_id: str) -> None:
        """Delete user session (logout)

        Args:
            user_id: User UUID
        """
        redis = await get_redis()
        key = f"{cls.SESSION_PREFIX}{user_id}"

        await redis.delete(key)

    @classmethod
    async def blacklist_token(cls, token_jti: str, expires_in: int) -> None:
        """Add access token to blacklist

        Args:
            token_jti: Token unique identifier (jti claim)
            expires_in: Time until token expiry in seconds
        """
        redis = await get_redis()
        key = f"{cls.BLACKLIST_PREFIX}{token_jti}"

        # Store with TTL matching token expiry
        await redis.set(key, "1", ex=expires_in)

    @classmethod
    async def is_token_blacklisted(cls, token_jti: str) -> bool:
        """Check if token is blacklisted

        Args:
            token_jti: Token unique identifier

        Returns:
            True if blacklisted, False otherwise
        """
        redis = await get_redis()
        key = f"{cls.BLACKLIST_PREFIX}{token_jti}"

        return await redis.exists(key) > 0

    @classmethod
    async def get_login_failure_count(cls, email: str) -> int:
        """Get login failure count for email

        Args:
            email: User email

        Returns:
            Number of failed login attempts
        """
        redis = await get_redis()
        key = f"{cls.LOGIN_FAILURE_PREFIX}{email.lower()}"

        count = await redis.get(key)
        return int(count) if count else 0

    @classmethod
    async def increment_login_failure(cls, email: str) -> int:
        """Increment login failure count

        Args:
            email: User email

        Returns:
            New failure count
        """
        redis = await get_redis()
        key = f"{cls.LOGIN_FAILURE_PREFIX}{email.lower()}"
        expire_seconds = settings.ACCOUNT_LOCK_MINUTES * 60

        # Increment and set expiry
        count = await redis.incr(key)
        await redis.expire(key, expire_seconds)

        return count

    @classmethod
    async def reset_login_failure(cls, email: str) -> None:
        """Reset login failure count

        Args:
            email: User email
        """
        redis = await get_redis()
        key = f"{cls.LOGIN_FAILURE_PREFIX}{email.lower()}"

        await redis.delete(key)
