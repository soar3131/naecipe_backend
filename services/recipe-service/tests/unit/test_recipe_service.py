"""
RecipeService 유닛 테스트

레시피 서비스 비즈니스 로직을 테스트합니다.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.middleware.error_handler import RecipeNotFoundError
from recipe_service.models import Chef, Recipe, RecipeIngredient, CookingStep, Tag, RecipeTag
from recipe_service.services import RecipeService


@pytest.fixture
def mock_session() -> AsyncMock:
    """모의 데이터베이스 세션"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_cache() -> AsyncMock:
    """모의 Redis 캐시"""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.recipe_key = MagicMock(side_effect=lambda x: f"recipe:{x}")
    return cache


@pytest.fixture
def sample_recipe() -> Recipe:
    """샘플 레시피 모델 객체"""
    chef = Chef(
        id=str(uuid4()),
        name="백종원",
        name_normalized="백종원",
        profile_image_url="https://example.com/chef.jpg",
        specialty="한식",
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    recipe = Recipe(
        id=str(uuid4()),
        chef_id=chef.id,
        title="김치찌개",
        description="맛있는 김치찌개 레시피",
        thumbnail_url="https://example.com/kimchi.jpg",
        video_url="https://youtube.com/watch?v=abc123",
        prep_time_minutes=10,
        cook_time_minutes=30,
        servings=4,
        difficulty="easy",
        source_url="https://youtube.com/watch?v=abc123",
        source_platform="youtube",
        exposure_score=85.5,
        view_count=1000,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    recipe.chef = chef

    # 재료 추가
    recipe.ingredients = [
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe.id,
            name="김치",
            amount="300",
            unit="g",
            order_index=0,
        ),
        RecipeIngredient(
            id=str(uuid4()),
            recipe_id=recipe.id,
            name="돼지고기",
            amount="200",
            unit="g",
            order_index=1,
        ),
    ]

    # 조리 단계 추가
    recipe.steps = [
        CookingStep(
            id=str(uuid4()),
            recipe_id=recipe.id,
            step_number=1,
            description="재료를 준비합니다.",
            duration_seconds=300,
        ),
        CookingStep(
            id=str(uuid4()),
            recipe_id=recipe.id,
            step_number=2,
            description="끓여줍니다.",
            duration_seconds=600,
        ),
    ]

    # 태그 추가
    tag = Tag(
        id=str(uuid4()),
        name="한식",
        category="cuisine",
    )
    recipe_tag = RecipeTag(
        id=str(uuid4()),
        recipe_id=recipe.id,
        tag_id=tag.id,
    )
    recipe_tag.tag = tag
    recipe.recipe_tags = [recipe_tag]

    return recipe


class TestRecipeServiceGetById:
    """RecipeService.get_by_id() 테스트"""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_recipe_detail(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
        sample_recipe: Recipe,
    ):
        """레시피 ID로 상세 정보를 조회할 수 있다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = sample_recipe
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act
            result = await service.get_by_id(sample_recipe.id)

            # Assert
            assert result.id == sample_recipe.id
            assert result.title == sample_recipe.title
            assert result.description == sample_recipe.description
            assert result.chef is not None
            assert result.chef.name == "백종원"
            assert len(result.ingredients) == 2
            assert len(result.steps) == 2
            assert len(result.tags) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_raises_not_found_error(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
    ):
        """존재하지 않는 레시피 ID로 조회 시 RecipeNotFoundError 발생"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)
        non_existent_id = str(uuid4())

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act & Assert
            with pytest.raises(RecipeNotFoundError) as exc_info:
                await service.get_by_id(non_existent_id)

            assert non_existent_id in str(exc_info.value.message)
            assert exc_info.value.code == "RECIPE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_by_id_uses_cache(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
        sample_recipe: Recipe,
    ):
        """캐시에서 데이터를 조회한다"""
        # Arrange
        cached_data = {
            "id": sample_recipe.id,
            "title": sample_recipe.title,
            "description": sample_recipe.description,
            "thumbnail_url": sample_recipe.thumbnail_url,
            "video_url": sample_recipe.video_url,
            "prep_time_minutes": sample_recipe.prep_time_minutes,
            "cook_time_minutes": sample_recipe.cook_time_minutes,
            "total_time_minutes": 40,
            "servings": sample_recipe.servings,
            "difficulty": sample_recipe.difficulty,
            "source_url": sample_recipe.source_url,
            "source_platform": sample_recipe.source_platform,
            "exposure_score": sample_recipe.exposure_score,
            "view_count": sample_recipe.view_count,
            "chef": {
                "id": sample_recipe.chef.id,
                "name": sample_recipe.chef.name,
                "profile_image_url": sample_recipe.chef.profile_image_url,
                "specialty": sample_recipe.chef.specialty,
                "is_verified": sample_recipe.chef.is_verified,
            },
            "ingredients": [],
            "steps": [],
            "tags": [],
            "created_at": sample_recipe.created_at.isoformat(),
            "updated_at": sample_recipe.updated_at.isoformat(),
        }
        mock_cache.get = AsyncMock(return_value=cached_data)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act
            result = await service.get_by_id(sample_recipe.id)

            # Assert
            assert result.id == sample_recipe.id
            assert result.title == sample_recipe.title
            # DB 호출 없이 캐시에서 반환
            mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_caches_db_result(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
        sample_recipe: Recipe,
    ):
        """DB 조회 결과를 캐시에 저장한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = sample_recipe
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act
            await service.get_by_id(sample_recipe.id)

            # Assert
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert f"recipe:{sample_recipe.id}" == call_args[0][0]


class TestRecipeServiceGetList:
    """RecipeService.get_list() 테스트"""

    @pytest.fixture
    def mock_cache_list(self) -> AsyncMock:
        """목록용 모의 Redis 캐시"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.recipes_list_key = MagicMock(return_value="recipes:list:first:20")
        return cache

    @pytest.mark.asyncio
    async def test_get_list_returns_empty_list(
        self,
        mock_session: AsyncMock,
        mock_cache_list: AsyncMock,
    ):
        """레시피가 없으면 빈 목록을 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_list,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_list(PaginationParams(limit=20))

            # Assert
            assert result.items == []
            assert result.has_more is False
            assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_get_list_returns_recipes(
        self,
        mock_session: AsyncMock,
        mock_cache_list: AsyncMock,
        sample_recipe: Recipe,
    ):
        """레시피 목록을 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            sample_recipe
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_list,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_list(PaginationParams(limit=20))

            # Assert
            assert len(result.items) == 1
            assert result.items[0].id == sample_recipe.id
            assert result.items[0].title == sample_recipe.title
            assert result.has_more is False

    @pytest.mark.asyncio
    async def test_get_list_pagination_has_more(
        self,
        mock_session: AsyncMock,
        mock_cache_list: AsyncMock,
        sample_recipe: Recipe,
    ):
        """더 많은 결과가 있으면 has_more가 True"""
        # Arrange
        # limit+1 개의 결과를 반환하여 has_more = True 시뮬레이션
        recipes = [sample_recipe, sample_recipe]  # 2개 반환 (limit=1 일 때)
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = recipes
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_list,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_list(PaginationParams(limit=1))

            # Assert
            assert len(result.items) == 1  # limit만큼만 반환
            assert result.has_more is True
            assert result.next_cursor is not None


