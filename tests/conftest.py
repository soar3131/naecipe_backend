"""
테스트 공통 설정 및 픽스처

pytest-asyncio 기반 비동기 테스트 환경을 제공합니다.
"""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.infra.database import Base, get_db_session
from app.main import app


# ==========================================================================
# 데이터베이스 설정
# ==========================================================================


def get_test_db_url() -> str:
    """테스트용 DB URL 생성"""
    base_url = settings.database_url
    if base_url.endswith(f"/{settings.DATABASE_NAME}"):
        return base_url[: -len(settings.DATABASE_NAME)] + f"{settings.DATABASE_NAME}_test"
    else:
        return base_url + "_test"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션 (각 테스트마다 독립 엔진)"""
    test_db_url = get_test_db_url()

    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    # 테이블 삭제 및 정리
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """테스트용 HTTP 클라이언트"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ==========================================================================
# 공통 유틸리티 픽스처
# ==========================================================================


@pytest.fixture
def uuid_factory():
    """UUID 생성 팩토리"""

    def _factory() -> str:
        return str(uuid4())

    return _factory
