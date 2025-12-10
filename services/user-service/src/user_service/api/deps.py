"""API dependencies for authentication and authorization"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.core.exceptions import InvalidTokenError, TokenRevokedError
from user_service.core.security import verify_access_token
from user_service.db.redis import RedisClient, get_redis
from user_service.db.session import get_db
from user_service.models.user import User

security = HTTPBearer()


async def get_redis_client() -> RedisClient:
    """Get Redis client dependency"""
    redis = await get_redis()
    return RedisClient(redis)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
) -> User:
    """Get current authenticated user from token"""
    token = credentials.credentials

    # Verify token
    payload = verify_access_token(token)
    if payload is None:
        raise InvalidTokenError(instance=str(request.url.path))

    user_id: str = payload.get("sub", "")
    if not user_id:
        raise InvalidTokenError(instance=str(request.url.path))

    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti:
        is_blacklisted = await redis.exists(f"blacklist:{jti}")
        if is_blacklisted:
            raise TokenRevokedError(instance=str(request.url.path))

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise InvalidTokenError(
            detail="사용자를 찾을 수 없습니다.",
            instance=str(request.url.path),
        )

    if not user.is_active:
        raise InvalidTokenError(
            detail="비활성화된 계정입니다.",
            instance=str(request.url.path),
        )

    return user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
Redis = Annotated[RedisClient, Depends(get_redis_client)]
