"""
Recipe Service 테스트 설정

pytest fixtures와 공통 테스트 유틸리티를 정의합니다.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from recipe_service.core.config import settings
from recipe_service.main import app
from recipe_service.models.base import Base


# 테스트용 데이터베이스 URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 고정"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """테스트용 데이터베이스 엔진"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # SQLite에서 외래 키 제약 조건 활성화
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    async_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """비동기 테스트 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def anyio_backend() -> str:
    """pytest-asyncio 백엔드 설정"""
    return "asyncio"


# 테스트 데이터 팩토리
@pytest.fixture
def sample_chef_data() -> dict[str, Any]:
    """샘플 요리사 데이터"""
    return {
        "id": str(uuid4()),
        "name": "백종원",
        "name_normalized": "백종원",
        "profile_image_url": "https://example.com/chef1.jpg",
        "bio": "요리 연구가, 외식 사업가",
        "specialty": "한식",
        "recipe_count": 150,
        "total_views": 10000000,
        "avg_rating": 4.8,
        "is_verified": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_recipe_data(sample_chef_data: dict[str, Any]) -> dict[str, Any]:
    """샘플 레시피 데이터"""
    return {
        "id": str(uuid4()),
        "chef_id": sample_chef_data["id"],
        "title": "김치찌개",
        "description": "맛있는 김치찌개 레시피",
        "thumbnail_url": "https://example.com/kimchi.jpg",
        "video_url": "https://youtube.com/watch?v=abc123",
        "prep_time_minutes": 10,
        "cook_time_minutes": 30,
        "servings": 4,
        "difficulty": "easy",
        "source_url": "https://youtube.com/watch?v=abc123",
        "source_platform": "youtube",
        "exposure_score": 85.5,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_ingredient_data(sample_recipe_data: dict[str, Any]) -> list[dict[str, Any]]:
    """샘플 재료 데이터"""
    return [
        {
            "id": str(uuid4()),
            "recipe_id": sample_recipe_data["id"],
            "name": "김치",
            "amount": "300",
            "unit": "g",
            "order_index": 0,
        },
        {
            "id": str(uuid4()),
            "recipe_id": sample_recipe_data["id"],
            "name": "돼지고기",
            "amount": "200",
            "unit": "g",
            "order_index": 1,
        },
        {
            "id": str(uuid4()),
            "recipe_id": sample_recipe_data["id"],
            "name": "두부",
            "amount": "1",
            "unit": "모",
            "order_index": 2,
        },
    ]


@pytest.fixture
def sample_step_data(sample_recipe_data: dict[str, Any]) -> list[dict[str, Any]]:
    """샘플 조리 단계 데이터"""
    return [
        {
            "id": str(uuid4()),
            "recipe_id": sample_recipe_data["id"],
            "step_number": 1,
            "description": "돼지고기를 한입 크기로 썰어 준비합니다.",
            "image_url": None,
            "duration_seconds": 300,
        },
        {
            "id": str(uuid4()),
            "recipe_id": sample_recipe_data["id"],
            "step_number": 2,
            "description": "냄비에 기름을 두르고 돼지고기를 볶습니다.",
            "image_url": None,
            "duration_seconds": 600,
        },
        {
            "id": str(uuid4()),
            "recipe_id": sample_recipe_data["id"],
            "step_number": 3,
            "description": "김치를 넣고 함께 볶아줍니다.",
            "image_url": None,
            "duration_seconds": 300,
        },
    ]


@pytest.fixture
def sample_tag_data() -> list[dict[str, Any]]:
    """샘플 태그 데이터"""
    return [
        {"id": str(uuid4()), "name": "한식", "category": "cuisine"},
        {"id": str(uuid4()), "name": "찌개", "category": "dish_type"},
        {"id": str(uuid4()), "name": "저녁", "category": "meal_type"},
    ]
