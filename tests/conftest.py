"""
테스트 공통 설정 및 픽스처

pytest-asyncio 기반 비동기 테스트 환경을 제공합니다.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.infra.database import Base, get_db_session
from app.main import app


# ==========================================================================
# 이벤트 루프 설정
# ==========================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """세션 범위 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==========================================================================
# 데이터베이스 설정
# ==========================================================================


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """테스트용 데이터베이스 엔진"""
    # 테스트용 DB URL (별도 테스트 DB 사용 권장)
    test_db_url = settings.database_url.replace(
        "/naecipe", "/naecipe_test"
    ) if "/naecipe" in settings.database_url else settings.database_url + "_test"

    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 테이블 삭제
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        # 각 테스트 후 롤백
        await session.rollback()


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
