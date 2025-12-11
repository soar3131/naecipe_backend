"""
Cookbooks 테스트 픽스처

레시피북 테스트용 공통 픽스처를 제공합니다.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cookbooks.models import Cookbook
from app.core.security import create_access_token
from app.users.models import User


@pytest.fixture
def user_id() -> str:
    """테스트용 사용자 ID"""
    return str(uuid4())


@pytest.fixture
def other_user_id() -> str:
    """다른 사용자 ID (권한 테스트용)"""
    return str(uuid4())


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, user_id: str) -> User:
    """테스트용 사용자"""
    user = User(
        id=user_id,
        email="test@example.com",
        nickname="테스트사용자",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession, other_user_id: str) -> User:
    """다른 사용자 (권한 테스트용)"""
    user = User(
        id=other_user_id,
        email="other@example.com",
        nickname="다른사용자",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def default_cookbook(
    db_session: AsyncSession, test_user: User, user_id: str
) -> Cookbook:
    """기본 레시피북"""
    cookbook = Cookbook(
        id=str(uuid4()),
        user_id=user_id,
        name="내 레시피북",
        is_default=True,
        sort_order=0,
    )
    db_session.add(cookbook)
    await db_session.flush()
    return cookbook


@pytest_asyncio.fixture
async def sample_cookbook(
    db_session: AsyncSession, test_user: User, user_id: str
) -> Cookbook:
    """샘플 레시피북 (기본 아님)"""
    cookbook = Cookbook(
        id=str(uuid4()),
        user_id=user_id,
        name="한식 모음",
        description="한식 레시피 모음집",
        cover_image_url="https://example.com/korean.jpg",
        is_default=False,
        sort_order=1,
    )
    db_session.add(cookbook)
    await db_session.flush()
    return cookbook


@pytest_asyncio.fixture
async def multiple_cookbooks(
    db_session: AsyncSession, test_user: User, user_id: str, default_cookbook: Cookbook
) -> list[Cookbook]:
    """여러 레시피북 (순서 테스트용)"""
    cookbooks = [default_cookbook]

    for i, name in enumerate(["한식 모음", "양식 모음", "중식 모음"], start=1):
        cookbook = Cookbook(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            is_default=False,
            sort_order=i,
        )
        db_session.add(cookbook)
        cookbooks.append(cookbook)

    await db_session.flush()
    return cookbooks


@pytest_asyncio.fixture
async def other_user_cookbook(
    db_session: AsyncSession, other_user: User, other_user_id: str
) -> Cookbook:
    """다른 사용자의 레시피북 (권한 테스트용)"""
    cookbook = Cookbook(
        id=str(uuid4()),
        user_id=other_user_id,
        name="다른 사용자 레시피북",
        is_default=True,
        sort_order=0,
    )
    db_session.add(cookbook)
    await db_session.flush()
    return cookbook


@pytest.fixture
def cookbook_create_data() -> dict:
    """레시피북 생성 요청 데이터"""
    return {
        "name": "새 레시피북",
        "description": "테스트용 레시피북입니다",
        "cover_image_url": "https://example.com/cover.jpg",
    }


@pytest.fixture
def cookbook_update_data() -> dict:
    """레시피북 수정 요청 데이터"""
    return {
        "name": "수정된 레시피북",
        "description": "수정된 설명입니다",
    }


@pytest.fixture
def auth_headers(user_id: str) -> dict[str, str]:
    """인증된 사용자 헤더"""
    token = create_access_token(subject=user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user_id: str) -> dict[str, str]:
    """다른 사용자 인증 헤더"""
    token = create_access_token(subject=other_user_id)
    return {"Authorization": f"Bearer {token}"}
