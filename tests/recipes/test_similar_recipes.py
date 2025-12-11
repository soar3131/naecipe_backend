"""
유사 레시피 API 통합 테스트

GET /api/v1/recipes/{recipe_id}/similar 엔드포인트 테스트
"""

import pytest
from httpx import AsyncClient

from app.recipes.models import Recipe


@pytest.mark.asyncio
class TestSimilarRecipesAPI:
    """유사 레시피 API 통합 테스트"""

    async def test_get_similar_recipes_success(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사 레시피 조회 성공"""
        # Given: 기준 레시피와 유사 레시피들이 존재
        recipe_id = sample_recipe.id

        # When: 유사 레시피 조회 API 호출
        response = await client.get(f"/api/v1/recipes/{recipe_id}/similar")

        # Then: 200 OK, 유사 레시피 목록 반환
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "next_cursor" in data
        assert "has_more" in data
        assert isinstance(data["items"], list)

    async def test_get_similar_recipes_with_similarity_score(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사 레시피 응답에 유사도 점수 포함"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/similar")

        # Then
        assert response.status_code == 200
        data = response.json()

        # 결과가 있으면 유사도 점수 확인
        if data["items"]:
            for item in data["items"]:
                assert "similarity_score" in item
                assert 0.0 <= item["similarity_score"] <= 1.0

    async def test_get_similar_recipes_sorted_by_similarity(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사 레시피가 유사도 내림차순으로 정렬됨"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/similar")

        # Then
        assert response.status_code == 200
        data = response.json()

        items = data["items"]
        if len(items) > 1:
            scores = [item["similarity_score"] for item in items]
            assert scores == sorted(scores, reverse=True)

    async def test_get_similar_recipes_excludes_base_recipe(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """기준 레시피는 결과에서 제외됨"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/similar")

        # Then
        assert response.status_code == 200
        data = response.json()

        recipe_ids = [item["id"] for item in data["items"]]
        assert sample_recipe.id not in recipe_ids

    async def test_get_similar_recipes_with_limit(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """limit 파라미터로 결과 개수 제한"""
        # When
        response = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/similar",
            params={"limit": 5},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

    async def test_get_similar_recipes_pagination(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """커서 기반 페이지네이션 동작"""
        # Given: 첫 페이지 조회
        response1 = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/similar",
            params={"limit": 3},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # When: 다음 페이지가 있으면 다음 페이지 조회
        if data1["has_more"] and data1["next_cursor"]:
            response2 = await client.get(
                f"/api/v1/recipes/{sample_recipe.id}/similar",
                params={"limit": 3, "cursor": data1["next_cursor"]},
            )

            # Then: 다음 페이지 정상 반환, 중복 없음
            assert response2.status_code == 200
            data2 = response2.json()

            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert ids1.isdisjoint(ids2)

    async def test_get_similar_recipes_contains_required_fields(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """응답 항목에 필수 필드 포함"""
        # When
        response = await client.get(f"/api/v1/recipes/{sample_recipe.id}/similar")

        # Then
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            item = data["items"][0]
            required_fields = ["id", "title", "similarity_score"]
            for field in required_fields:
                assert field in item

    async def test_get_similar_recipes_not_found(
        self,
        client: AsyncClient,
    ):
        """존재하지 않는 레시피 ID로 조회 시 404"""
        # When
        response = await client.get("/api/v1/recipes/non-existent-id/similar")

        # Then
        assert response.status_code == 404

    async def test_get_similar_recipes_no_tags(
        self,
        client: AsyncClient,
        recipe_with_no_tags: Recipe,
    ):
        """태그 없는 레시피의 유사 레시피 조회 (빈 결과 허용)"""
        # When
        response = await client.get(f"/api/v1/recipes/{recipe_with_no_tags.id}/similar")

        # Then: 에러 없이 빈 결과 반환
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_get_similar_recipes_limit_validation(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
    ):
        """limit 파라미터 유효성 검증"""
        # When: 잘못된 limit 값
        response = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/similar",
            params={"limit": 100},  # max 50
        )

        # Then: 422 또는 범위 내 값으로 조정
        assert response.status_code in [200, 422]

    async def test_get_similar_recipes_invalid_cursor(
        self,
        client: AsyncClient,
        sample_recipe: Recipe,
    ):
        """잘못된 커서 형식 처리"""
        # When
        response = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}/similar",
            params={"cursor": "invalid-cursor-format"},
        )

        # Then: 400 또는 첫 페이지 반환
        assert response.status_code in [200, 400]


@pytest.mark.asyncio
class TestSimilarRecipesSimilarityCalculation:
    """유사도 계산 로직 테스트"""

    async def test_tag_similarity_affects_score(
        self,
        client: AsyncClient,
        many_similar_recipes: list[Recipe],
    ):
        """태그 겹침이 유사도 점수에 반영됨"""
        # Given: 기준 레시피 (김치찌개 - 한식, 찌개, 저녁)
        base_recipe = many_similar_recipes[0]

        # When
        response = await client.get(f"/api/v1/recipes/{base_recipe.id}/similar")

        # Then: 태그가 많이 겹치는 레시피가 상위에 위치
        assert response.status_code == 200
        data = response.json()

        # 찌개 태그가 있는 레시피들이 상위에 있어야 함
        if len(data["items"]) > 3:
            top_items = data["items"][:3]
            # 최소 하나는 찌개 관련 태그를 가져야 함
            top_titles = [item["title"] for item in top_items]
            assert any("찌개" in title for title in top_titles)

    async def test_higher_similarity_for_same_tags(
        self,
        client: AsyncClient,
        many_similar_recipes: list[Recipe],
    ):
        """동일 태그를 공유하는 레시피가 더 높은 유사도"""
        # Given: 김치찌개 (한식, 찌개, 저녁)
        base_recipe = many_similar_recipes[0]

        # When
        response = await client.get(f"/api/v1/recipes/{base_recipe.id}/similar")

        # Then
        assert response.status_code == 200
        data = response.json()

        # 찌개류가 양식보다 상위에 있어야 함
        if len(data["items"]) >= 5:
            jjigae_indices = []
            western_indices = []

            for i, item in enumerate(data["items"]):
                title = item["title"]
                if "찌개" in title:
                    jjigae_indices.append(i)
                elif "파스타" in title or "스테이크" in title:
                    western_indices.append(i)

            # 찌개류가 있다면 양식보다 상위에 있어야 함
            if jjigae_indices and western_indices:
                assert min(jjigae_indices) < min(western_indices)
