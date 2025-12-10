"""
필터링 Integration 테스트

실제 데이터베이스를 사용한 필터링 통합 테스트
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.models import Chef, Recipe, RecipeIngredient, Tag, RecipeTag
from recipe_service.schemas.search import SearchQueryParams
from recipe_service.services.search_service import SearchService


@pytest.fixture
async def filter_test_data(test_session: AsyncSession):
    """필터 테스트용 데이터 설정"""
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
    tag_western = Tag(
        id=str(uuid4()),
        name="양식",
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
    test_session.add_all([tag_korean, tag_western, tag_stew])
    await test_session.flush()

    # 레시피 생성 (다양한 조건)
    recipes = [
        # 쉬운 난이도, 짧은 조리시간, 한식
        Recipe(
            id=str(uuid4()),
            chef_id=chef1_id,
            title="김치찌개",
            description="간단한 김치찌개",
            cook_time_minutes=20,
            difficulty="easy",
            exposure_score=90.0,
            view_count=1000,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        # 중간 난이도, 중간 조리시간, 한식
        Recipe(
            id=str(uuid4()),
            chef_id=chef1_id,
            title="불고기",
            description="맛있는 불고기",
            cook_time_minutes=45,
            difficulty="medium",
            exposure_score=85.0,
            view_count=800,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        # 어려운 난이도, 긴 조리시간, 양식
        Recipe(
            id=str(uuid4()),
            chef_id=chef2_id,
            title="스테이크",
            description="완벽한 스테이크",
            cook_time_minutes=60,
            difficulty="hard",
            exposure_score=95.0,
            view_count=1500,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        # 쉬운 난이도, 짧은 조리시간, 한식, 찌개
        Recipe(
            id=str(uuid4()),
            chef_id=chef2_id,
            title="된장찌개",
            description="구수한 된장찌개",
            cook_time_minutes=25,
            difficulty="easy",
            exposure_score=80.0,
            view_count=600,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    test_session.add_all(recipes)
    await test_session.flush()

    # 레시피-태그 연결
    recipe_tags = [
        # 김치찌개: 한식, 찌개
        RecipeTag(recipe_id=recipes[0].id, tag_id=tag_korean.id),
        RecipeTag(recipe_id=recipes[0].id, tag_id=tag_stew.id),
        # 불고기: 한식
        RecipeTag(recipe_id=recipes[1].id, tag_id=tag_korean.id),
        # 스테이크: 양식
        RecipeTag(recipe_id=recipes[2].id, tag_id=tag_western.id),
        # 된장찌개: 한식, 찌개
        RecipeTag(recipe_id=recipes[3].id, tag_id=tag_korean.id),
        RecipeTag(recipe_id=recipes[3].id, tag_id=tag_stew.id),
    ]
    test_session.add_all(recipe_tags)
    await test_session.commit()

    return {
        "chef1": chef1,
        "chef2": chef2,
        "recipes": recipes,
        "tag_korean": tag_korean,
        "tag_western": tag_western,
        "tag_stew": tag_stew,
    }


class TestDifficultyFilterIntegration:
    """난이도 필터 통합 테스트"""

    @pytest.mark.asyncio
    async def test_filter_by_easy_difficulty(self, test_session: AsyncSession, filter_test_data):
        """쉬운 난이도 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(difficulty="easy")

        result = await service.search(params)

        assert len(result.items) == 2
        for item in result.items:
            assert item.difficulty == "easy"

    @pytest.mark.asyncio
    async def test_filter_by_medium_difficulty(self, test_session: AsyncSession, filter_test_data):
        """중간 난이도 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(difficulty="medium")

        result = await service.search(params)

        assert len(result.items) == 1
        assert result.items[0].difficulty == "medium"

    @pytest.mark.asyncio
    async def test_filter_by_hard_difficulty(self, test_session: AsyncSession, filter_test_data):
        """어려운 난이도 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(difficulty="hard")

        result = await service.search(params)

        assert len(result.items) == 1
        assert result.items[0].difficulty == "hard"


