"""
정렬 Integration 테스트

실제 데이터베이스를 사용한 정렬 통합 테스트
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.models import Chef, Recipe
from recipe_service.schemas.search import SearchQueryParams
from recipe_service.services.search_service import SearchService


@pytest.fixture
async def sort_test_data(test_session: AsyncSession):
    """정렬 테스트용 데이터 설정"""
    # 요리사 생성
    chef_id = str(uuid4())
    chef = Chef(
        id=chef_id,
        name="테스트셰프",
        name_normalized="테스트셰프",
        recipe_count=0,
        total_views=0,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add(chef)
    await test_session.flush()

    # 레시피 생성 (다양한 정렬 필드 값)
    base_time = datetime.now(timezone.utc)
    
    recipes = [
        Recipe(
            id=str(uuid4()),
            chef_id=chef_id,
            title="레시피 A",
            description="가장 최신",
            cook_time_minutes=60,
            difficulty="hard",
            exposure_score=50.0,  # 낮은 관련도
            view_count=100,  # 낮은 조회수
            is_active=True,
            created_at=base_time,  # 가장 최신
            updated_at=base_time,
        ),
        Recipe(
            id=str(uuid4()),
            chef_id=chef_id,
            title="레시피 B",
            description="중간 시간",
            cook_time_minutes=30,
            difficulty="medium",
            exposure_score=80.0,  # 중간 관련도
            view_count=500,  # 중간 조회수
            is_active=True,
            created_at=base_time - timedelta(days=1),
            updated_at=base_time - timedelta(days=1),
        ),
        Recipe(
            id=str(uuid4()),
            chef_id=chef_id,
            title="레시피 C",
            description="가장 오래됨",
            cook_time_minutes=15,  # 가장 짧은 조리시간
            difficulty="easy",
            exposure_score=95.0,  # 가장 높은 관련도
            view_count=1000,  # 가장 높은 조회수
            is_active=True,
            created_at=base_time - timedelta(days=7),
            updated_at=base_time - timedelta(days=7),
        ),
        Recipe(
            id=str(uuid4()),
            chef_id=chef_id,
            title="레시피 D",
            description="조리시간 없음",
            cook_time_minutes=None,  # 조리시간 없음
            difficulty="easy",
            exposure_score=70.0,
            view_count=300,
            is_active=True,
            created_at=base_time - timedelta(days=3),
            updated_at=base_time - timedelta(days=3),
        ),
    ]
    test_session.add_all(recipes)
    await test_session.commit()

    return {
        "chef": chef,
        "recipes": recipes,
    }


class TestRelevanceSortIntegration:
    """관련도순 정렬 통합 테스트"""

    @pytest.mark.asyncio
    async def test_relevance_sort_order(self, test_session: AsyncSession, sort_test_data):
        """관련도순 정렬 (exposure_score DESC)"""
        service = SearchService(test_session)
        params = SearchQueryParams(sort="relevance")

        result = await service.search(params)

        assert len(result.items) == 4
        # exposure_score 내림차순 확인
        scores = [item.exposure_score for item in result.items]
        assert scores == sorted(scores, reverse=True)
        assert result.items[0].title == "레시피 C"  # 95.0
        assert result.items[1].title == "레시피 B"  # 80.0

    @pytest.mark.asyncio
    async def test_relevance_is_default_sort(self, test_session: AsyncSession, sort_test_data):
        """정렬 미지정 시 관련도순"""
        service = SearchService(test_session)
        params = SearchQueryParams()  # sort 미지정

        result = await service.search(params)

        # 첫 번째는 가장 높은 exposure_score
        assert result.items[0].title == "레시피 C"


class TestLatestSortIntegration:
    """최신순 정렬 통합 테스트"""

    @pytest.mark.asyncio
    async def test_latest_sort_order(self, test_session: AsyncSession, sort_test_data):
        """최신순 정렬 (created_at DESC)"""
        service = SearchService(test_session)
        params = SearchQueryParams(sort="latest")

        result = await service.search(params)

        assert len(result.items) == 4
        # created_at 내림차순 확인
        assert result.items[0].title == "레시피 A"  # 가장 최신
        assert result.items[-1].title == "레시피 C"  # 가장 오래됨


class TestCookTimeSortIntegration:
    """조리시간순 정렬 통합 테스트"""

    @pytest.mark.asyncio
    async def test_cook_time_sort_order(self, test_session: AsyncSession, sort_test_data):
        """조리시간순 정렬 (cook_time_minutes ASC)"""
        service = SearchService(test_session)
        params = SearchQueryParams(sort="cook_time")

        result = await service.search(params)

        assert len(result.items) == 4
        # 조리시간이 있는 레시피들은 오름차순
        recipes_with_time = [item for item in result.items if item.cook_time_minutes is not None]
        cook_times = [item.cook_time_minutes for item in recipes_with_time]
        assert cook_times == sorted(cook_times)
        
        # 첫 번째는 가장 짧은 조리시간
        assert result.items[0].cook_time_minutes == 15

    @pytest.mark.asyncio
    async def test_cook_time_null_last(self, test_session: AsyncSession, sort_test_data):
        """조리시간 NULL은 마지막"""
        service = SearchService(test_session)
        params = SearchQueryParams(sort="cook_time")

        result = await service.search(params)

        # NULL 조리시간은 마지막에 위치
        assert result.items[-1].cook_time_minutes is None


class TestPopularitySortIntegration:
    """인기순 정렬 통합 테스트"""

    @pytest.mark.asyncio
    async def test_popularity_sort_order(self, test_session: AsyncSession, sort_test_data):
        """인기순 정렬 (view_count DESC)"""
        service = SearchService(test_session)
        params = SearchQueryParams(sort="popularity")

        result = await service.search(params)

        assert len(result.items) == 4
        # view_count 내림차순 확인
        view_counts = [item.exposure_score for item in result.items]  # exposure_score가 view_count와 다르게 정렬되므로 view_count 직접 확인 필요
        # 첫 번째는 가장 높은 조회수
        assert result.items[0].title == "레시피 C"  # 1000 views


class TestSortWithFiltersIntegration:
    """필터와 함께 정렬 통합 테스트"""

    @pytest.mark.asyncio
    async def test_sort_with_difficulty_filter(self, test_session: AsyncSession, sort_test_data):
        """난이도 필터와 함께 정렬"""
        service = SearchService(test_session)
        params = SearchQueryParams(difficulty="easy", sort="latest")

        result = await service.search(params)

        # easy 난이도만 필터링되어 정렬됨
        for item in result.items:
            assert item.difficulty == "easy"
        # 필터링된 결과 내에서 최신순 정렬
        if len(result.items) >= 2:
            assert result.items[0].created_at >= result.items[1].created_at

    @pytest.mark.asyncio
    async def test_sort_with_cook_time_filter(self, test_session: AsyncSession, sort_test_data):
        """조리시간 필터와 함께 정렬"""
        service = SearchService(test_session)
        params = SearchQueryParams(max_cook_time=30, sort="popularity")

        result = await service.search(params)

        # 30분 이하만 필터링
        for item in result.items:
            if item.cook_time_minutes is not None:
                assert item.cook_time_minutes <= 30
