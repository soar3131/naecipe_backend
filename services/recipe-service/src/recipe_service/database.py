"""
데이터베이스 연결 및 세션 관리

SQLAlchemy async 엔진과 세션을 설정합니다.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recipe_service.core.config import settings


def create_engine() -> AsyncEngine:
    """비동기 데이터베이스 엔진 생성"""
    return create_async_engine(
        settings.database.async_url,
        echo=settings.DEBUG,
        pool_size=settings.database.DATABASE_POOL_SIZE,
        max_overflow=settings.database.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # 연결 유효성 검사
    )


# 전역 엔진 인스턴스
engine = create_engine()

# 세션 팩토리
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 주입용 세션 생성기"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """컨텍스트 매니저 방식의 세션 생성"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """데이터베이스 초기화 (개발용, Alembic 마이그레이션 권장)"""
    from recipe_service.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """데이터베이스 연결 종료"""
    await engine.dispose()
