"""
태그 기반 관련 레시피 API 통합 테스트

GET /api/v1/recipes/{recipe_id}/related-by-tags 엔드포인트 테스트
"""

import pytest
from httpx import AsyncClient

from app.recipes.models import Recipe


@pytest.mark.asyncio
class TestRelatedByTagsAPI:
    """태그 기반 관련 레시피 API 통합 테스트"""

    async def test_get_related_by_tags_success(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """태그 기반 관련 레시피 조회 성공"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/related-by-tags")

        # Then
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "next_cursor" in data
        assert "has_more" in data

    async def test_get_related_by_tags_excludes_base_recipe(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """기준 레시피는 결과에서 제외"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/related-by-tags")

        # Then
        assert response.status_code == 200
        data = response.json()

        recipe_ids = [item["id"] for item in data["items"]]
        assert sample_recipe.id not in recipe_ids

    async def test_get_related_by_tags_sorted_by_shared_count(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """공유 태그 개수 내림차순 정렬"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/related-by-tags")

        # Then
        assert response.status_code == 200
        data = response.json()

        items = data["items"]
        if len(items) > 1:
            shared_counts = [item["shared_tags_count"] for item in items]
            assert shared_counts == sorted(shared_counts, reverse=True)

    async def test_get_related_by_tags_contains_shared_tags_count(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """응답에 shared_tags_count 필드 포함"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/related-by-tags")

        # Then
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            for item in data["items"]:
                assert "shared_tags_count" in item
                assert isinstance(item["shared_tags_count"], int)
                assert item["shared_tags_count"] > 0

    async def test_get_related_by_tags_with_limit(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """limit 파라미터 동작"""
        # When
        response = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/related-by-tags",
            params={"limit": 3},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3

    async def test_get_related_by_tags_pagination(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """커서 기반 페이지네이션"""
        # Given: 첫 페이지
        response1 = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/related-by-tags",
            params={"limit": 2},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # When: 다음 페이지가 있으면
        if data1["has_more"] and data1["next_cursor"]:
            response2 = await client.get(
                f"/api/v1/recipes/{sample_recipe.id}/related-by-tags",
                params={"limit": 2, "cursor": data1["next_cursor"]},
            )

            # Then: 중복 없음
            assert response2.status_code == 200
            data2 = response2.json()

            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert ids1.isdisjoint(ids2)

    async def test_get_related_by_tags_not_found(
        self,
        client: AsyncClient,
    ):
        """존재하지 않는 레시피 ID"""
        # When
        response = await client.get("/api/v1/recipes/non-existent-id/related-by-tags")

        # Then
        assert response.status_code == 404

    async def test_get_related_by_tags_no_tags(
        self,
        client: AsyncClient,
        recipe_with_no_tags: Recipe,
    ):
        """태그 없는 레시피"""
        # When
        response = await client.get(f"/api/v1/recipes/{recipe_with_no_tags.id}/related-by-tags")

        # Then: 빈 결과 반환
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False

    async def test_get_related_by_tags_required_fields(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """응답 필수 필드 확인"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/related-by-tags")

        # Then
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            item = data["items"][0]
            required_fields = ["id", "title", "shared_tags_count", "shared_tags"]
            for field in required_fields:
                assert field in item

    async def test_get_related_by_tags_includes_shared_tags_list(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """공유 태그 목록 포함"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/related-by-tags")

        # Then
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            for item in data["items"]:
                assert "shared_tags" in item
                assert isinstance(item["shared_tags"], list)
                # shared_tags_count와 shared_tags 목록 개수 일치
                assert len(item["shared_tags"]) == item["shared_tags_count"]
