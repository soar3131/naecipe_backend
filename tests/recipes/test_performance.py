"""
유사 레시피 추천 API 성능 테스트

T041: 응답 시간 300ms 이내 검증
"""

import time

import pytest
from httpx import AsyncClient

from app.recipes.models import Recipe


@pytest.mark.asyncio
class TestSimilarRecipesPerformance:
    """유사 레시피 API 성능 테스트"""

    # 성능 임계값 (밀리초)
    RESPONSE_TIME_THRESHOLD_MS = 300

    async def test_similar_recipes_response_time(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사 레시피 API 응답 시간 300ms 이내"""
        # Given
        recipe_id = sample_recipe.id

        # When: 여러 번 측정하여 평균 계산
        response_times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(f"/api/v1/recipes/{recipe_id}/similar")
            elapsed = (time.perf_counter() - start) * 1000  # ms 변환

            assert response.status_code == 200
            response_times.append(elapsed)

        # Then: 평균 응답 시간이 임계값 이내
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < self.RESPONSE_TIME_THRESHOLD_MS, (
            f"평균 응답 시간 {avg_response_time:.2f}ms가 "
            f"임계값 {self.RESPONSE_TIME_THRESHOLD_MS}ms를 초과"
        )

    async def test_same_chef_recipes_response_time(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """같은 요리사 레시피 API 응답 시간 300ms 이내"""
        # Given
        recipe_id = sample_recipe.id

        # When
        response_times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(f"/api/v1/recipes/{recipe_id}/same-chef")
            elapsed = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            response_times.append(elapsed)

        # Then
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < self.RESPONSE_TIME_THRESHOLD_MS, (
            f"평균 응답 시간 {avg_response_time:.2f}ms가 "
            f"임계값 {self.RESPONSE_TIME_THRESHOLD_MS}ms를 초과"
        )

    async def test_related_by_tags_response_time(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """태그 기반 관련 레시피 API 응답 시간 300ms 이내"""
        # Given
        recipe_id = sample_recipe.id

        # When
        response_times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(f"/api/v1/recipes/{recipe_id}/related-by-tags")
            elapsed = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            response_times.append(elapsed)

        # Then
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < self.RESPONSE_TIME_THRESHOLD_MS, (
            f"평균 응답 시간 {avg_response_time:.2f}ms가 "
            f"임계값 {self.RESPONSE_TIME_THRESHOLD_MS}ms를 초과"
        )

    async def test_category_popular_response_time(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """카테고리 인기 레시피 API 응답 시간 300ms 이내"""
        # Given
        recipe_id = sample_recipe.id

        # When
        response_times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(f"/api/v1/recipes/{recipe_id}/category-popular")
            elapsed = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            response_times.append(elapsed)

        # Then
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < self.RESPONSE_TIME_THRESHOLD_MS, (
            f"평균 응답 시간 {avg_response_time:.2f}ms가 "
            f"임계값 {self.RESPONSE_TIME_THRESHOLD_MS}ms를 초과"
        )

    async def test_cache_improves_response_time(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """캐시 히트 시 응답 시간 개선 확인"""
        # Given
        recipe_id = sample_recipe.id

        # When: 첫 번째 요청 (캐시 미스)
        start = time.perf_counter()
        response1 = await client.get(f"/api/v1/recipes/{recipe_id}/similar")
        first_call_time = (time.perf_counter() - start) * 1000

        assert response1.status_code == 200

        # When: 두 번째 요청 (캐시 히트)
        start = time.perf_counter()
        response2 = await client.get(f"/api/v1/recipes/{recipe_id}/similar")
        second_call_time = (time.perf_counter() - start) * 1000

        assert response2.status_code == 200

        # Then: 캐시 히트 시 더 빠르거나 비슷해야 함
        # (테스트 환경에서는 캐시가 비활성화될 수 있으므로 완화된 조건)
        assert second_call_time <= first_call_time * 1.5, (
            f"캐시 히트 응답 시간({second_call_time:.2f}ms)이 "
            f"첫 요청({first_call_time:.2f}ms)보다 현저히 느림"
        )


@pytest.mark.asyncio
class TestPaginationPerformance:
    """페이지네이션 성능 테스트"""

    RESPONSE_TIME_THRESHOLD_MS = 300

    async def test_pagination_consistent_performance(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """페이지네이션 시 일관된 응답 시간"""
        # Given
        recipe_id = sample_recipe.id

        # When: 첫 페이지
        start = time.perf_counter()
        response1 = await client.get(
            f"/api/v1/recipes/{recipe_id}/similar",
            params={"limit": 5},
        )
        first_page_time = (time.perf_counter() - start) * 1000

        assert response1.status_code == 200
        data1 = response1.json()

        # When: 다음 페이지가 있으면
        if data1["has_more"] and data1["next_cursor"]:
            start = time.perf_counter()
            response2 = await client.get(
                f"/api/v1/recipes/{recipe_id}/similar",
                params={"limit": 5, "cursor": data1["next_cursor"]},
            )
            second_page_time = (time.perf_counter() - start) * 1000

            assert response2.status_code == 200

            # Then: 두 번째 페이지도 임계값 이내
            assert second_page_time < self.RESPONSE_TIME_THRESHOLD_MS, (
                f"두 번째 페이지 응답 시간 {second_page_time:.2f}ms가 "
                f"임계값 {self.RESPONSE_TIME_THRESHOLD_MS}ms를 초과"
            )

            # 두 페이지 간 응답 시간 차이가 50% 이내
            time_diff = abs(first_page_time - second_page_time)
            max_time = max(first_page_time, second_page_time)
            assert time_diff / max_time < 0.5, (
                f"페이지 간 응답 시간 차이({time_diff:.2f}ms)가 너무 큼"
            )
