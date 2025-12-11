"""
같은 요리사 레시피 API 통합 테스트

GET /api/v1/recipes/{recipe_id}/same-chef 엔드포인트 테스트
"""

import pytest
from httpx import AsyncClient

from app.recipes.models import Chef, Recipe


@pytest.mark.asyncio
class TestSameChefRecipesAPI:
    """같은 요리사 레시피 API 통합 테스트"""

    async def test_get_same_chef_recipes_success(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """같은 요리사 레시피 조회 성공"""
        # Given: 요리사가 있는 레시피
        recipe_id = sample_recipe.id

        # When
        response = await client.get(f"/api/v1/recipes/{recipe_id}/same-chef")

        # Then
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "next_cursor" in data
        assert "has_more" in data

    async def test_get_same_chef_recipes_excludes_base_recipe(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """기준 레시피는 결과에서 제외"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/same-chef")

        # Then
        assert response.status_code == 200
        data = response.json()

        recipe_ids = [item["id"] for item in data["items"]]
        assert sample_recipe.id not in recipe_ids

    async def test_get_same_chef_recipes_sorted_by_view_count(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """조회수 내림차순 정렬"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/same-chef")

        # Then
        assert response.status_code == 200
        data = response.json()

        items = data["items"]
        if len(items) > 1:
            view_counts = [item["view_count"] for item in items]
            assert view_counts == sorted(view_counts, reverse=True)

    async def test_get_same_chef_recipes_contains_view_count(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """응답에 view_count 필드 포함"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/same-chef")

        # Then
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            for item in data["items"]:
                assert "view_count" in item
                assert isinstance(item["view_count"], int)

    async def test_get_same_chef_recipes_with_limit(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """limit 파라미터 동작"""
        # When
        response = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/same-chef",
            params={"limit": 3},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3

    async def test_get_same_chef_recipes_pagination(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """커서 기반 페이지네이션"""
        # Given: 첫 페이지
        response1 = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/same-chef",
            params={"limit": 2},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # When: 다음 페이지가 있으면
        if data1["has_more"] and data1["next_cursor"]:
            response2 = await client.get(
                f"/api/v1/recipes/{sample_recipe.id}/same-chef",
                params={"limit": 2, "cursor": data1["next_cursor"]},
            )

            # Then: 중복 없음
            assert response2.status_code == 200
            data2 = response2.json()

            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert ids1.isdisjoint(ids2)

    async def test_get_same_chef_recipes_not_found(
        self,
        client: AsyncClient,
    ):
        """존재하지 않는 레시피 ID"""
        # When
        response = await client.get("/api/v1/recipes/non-existent-id/same-chef")

        # Then
        assert response.status_code == 404

    async def test_get_same_chef_recipes_no_chef(
        self,
        client: AsyncClient,
        recipe_without_chef: Recipe,
    ):
        """요리사 없는 레시피"""
        # When
        response = await client.get(f"/api/v1/recipes/{recipe_without_chef.id}/same-chef")

        # Then: 빈 결과 반환 (에러 아님)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False

    async def test_get_same_chef_recipes_required_fields(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """응답 필수 필드 확인"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/same-chef")

        # Then
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            item = data["items"][0]
            required_fields = ["id", "title", "view_count"]
            for field in required_fields:
                assert field in item
