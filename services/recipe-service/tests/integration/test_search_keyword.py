"""
키워드 검색 Integration 테스트

실제 데이터베이스와 검색 서비스를 사용한 통합 테스트
- 제목/설명/재료/요리사 매칭 검증
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.models import Chef, Recipe, RecipeIngredient, Tag, RecipeTag
from recipe_service.schemas.search import SearchQueryParams
from recipe_service.services.search_service import SearchService


@pytest.fixture
async def search_test_data(test_session: AsyncSession):
    """검색 테스트용 데이터 설정"""
    # 요리사 생성
    chef1_id = str(uuid4())
    chef2_id = str(uuid4())
    
    chef1 = Chef(
        id=chef1_id,
        name="백종원",
        name_normalized="백종원",
        recipe_count=0,
        total_views=0,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    chef2 = Chef(
        id=chef2_id,
        name="김수미",
        name_normalized="김수미",
        recipe_count=0,
        total_views=0,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add_all([chef1, chef2])
    await test_session.flush()

    # 태그 생성
    tag_korean = Tag(
        id=str(uuid4()),
        name="한식",
        category="cuisine",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    tag_stew = Tag(
        id=str(uuid4()),
        name="찌개",
        category="dish_type",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add_all([tag_korean, tag_stew])
    await test_session.flush()

    # 레시피 생성
    recipe1 = Recipe(
        id=str(uuid4()),
        chef_id=chef1_id,
        title="김치찌개",
        description="맛있는 김치찌개 레시피입니다",
        cook_time_minutes=30,
        difficulty="easy",
        exposure_score=90.0,
        view_count=1000,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    recipe2 = Recipe(
        id=str(uuid4()),
        chef_id=chef2_id,
        title="된장찌개",
        description="구수한 된장찌개",
        cook_time_minutes=25,
        difficulty="easy",
        exposure_score=85.0,
        view_count=800,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    recipe3 = Recipe(
        id=str(uuid4()),
        chef_id=chef1_id,
        title="불고기",
        description="달콤한 불고기",
        cook_time_minutes=40,
        difficulty="medium",
        exposure_score=95.0,
        view_count=1500,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # 비활성 레시피 (검색에서 제외되어야 함)
    recipe_inactive = Recipe(
        id=str(uuid4()),
        chef_id=chef1_id,
        title="비활성 김치볶음",
        description="이 레시피는 검색되면 안됩니다",
        cook_time_minutes=20,
        difficulty="easy",
        exposure_score=50.0,
        view_count=100,
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add_all([recipe1, recipe2, recipe3, recipe_inactive])
    await test_session.flush()

    # 재료 생성
    ingredients = [
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe1.id,
            name="김치",
            amount="300",
            unit="g",
            order_index=0,
        ),
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe1.id,
            name="돼지고기",
            amount="200",
            unit="g",
            order_index=1,
        ),
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe2.id,
            name="된장",
            amount="2",
            unit="큰술",
            order_index=0,
        ),
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe2.id,
            name="두부",
            amount="1",
            unit="모",
            order_index=1,
        ),
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe3.id,
            name="소고기",
            amount="300",
            unit="g",
            order_index=0,
        ),
    ]
    test_session.add_all(ingredients)

    # 레시피-태그 연결
    recipe_tags = [
        RecipeTag(recipe_id=recipe1.id, tag_id=tag_korean.id),
        RecipeTag(recipe_id=recipe1.id, tag_id=tag_stew.id),
        RecipeTag(recipe_id=recipe2.id, tag_id=tag_korean.id),
        RecipeTag(recipe_id=recipe2.id, tag_id=tag_stew.id),
        RecipeTag(recipe_id=recipe3.id, tag_id=tag_korean.id),
    ]
    test_session.add_all(recipe_tags)
    await test_session.commit()

    return {
        "chef1": chef1,
        "chef2": chef2,
        "recipe1": recipe1,
        "recipe2": recipe2,
        "recipe3": recipe3,
        "recipe_inactive": recipe_inactive,
        "tag_korean": tag_korean,
        "tag_stew": tag_stew,
    }


class TestKeywordSearchIntegration:
    """키워드 검색 통합 테스트"""

    @pytest.mark.asyncio
    async def test_search_by_title(self, test_session: AsyncSession, search_test_data):
        """제목으로 검색"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="김치")

        result = await service.search(params)

        assert len(result.items) >= 1
        titles = [item.title for item in result.items]
        assert "김치찌개" in titles

    @pytest.mark.asyncio
    async def test_search_by_description(self, test_session: AsyncSession, search_test_data):
        """설명으로 검색"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="구수한")

        result = await service.search(params)

        assert len(result.items) >= 1
        assert any("된장찌개" in item.title for item in result.items)

    @pytest.mark.asyncio
    async def test_search_by_ingredient(self, test_session: AsyncSession, search_test_data):
        """재료로 검색"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="두부")

        result = await service.search(params)

        assert len(result.items) >= 1
        # 두부가 재료로 있는 된장찌개가 검색되어야 함
        titles = [item.title for item in result.items]
        assert "된장찌개" in titles

    @pytest.mark.asyncio
    async def test_search_by_chef_name(self, test_session: AsyncSession, search_test_data):
        """요리사 이름으로 검색"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="백종원")

        result = await service.search(params)

        assert len(result.items) >= 1
        # 백종원 셰프의 레시피만 검색되어야 함
        for item in result.items:
            assert item.chef is not None
            assert item.chef.name == "백종원"

    @pytest.mark.asyncio
    async def test_search_excludes_inactive_recipes(self, test_session: AsyncSession, search_test_data):
        """비활성 레시피 제외 검증"""
        service = SearchService(test_session)
        # "비활성"이 제목에 있는 비활성 레시피가 검색되지 않아야 함
        params = SearchQueryParams(q="비활성")

        result = await service.search(params)

        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_search_empty_result(self, test_session: AsyncSession, search_test_data):
        """검색 결과 없음"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="존재하지않는레시피12345")

        result = await service.search(params)

        assert len(result.items) == 0
        assert result.has_more is False
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_search_without_keyword(self, test_session: AsyncSession, search_test_data):
        """키워드 없이 검색 (전체 조회)"""
        service = SearchService(test_session)
        params = SearchQueryParams()  # 키워드 없음

        result = await service.search(params)

        # 활성 레시피만 반환되어야 함
        assert len(result.items) >= 3
        titles = [item.title for item in result.items]
        assert "비활성 김치볶음" not in titles

    @pytest.mark.asyncio
    async def test_search_returns_chef_summary(self, test_session: AsyncSession, search_test_data):
        """검색 결과에 요리사 정보 포함 검증"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="찌개")

        result = await service.search(params)

        for item in result.items:
            assert item.chef is not None
            assert item.chef.id is not None
            assert item.chef.name is not None

    @pytest.mark.asyncio
    async def test_search_returns_tags(self, test_session: AsyncSession, search_test_data):
        """검색 결과에 태그 정보 포함 검증"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="찌개")

        result = await service.search(params)

        # 찌개 레시피에는 태그가 있어야 함
        for item in result.items:
            if "찌개" in item.title:
                assert len(item.tags) > 0
                tag_names = [tag.name for tag in item.tags]
                assert "한식" in tag_names or "찌개" in tag_names