class TestCookTimeFilterIntegration:
    """조리시간 필터 통합 테스트"""

    @pytest.mark.asyncio
    async def test_filter_by_max_cook_time_30(self, test_session: AsyncSession, filter_test_data):
        """30분 이하 조리시간 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(max_cook_time=30)

        result = await service.search(params)

        assert len(result.items) == 2
        for item in result.items:
            assert item.cook_time_minutes <= 30

    @pytest.mark.asyncio
    async def test_filter_by_max_cook_time_60(self, test_session: AsyncSession, filter_test_data):
        """60분 이하 조리시간 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(max_cook_time=60)

        result = await service.search(params)

        assert len(result.items) == 4
        for item in result.items:
            assert item.cook_time_minutes <= 60


class TestTagFilterIntegration:
    """태그 필터 통합 테스트"""

    @pytest.mark.asyncio
    async def test_filter_by_korean_tag(self, test_session: AsyncSession, filter_test_data):
        """한식 태그 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(tag="한식")

        result = await service.search(params)

        assert len(result.items) == 3
        for item in result.items:
            tag_names = [tag.name for tag in item.tags]
            assert "한식" in tag_names

    @pytest.mark.asyncio
    async def test_filter_by_western_tag(self, test_session: AsyncSession, filter_test_data):
        """양식 태그 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(tag="양식")

        result = await service.search(params)

        assert len(result.items) == 1
        assert result.items[0].title == "스테이크"

    @pytest.mark.asyncio
    async def test_filter_by_stew_tag(self, test_session: AsyncSession, filter_test_data):
        """찌개 태그 필터"""
        service = SearchService(test_session)
        params = SearchQueryParams(tag="찌개")

        result = await service.search(params)

        assert len(result.items) == 2
        titles = [item.title for item in result.items]
        assert "김치찌개" in titles
        assert "된장찌개" in titles


class TestChefIdFilterIntegration:
    """요리사 ID 필터 통합 테스트"""

    @pytest.mark.asyncio
    async def test_filter_by_chef_id(self, test_session: AsyncSession, filter_test_data):
        """특정 요리사 필터"""
        service = SearchService(test_session)
        chef1 = filter_test_data["chef1"]
        params = SearchQueryParams(chef_id=chef1.id)

        result = await service.search(params)

        assert len(result.items) == 2
        for item in result.items:
            assert item.chef is not None
            assert item.chef.name == "백종원"


class TestFilterCombinationsIntegration:
    """필터 조합 통합 테스트"""

    @pytest.mark.asyncio
    async def test_difficulty_and_cook_time_filter(self, test_session: AsyncSession, filter_test_data):
        """난이도 + 조리시간 필터 조합"""
        service = SearchService(test_session)
        params = SearchQueryParams(difficulty="easy", max_cook_time=25)

        result = await service.search(params)

        assert len(result.items) == 2
        for item in result.items:
            assert item.difficulty == "easy"
            assert item.cook_time_minutes <= 25

    @pytest.mark.asyncio
    async def test_keyword_and_filter_combination(self, test_session: AsyncSession, filter_test_data):
        """키워드 + 필터 조합"""
        service = SearchService(test_session)
        params = SearchQueryParams(q="찌개", difficulty="easy")

        result = await service.search(params)

        assert len(result.items) >= 1
        for item in result.items:
            assert item.difficulty == "easy"
            assert "찌개" in item.title

    @pytest.mark.asyncio
    async def test_all_filters_combination(self, test_session: AsyncSession, filter_test_data):
        """모든 필터 조합"""
        service = SearchService(test_session)
        chef2 = filter_test_data["chef2"]
        params = SearchQueryParams(
            difficulty="easy",
            max_cook_time=30,
            tag="찌개",
            chef_id=chef2.id,
        )

        result = await service.search(params)

        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "된장찌개"
        assert item.difficulty == "easy"
        assert item.cook_time_minutes <= 30
        assert item.chef.name == "김수미"

    @pytest.mark.asyncio
    async def test_filters_with_no_results(self, test_session: AsyncSession, filter_test_data):
        """필터 결과 없음"""
        service = SearchService(test_session)
        params = SearchQueryParams(difficulty="hard", tag="한식")

        result = await service.search(params)

        # 한식 중 hard 난이도는 없음
        assert len(result.items) == 0
        assert result.has_more is False