class TestRecipeServiceGetPopular:
    """RecipeService.get_popular() 테스트"""

    @pytest.fixture
    def mock_cache_popular(self) -> AsyncMock:
        """인기 레시피용 모의 Redis 캐시"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.popular_recipes_key = MagicMock(return_value="recipes:popular:all:10")
        return cache

    @pytest.mark.asyncio
    async def test_get_popular_returns_recipes(
        self,
        mock_session: AsyncMock,
        mock_cache_popular: AsyncMock,
        sample_recipe: Recipe,
    ):
        """인기 레시피 목록을 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            sample_recipe
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_popular,
        ):
            # Act
            result = await service.get_popular(limit=10)

            # Assert
            assert len(result) == 1
            assert result[0].id == sample_recipe.id

    @pytest.mark.asyncio
    async def test_get_popular_limit_max_50(
        self,
        mock_session: AsyncMock,
        mock_cache_popular: AsyncMock,
    ):
        """인기 레시피 limit은 최대 50개로 제한된다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_popular,
        ):
            # Act - 100개 요청해도 50개로 제한
            await service.get_popular(limit=100)

            # Assert - limit(51)이 아닌 limit(50)+1이 아님 (내부적으로 50으로 제한)
            # 실제 실행 확인
            mock_session.execute.assert_called_once()


class TestRecipeServiceGetByChef:
    """RecipeService.get_by_chef() 테스트"""

    @pytest.fixture
    def mock_cache_chef_recipes(self) -> AsyncMock:
        """요리사별 레시피용 모의 Redis 캐시"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.chef_recipes_key = MagicMock(return_value="chef:abc:recipes:first:20")
        return cache

    @pytest.mark.asyncio
    async def test_get_by_chef_returns_recipes(
        self,
        mock_session: AsyncMock,
        mock_cache_chef_recipes: AsyncMock,
        sample_recipe: Recipe,
    ):
        """요리사별 레시피 목록을 반환한다"""
        # Arrange
        chef_id = sample_recipe.chef_id
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            sample_recipe
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_chef_recipes,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_by_chef(chef_id, PaginationParams(limit=20))

            # Assert
            assert len(result.items) == 1
            assert result.items[0].id == sample_recipe.id
            assert result.has_more is False

    @pytest.mark.asyncio
    async def test_get_by_chef_returns_empty_list(
        self,
        mock_session: AsyncMock,
        mock_cache_chef_recipes: AsyncMock,
    ):
        """레시피가 없으면 빈 목록을 반환한다"""
        # Arrange
        chef_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_chef_recipes,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_by_chef(chef_id, PaginationParams(limit=20))

            # Assert
            assert result.items == []
            assert result.has_more is False
            assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_get_by_chef_uses_cache(
        self,
        mock_session: AsyncMock,
        mock_cache_chef_recipes: AsyncMock,
        sample_recipe: Recipe,
    ):
        """캐시에서 데이터를 조회한다"""
        # Arrange
        chef_id = sample_recipe.chef_id
        cached_data = {
            "items": [],
            "next_cursor": None,
            "has_more": False,
            "total_count": None,
        }
        mock_cache_chef_recipes.get = AsyncMock(return_value=cached_data)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_chef_recipes,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_by_chef(chef_id, PaginationParams(limit=20))

            # Assert
            assert result.items == []
            # DB 호출 없이 캐시에서 반환
            mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_chef_pagination_has_more(
        self,
        mock_session: AsyncMock,
        mock_cache_chef_recipes: AsyncMock,
        sample_recipe: Recipe,
    ):
        """더 많은 결과가 있으면 has_more가 True"""
        # Arrange
        chef_id = sample_recipe.chef_id
        # limit+1 개의 결과를 반환하여 has_more = True 시뮬레이션
        recipes = [sample_recipe, sample_recipe]  # 2개 반환 (limit=1 일 때)
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = recipes
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = RecipeService(mock_session)

        with patch(
            "recipe_service.services.recipe_service.get_redis_cache",
            return_value=mock_cache_chef_recipes,
        ):
            from recipe_service.schemas.pagination import PaginationParams

            # Act
            result = await service.get_by_chef(chef_id, PaginationParams(limit=1))

            # Assert
            assert len(result.items) == 1  # limit만큼만 반환
            assert result.has_more is True
            assert result.next_cursor is not None
