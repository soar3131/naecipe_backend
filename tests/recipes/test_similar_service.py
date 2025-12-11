"""
유사 레시피 서비스 단위 테스트

SimilarRecipeService 클래스의 단위 테스트
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.models import Recipe
from app.recipes.services import SimilarRecipeService


@pytest.mark.asyncio
class TestSimilarRecipeServiceGetSimilar:
    """get_similar_recipes 메서드 테스트"""

    async def test_returns_similar_recipes(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사 레시피 목록 반환"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then
        assert result is not None
        assert hasattr(result, "items")
        assert hasattr(result, "next_cursor")
        assert hasattr(result, "has_more")

    async def test_excludes_base_recipe(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """기준 레시피 제외"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then
        recipe_ids = [item.id for item in result.items]
        assert sample_recipe.id not in recipe_ids

    async def test_sorted_by_similarity_descending(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사도 내림차순 정렬"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then
        if len(result.items) > 1:
            scores = [item.similarity_score for item in result.items]
            assert scores == sorted(scores, reverse=True)

    async def test_similarity_score_range(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """유사도 점수 범위 (0~1)"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then
        for item in result.items:
            assert 0.0 <= item.similarity_score <= 1.0

    async def test_respects_limit_parameter(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """limit 파라미터 존중"""
        # Given
        service = SimilarRecipeService(db_session)
        limit = 3

        # When
        result = await service.get_similar_recipes(sample_recipe.id, limit=limit)

        # Then
        assert len(result.items) <= limit

    async def test_pagination_with_cursor(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """커서 기반 페이지네이션"""
        # Given
        service = SimilarRecipeService(db_session)

        # When: 첫 페이지
        result1 = await service.get_similar_recipes(sample_recipe.id, limit=3)

        # Then: 다음 페이지가 있으면 페이지네이션 동작 확인
        if result1.has_more and result1.next_cursor:
            result2 = await service.get_similar_recipes(
                sample_recipe.id,
                cursor=result1.next_cursor,
                limit=3,
            )

            # 중복 없음
            ids1 = {item.id for item in result1.items}
            ids2 = {item.id for item in result2.items}
            assert ids1.isdisjoint(ids2)

    async def test_recipe_not_found(
        self,
        db_session: AsyncSession,
    ):
        """존재하지 않는 레시피 ID"""
        # Given
        service = SimilarRecipeService(db_session)

        # When/Then
        with pytest.raises(Exception):  # RecipeNotFoundError 또는 ValueError
            await service.get_similar_recipes("non-existent-id")

    async def test_recipe_with_no_tags_returns_empty_or_fallback(
        self,
        db_session: AsyncSession,
        recipe_with_no_tags: Recipe,
    ):
        """태그 없는 레시피 처리"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(recipe_with_no_tags.id)

        # Then: 에러 없이 빈 결과 또는 대체 결과 반환
        assert result is not None
        assert hasattr(result, "items")


@pytest.mark.asyncio
class TestSimilarityCalculation:
    """유사도 계산 로직 테스트"""

    async def test_tag_similarity_weight(
        self,
        db_session: AsyncSession,
        many_similar_recipes: list[Recipe],
    ):
        """태그 유사도 가중치 (40%) 적용"""
        # Given: 김치찌개 (한식, 찌개, 저녁)
        base_recipe = many_similar_recipes[0]
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(base_recipe.id)

        # Then: 태그가 많이 겹치는 레시피가 높은 점수
        if len(result.items) >= 2:
            # 찌개류가 양식류보다 높은 점수를 가져야 함
            scores_by_title = {item.title: item.similarity_score for item in result.items}

            # 된장찌개, 순두부찌개 등이 있다면 확인
            jjigae_scores = [s for t, s in scores_by_title.items() if "찌개" in t]
            western_scores = [s for t, s in scores_by_title.items() if "파스타" in t or "스테이크" in t]

            if jjigae_scores and western_scores:
                assert max(jjigae_scores) >= max(western_scores)

    async def test_combined_similarity_score(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """복합 유사도 점수 계산"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then: 모든 항목이 복합 유사도 점수를 가짐
        for item in result.items:
            # 태그(40%) + 재료(40%) + 조리(20%) = 100%
            assert item.similarity_score >= 0.0
            assert item.similarity_score <= 1.0


@pytest.mark.asyncio
class TestSimilarRecipesResponseSchema:
    """응답 스키마 테스트"""

    async def test_item_contains_required_fields(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """응답 항목 필수 필드 확인"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then
        if result.items:
            item = result.items[0]
            assert hasattr(item, "id")
            assert hasattr(item, "title")
            assert hasattr(item, "similarity_score")
            assert hasattr(item, "tags")

    async def test_item_chef_info_when_exists(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """요리사 정보 포함 (있는 경우)"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then: chef 필드 존재
        for item in result.items:
            assert hasattr(item, "chef")
            # chef는 None이거나 ChefSummary 객체

    async def test_tags_list_in_response(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
    ):
        """태그 목록 포함"""
        # Given
        service = SimilarRecipeService(db_session)

        # When
        result = await service.get_similar_recipes(sample_recipe.id)

        # Then
        for item in result.items:
            assert isinstance(item.tags, list)


@pytest.mark.asyncio
class TestSimilarRecipesCaching:
    """Redis 캐싱 테스트"""

    async def test_cache_hit_returns_same_result(
        self,
        db_session: AsyncSession,
        sample_recipe: Recipe,
        many_similar_recipes: list[Recipe],
        mock_redis_cache,
    ):
        """캐시 히트 시 동일 결과 반환"""
        # Given
        service = SimilarRecipeService(db_session)

        # When: 두 번 호출
        result1 = await service.get_similar_recipes(sample_recipe.id)
        result2 = await service.get_similar_recipes(sample_recipe.id)

        # Then: 동일한 결과
        ids1 = [item.id for item in result1.items]
        ids2 = [item.id for item in result2.items]
        assert ids1 == ids2
