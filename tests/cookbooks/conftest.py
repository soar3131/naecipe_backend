"""
Cookbooks 테스트 픽스처

레시피북 및 저장된 레시피 테스트용 공통 픽스처를 제공합니다.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cookbooks.models import Cookbook, SavedRecipe
from app.core.security import create_access_token
from app.recipes.models import Chef, Recipe
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


# ==========================================================================
# SavedRecipe 테스트 픽스처 (SPEC-008)
# ==========================================================================


@pytest_asyncio.fixture
async def sample_chef(db_session: AsyncSession) -> Chef:
    """샘플 요리사"""
    chef = Chef(
        id=str(uuid4()),
        name="백종원",
        name_normalized="백종원",
        specialty="한식",
    )
    db_session.add(chef)
    await db_session.flush()
    return chef


@pytest_asyncio.fixture
async def sample_recipe(db_session: AsyncSession, sample_chef: Chef) -> Recipe:
    """샘플 레시피"""
    recipe = Recipe(
        id=str(uuid4()),
        chef_id=sample_chef.id,
        title="백종원 김치찌개",
        description="집에서 간단하게 만드는 김치찌개",
        thumbnail_url="https://example.com/kimchi.jpg",
        video_url="https://youtube.com/watch?v=xxx",
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=2,
        difficulty="easy",
        source_platform="youtube",
    )
    db_session.add(recipe)
    await db_session.flush()
    return recipe


@pytest_asyncio.fixture
async def another_recipe(db_session: AsyncSession, sample_chef: Chef) -> Recipe:
    """다른 샘플 레시피 (중복 테스트용)"""
    recipe = Recipe(
        id=str(uuid4()),
        chef_id=sample_chef.id,
        title="백종원 된장찌개",
        description="집에서 간단하게 만드는 된장찌개",
        thumbnail_url="https://example.com/doenjang.jpg",
        prep_time_minutes=15,
        cook_time_minutes=25,
        servings=3,
        difficulty="easy",
    )
    db_session.add(recipe)
    await db_session.flush()
    return recipe


@pytest_asyncio.fixture
async def saved_recipe(
    db_session: AsyncSession,
    default_cookbook: Cookbook,
    sample_recipe: Recipe,
) -> SavedRecipe:
    """저장된 레시피"""
    saved = SavedRecipe(
        id=str(uuid4()),
        cookbook_id=default_cookbook.id,
        original_recipe_id=sample_recipe.id,
        memo="백종원 레시피! 돼지고기 300g 필요",
    )
    db_session.add(saved)
    await db_session.flush()
    return saved


@pytest_asyncio.fixture
async def multiple_saved_recipes(
    db_session: AsyncSession,
    default_cookbook: Cookbook,
    sample_recipe: Recipe,
    another_recipe: Recipe,
) -> list[SavedRecipe]:
    """여러 저장된 레시피 (페이지네이션 테스트용)"""
    saved_recipes = []

    # 첫 번째 레시피 저장
    saved1 = SavedRecipe(
        id=str(uuid4()),
        cookbook_id=default_cookbook.id,
        original_recipe_id=sample_recipe.id,
        memo="첫 번째 레시피",
    )
    db_session.add(saved1)
    saved_recipes.append(saved1)

    # 두 번째 레시피 저장
    saved2 = SavedRecipe(
        id=str(uuid4()),
        cookbook_id=default_cookbook.id,
        original_recipe_id=another_recipe.id,
        memo="두 번째 레시피",
    )
    db_session.add(saved2)
    saved_recipes.append(saved2)

    await db_session.flush()
    return saved_recipes


@pytest.fixture
def save_recipe_data(sample_recipe: Recipe) -> dict:
    """레시피 저장 요청 데이터"""
    return {
        "recipe_id": sample_recipe.id,
        "memo": "테스트 메모입니다",
    }


@pytest.fixture
def save_recipe_data_no_memo(sample_recipe: Recipe) -> dict:
    """레시피 저장 요청 데이터 (메모 없음)"""
    return {
        "recipe_id": sample_recipe.id,
    }


@pytest.fixture
def update_saved_recipe_data() -> dict:
    """저장된 레시피 수정 요청 데이터"""
    return {
        "memo": "수정된 메모입니다. 청양고추 추가!",
    }
