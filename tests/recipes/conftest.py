"""
Recipes 모듈 테스트 픽스처

유사 레시피 추천 테스트를 위한 샘플 데이터를 제공합니다.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.models import Chef, CookingStep, Recipe, RecipeIngredient, RecipeTag, Tag


# ==========================================================================
# 태그 픽스처
# ==========================================================================


@pytest_asyncio.fixture
async def sample_tags(db_session: AsyncSession) -> list[Tag]:
    """샘플 태그 목록 (10개)"""
    tags_data = [
        {"name": "한식", "category": "cuisine"},
        {"name": "양식", "category": "cuisine"},
        {"name": "중식", "category": "cuisine"},
        {"name": "찌개", "category": "dish_type"},
        {"name": "볶음", "category": "dish_type"},
        {"name": "구이", "category": "dish_type"},
        {"name": "아침", "category": "meal_type"},
        {"name": "점심", "category": "meal_type"},
        {"name": "저녁", "category": "meal_type"},
        {"name": "비건", "category": "dietary"},
    ]

    tags = []
    for data in tags_data:
        tag = Tag(
            id=str(uuid4()),
            name=data["name"],
            category=data["category"],
        )
        db_session.add(tag)
        tags.append(tag)

    await db_session.commit()

    for tag in tags:
        await db_session.refresh(tag)

    return tags


# ==========================================================================
# 요리사 픽스처
# ==========================================================================


@pytest_asyncio.fixture
async def sample_chef(db_session: AsyncSession) -> Chef:
    """샘플 요리사 (1명)"""
    chef = Chef(
        id=str(uuid4()),
        name="백종원",
        name_normalized="백종원",
        profile_image_url="https://example.com/chef1.jpg",
        bio="대한민국 대표 요리연구가",
        specialty="한식",
        recipe_count=100,
        total_views=1000000,
        avg_rating=4.8,
        is_verified=True,
    )
    db_session.add(chef)
    await db_session.commit()
    await db_session.refresh(chef)
    return chef


@pytest_asyncio.fixture
async def sample_chefs(db_session: AsyncSession) -> list[Chef]:
    """샘플 요리사 목록 (3명)"""
    chefs_data = [
        {
            "name": "백종원",
            "name_normalized": "백종원",
            "specialty": "한식",
            "recipe_count": 100,
            "is_verified": True,
        },
        {
            "name": "이연복",
            "name_normalized": "이연복",
            "specialty": "중식",
            "recipe_count": 80,
            "is_verified": True,
        },
        {
            "name": "김풍",
            "name_normalized": "김풍",
            "specialty": "양식",
            "recipe_count": 50,
            "is_verified": False,
        },
    ]

    chefs = []
    for data in chefs_data:
        chef = Chef(
            id=str(uuid4()),
            **data,
            profile_image_url=f"https://example.com/{data['name']}.jpg",
            total_views=10000,
            avg_rating=4.5,
        )
        db_session.add(chef)
        chefs.append(chef)

    await db_session.commit()

    for chef in chefs:
        await db_session.refresh(chef)

    return chefs


# ==========================================================================
# 레시피 픽스처
# ==========================================================================


@pytest_asyncio.fixture
async def sample_recipe(
    db_session: AsyncSession,
    sample_chef: Chef,
    sample_tags: list[Tag],
) -> Recipe:
    """샘플 레시피 (1개) - 태그 3개, 재료 5개, 조리 단계 3개"""
    recipe = Recipe(
        id=str(uuid4()),
        chef_id=sample_chef.id,
        title="김치찌개",
        description="맛있는 돼지고기 김치찌개",
        thumbnail_url="https://example.com/kimchi-jjigae.jpg",
        prep_time_minutes=10,
        cook_time_minutes=30,
        servings=2,
        difficulty="medium",
        source_url="https://example.com/recipes/1",
        source_platform="youtube",
        exposure_score=100.0,
        view_count=5000,
        is_active=True,
    )
    db_session.add(recipe)
    await db_session.flush()

    # 재료 추가 (5개)
    ingredients_data = [
        {"name": "돼지고기", "amount": "200", "unit": "g"},
        {"name": "김치", "amount": "300", "unit": "g"},
        {"name": "두부", "amount": "1", "unit": "모"},
        {"name": "대파", "amount": "1", "unit": "대"},
        {"name": "고춧가루", "amount": "1", "unit": "큰술"},
    ]

    for i, ing_data in enumerate(ingredients_data):
        ingredient = RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe.id,
            name=ing_data["name"],
            amount=ing_data["amount"],
            unit=ing_data["unit"],
            order_index=i,
        )
        db_session.add(ingredient)

    # 조리 단계 추가 (3개)
    steps_data = [
        {"step_number": 1, "description": "돼지고기와 김치를 먹기 좋은 크기로 썬다."},
        {"step_number": 2, "description": "냄비에 돼지고기와 김치를 넣고 볶는다."},
        {"step_number": 3, "description": "물을 붓고 끓인 후 두부를 넣는다."},
    ]

    for step_data in steps_data:
        step = CookingStep(
            id=str(uuid4()),
            recipe_id=recipe.id,
            step_number=step_data["step_number"],
            description=step_data["description"],
        )
        db_session.add(step)

    # 태그 연결 (3개: 한식, 찌개, 저녁)
    tag_names = ["한식", "찌개", "저녁"]
    for tag in sample_tags:
        if tag.name in tag_names:
            recipe_tag = RecipeTag(
                id=str(uuid4()),
                recipe_id=recipe.id,
                tag_id=tag.id,
            )
            db_session.add(recipe_tag)

    await db_session.commit()
    await db_session.refresh(recipe)

    return recipe


@pytest_asyncio.fixture
async def recipe_without_chef(
    db_session: AsyncSession,
    sample_tags: list[Tag],
) -> Recipe:
    """요리사 없는 샘플 레시피"""
    recipe = Recipe(
        id=str(uuid4()),
        chef_id=None,
        title="간단 계란볶음밥",
        description="누구나 쉽게 만드는 볶음밥",
        thumbnail_url="https://example.com/fried-rice.jpg",
        prep_time_minutes=5,
        cook_time_minutes=10,
        servings=1,
        difficulty="easy",
        exposure_score=50.0,
        view_count=1000,
        is_active=True,
    )
    db_session.add(recipe)
    await db_session.flush()

    # 태그 연결 (2개: 한식, 볶음)
    tag_names = ["한식", "볶음"]
    for tag in sample_tags:
        if tag.name in tag_names:
            recipe_tag = RecipeTag(
                id=str(uuid4()),
                recipe_id=recipe.id,
                tag_id=tag.id,
            )
            db_session.add(recipe_tag)

    await db_session.commit()
    await db_session.refresh(recipe)

    return recipe


@pytest_asyncio.fixture
async def many_similar_recipes(
    db_session: AsyncSession,
    sample_chef: Chef,
    sample_tags: list[Tag],
) -> list[Recipe]:
    """
    유사 레시피 테스트용 레시피 목록 (15개)

    기준 레시피와 태그/재료가 겹치는 레시피들
    """
    recipes = []

    # 기준 레시피 (김치찌개)
    base_recipe = Recipe(
        id=str(uuid4()),
        chef_id=sample_chef.id,
        title="김치찌개",
        description="맛있는 돼지고기 김치찌개",
        thumbnail_url="https://example.com/kimchi-jjigae.jpg",
        prep_time_minutes=10,
        cook_time_minutes=30,
        servings=2,
        difficulty="medium",
        exposure_score=100.0,
        view_count=5000,
        is_active=True,
    )
    db_session.add(base_recipe)
    recipes.append(base_recipe)

    # 유사 레시피들
    similar_recipes_data = [
        {"title": "돼지고기 김치찌개", "exposure_score": 95.0, "tags": ["한식", "찌개"]},
        {"title": "참치 김치찌개", "exposure_score": 90.0, "tags": ["한식", "찌개"]},
        {"title": "된장찌개", "exposure_score": 88.0, "tags": ["한식", "찌개", "저녁"]},
        {"title": "순두부찌개", "exposure_score": 85.0, "tags": ["한식", "찌개"]},
        {"title": "부대찌개", "exposure_score": 82.0, "tags": ["한식", "찌개", "저녁"]},
        {"title": "불고기", "exposure_score": 78.0, "tags": ["한식", "구이"]},
        {"title": "삼겹살 구이", "exposure_score": 75.0, "tags": ["한식", "구이"]},
        {"title": "김치볶음밥", "exposure_score": 70.0, "tags": ["한식", "볶음"]},
        {"title": "제육볶음", "exposure_score": 68.0, "tags": ["한식", "볶음"]},
        {"title": "짜장면", "exposure_score": 65.0, "tags": ["중식"]},
        {"title": "짬뽕", "exposure_score": 62.0, "tags": ["중식"]},
        {"title": "파스타", "exposure_score": 58.0, "tags": ["양식"]},
        {"title": "스테이크", "exposure_score": 55.0, "tags": ["양식", "구이"]},
        {"title": "비건 샐러드", "exposure_score": 50.0, "tags": ["양식", "비건"]},
    ]

    await db_session.flush()

    # 기준 레시피에 태그 연결
    base_tags = ["한식", "찌개", "저녁"]
    for tag in sample_tags:
        if tag.name in base_tags:
            recipe_tag = RecipeTag(
                id=str(uuid4()),
                recipe_id=base_recipe.id,
                tag_id=tag.id,
            )
            db_session.add(recipe_tag)

    # 유사 레시피들 생성
    for i, data in enumerate(similar_recipes_data):
        recipe = Recipe(
            id=str(uuid4()),
            chef_id=sample_chef.id if i < 7 else None,  # 일부는 다른 요리사
            title=data["title"],
            description=f"{data['title']} 레시피입니다.",
            thumbnail_url=f"https://example.com/{i}.jpg",
            prep_time_minutes=10 + i,
            cook_time_minutes=20 + i * 2,
            servings=2,
            difficulty="medium" if i % 2 == 0 else "easy",
            exposure_score=data["exposure_score"],
            view_count=1000 * (15 - i),
            is_active=True,
        )
        db_session.add(recipe)
        recipes.append(recipe)
        await db_session.flush()

        # 태그 연결
        for tag in sample_tags:
            if tag.name in data["tags"]:
                recipe_tag = RecipeTag(
                    id=str(uuid4()),
                    recipe_id=recipe.id,
                    tag_id=tag.id,
                )
                db_session.add(recipe_tag)

    await db_session.commit()

    for recipe in recipes:
        await db_session.refresh(recipe)

    return recipes


@pytest_asyncio.fixture
async def recipe_with_no_tags(db_session: AsyncSession) -> Recipe:
    """태그 없는 레시피"""
    recipe = Recipe(
        id=str(uuid4()),
        chef_id=None,
        title="재료만 있는 요리",
        description="태그 없는 레시피",
        exposure_score=10.0,
        view_count=100,
        is_active=True,
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)
    return recipe


@pytest_asyncio.fixture
async def recipe_without_difficulty(
    db_session: AsyncSession,
    sample_tags: list[Tag],
) -> Recipe:
    """난이도 없는 레시피 (카테고리 인기 레시피 테스트용)"""
    recipe = Recipe(
        id=str(uuid4()),
        chef_id=None,
        title="난이도 미정 요리",
        description="난이도가 설정되지 않은 레시피",
        thumbnail_url="https://example.com/no-difficulty.jpg",
        prep_time_minutes=None,
        cook_time_minutes=None,
        servings=1,
        difficulty=None,
        exposure_score=30.0,
        view_count=500,
        is_active=True,
    )
    db_session.add(recipe)
    await db_session.flush()

    # 태그 연결 (1개: 한식)
    for tag in sample_tags:
        if tag.name == "한식":
            recipe_tag = RecipeTag(
                id=str(uuid4()),
                recipe_id=recipe.id,
                tag_id=tag.id,
            )
            db_session.add(recipe_tag)
            break

    await db_session.commit()
    await db_session.refresh(recipe)
    return recipe


# ==========================================================================
# Redis 모킹 픽스처
# ==========================================================================


@pytest.fixture
def mock_redis_cache(mocker):
    """Redis 캐시 모킹"""
    mock_cache = mocker.MagicMock()
    mock_cache.get = mocker.AsyncMock(return_value=None)
    mock_cache.set = mocker.AsyncMock(return_value=True)
    mock_cache.delete = mocker.AsyncMock(return_value=True)
    mock_cache.exists = mocker.AsyncMock(return_value=False)

    mocker.patch(
        "app.infra.redis.get_redis_cache",
        return_value=mock_cache,
    )

    return mock_cache
