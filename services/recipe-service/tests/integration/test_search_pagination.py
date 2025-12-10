"""
페이지네이션 Integration 테스트

실제 데이터베이스를 사용한 커서 기반 페이지네이션 통합 테스트
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.models import Chef, Recipe
from recipe_service.schemas.search import SearchQueryParams
from recipe_service.services.search_service import SearchService


@pytest.fixture
async def pagination_test_data(test_session: AsyncSession):
    """페이지네이션 테스트용 데이터 설정 (10개 레시피)"""
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

    base_time = datetime.now(timezone.utc)
    recipes = []

    for i in range(10):
        recipe = Recipe(
            id=str(uuid4()),
            chef_id=chef_id,
            title=f"레시피 {i+1}",
            description=f"테스트 레시피 {i+1}",
            cook_time_minutes=15 + i * 5,
            difficulty="easy",
            exposure_score=100 - i * 10,  # 100, 90, 80, ...
            view_count=1000 - i * 100,  # 1000, 900, 800, ...
            is_active=True,
            created_at=base_time - timedelta(days=i),  # 최신순: 0일 전, 1일 전, ...
            updated_at=base_time - timedelta(days=i),
        )
        recipes.append(recipe)

    test_session.add_all(recipes)
    await test_session.commit()

    return {"chef": chef, "recipes": recipes}


class TestFirstPageIntegration:
    """첫 페이지 통합 테스트"""

    @pytest.mark.asyncio
    async def test_first_page_with_limit(self, test_session: AsyncSession, pagination_test_data):
        """limit 지정 시 첫 페이지"""
        service = SearchService(test_session)
        params = SearchQueryParams(limit=3)

        result = await service.search(params)

        assert len(result.items) == 3
        assert result.has_more is True
        assert result.next_cursor is not None

    @pytest.mark.asyncio
    async def test_first_page_all_results(self, test_session: AsyncSession, pagination_test_data):
        """전체 결과가 limit 이하면 has_more=False"""
        service = SearchService(test_session)
        params = SearchQueryParams(limit=20)  # 10개 레시피보다 큼

        result = await service.search(params)

        assert len(result.items) == 10
        assert result.has_more is False
        assert result.next_cursor is None


class TestNextPageIntegration:
    """다음 페이지 통합 테스트"""

    @pytest.mark.asyncio
    async def test_next_page_with_cursor(self, test_session: AsyncSession, pagination_test_data):
        """커서로 다음 페이지 조회"""
        service = SearchService(test_session)

        # 첫 페이지
        params1 = SearchQueryParams(limit=3, sort="relevance")
        result1 = await service.search(params1)

        # 두 번째 페이지
        params2 = SearchQueryParams(
            limit=3,
            sort="relevance",
            cursor=result1.next_cursor,
        )
        result2 = await service.search(params2)

        # 첫 페이지와 두 번째 페이지는 중복이 없어야 함
        ids1 = {item.id for item in result1.items}
        ids2 = {item.id for item in result2.items}
        assert ids1.isdisjoint(ids2)

        # 두 번째 페이지도 3개
        assert len(result2.items) == 3
        assert result2.has_more is True

    @pytest.mark.asyncio
    async def test_iterate_all_pages(self, test_session: AsyncSession, pagination_test_data):
        """모든 페이지 순회"""
        service = SearchService(test_session)
        all_ids = set()
        cursor = None
        page_count = 0

        while True:
            params = SearchQueryParams(limit=3, sort="relevance", cursor=cursor)
            result = await service.search(params)

            for item in result.items:
                all_ids.add(item.id)

            page_count += 1

            if not result.has_more:
                break

            cursor = result.next_cursor

        # 모든 10개 레시피를 가져와야 함
        assert len(all_ids) == 10
        # 3개씩 페이지네이션하면 4페이지 (3+3+3+1)
        assert page_count == 4


class TestCursorConsistencyIntegration:
    """커서 일관성 통합 테스트"""

    @pytest.mark.asyncio
    async def test_cursor_with_relevance_sort(self, test_session: AsyncSession, pagination_test_data):
        """relevance 정렬 커서 일관성"""
        service = SearchService(test_session)

        params1 = SearchQueryParams(limit=3, sort="relevance")
        result1 = await service.search(params1)

        params2 = SearchQueryParams(
            limit=3,
            sort="relevance",
            cursor=result1.next_cursor,
        )
        result2 = await service.search(params2)

        # relevance 내림차순이므로 result1의 마지막 아이템 점수 > result2의 첫 아이템 점수
        if result1.items and result2.items:
            assert result1.items[-1].exposure_score >= result2.items[0].exposure_score

    @pytest.mark.asyncio
    async def test_cursor_with_latest_sort(self, test_session: AsyncSession, pagination_test_data):
        """latest 정렬 커서 일관성"""
        service = SearchService(test_session)

        params1 = SearchQueryParams(limit=3, sort="latest")
        result1 = await service.search(params1)

        params2 = SearchQueryParams(
            limit=3,
            sort="latest",
            cursor=result1.next_cursor,
        )
        result2 = await service.search(params2)

        # latest 내림차순이므로 result1의 마지막 아이템 시간 >= result2의 첫 아이템 시간
        if result1.items and result2.items:
            assert result1.items[-1].created_at >= result2.items[0].created_at

    @pytest.mark.asyncio
    async def test_cursor_with_cook_time_sort(self, test_session: AsyncSession, pagination_test_data):
        """cook_time 정렬 커서 일관성"""
        service = SearchService(test_session)

        params1 = SearchQueryParams(limit=3, sort="cook_time")
        result1 = await service.search(params1)

        params2 = SearchQueryParams(
            limit=3,
            sort="cook_time",
            cursor=result1.next_cursor,
        )
        result2 = await service.search(params2)

        # cook_time 오름차순이므로 result1의 마지막 아이템 시간 <= result2의 첫 아이템 시간
        if result1.items and result2.items:
            time1 = result1.items[-1].cook_time_minutes or 0
            time2 = result2.items[0].cook_time_minutes or 0
            assert time1 <= time2


class TestInvalidCursorIntegration:
    """잘못된 커서 통합 테스트"""

    @pytest.mark.asyncio
    async def test_invalid_cursor_raises_error(self, test_session: AsyncSession, pagination_test_data):
        """잘못된 커서 형식은 에러"""
        from recipe_service.utils.cursor import CursorError

        service = SearchService(test_session)
        params = SearchQueryParams(limit=3, cursor="invalid-cursor")

        with pytest.raises(CursorError):
            await service.search(params)

    @pytest.mark.asyncio
    async def test_cursor_sort_mismatch(self, test_session: AsyncSession, pagination_test_data):
        """커서와 정렬 기준 불일치"""
        from recipe_service.utils.cursor import CursorError, encode_cursor

        service = SearchService(test_session)

        # latest 정렬로 커서 생성
        cursor_for_latest = encode_cursor("latest", "2024-12-10T12:00:00", "recipe-1")

        # relevance 정렬로 조회 시도
        params = SearchQueryParams(
            limit=3,
            sort="relevance",  # 다른 정렬
            cursor=cursor_for_latest,
        )

        with pytest.raises(CursorError):
            await service.search(params)
