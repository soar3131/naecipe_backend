"""
Recipe Service 테스트 설정

pytest fixtures와 공통 테스트 유틸리티를 정의합니다.
"""

from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from recipe_service.main import app


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
