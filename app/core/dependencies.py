"""
FastAPI 의존성 주입

데이터베이스 세션, Redis 클라이언트, 현재 사용자 등의 의존성을 제공합니다.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError
from app.core.security import verify_access_token
from app.infra.database import get_db_session
from app.infra.redis import RedisClient, get_redis_client


# ==========================================================================
# 데이터베이스 의존성
# ==========================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """데이터베이스 세션 의존성"""
    async for session in get_db_session():
        yield session


# 타입 어노테이션
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ==========================================================================
# Redis 의존성
# ==========================================================================


async def get_redis() -> RedisClient:
    """Redis 클라이언트 의존성"""
    return await get_redis_client()


# 타입 어노테이션
Redis = Annotated[RedisClient, Depends(get_redis)]


# ==========================================================================
# 인증 의존성
# ==========================================================================


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """현재 인증된 사용자 ID 반환"""
    if not authorization:
        raise InvalidTokenError("인증 토큰이 필요합니다.")

    # Bearer 토큰 추출
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidTokenError("올바른 Bearer 토큰 형식이 아닙니다.")

    # 토큰 검증
    payload = verify_access_token(token)
    if payload is None:
        raise InvalidTokenError()

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("토큰에 사용자 정보가 없습니다.")

    return user_id


async def get_optional_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """선택적 인증 - 토큰이 있으면 사용자 ID 반환, 없으면 None"""
    if not authorization:
        return None

    try:
        return await get_current_user_id(authorization)
    except InvalidTokenError:
        return None


# 타입 어노테이션
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
OptionalUserId = Annotated[str | None, Depends(get_optional_user_id)]
