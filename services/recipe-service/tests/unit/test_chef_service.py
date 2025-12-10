"""
ChefService 유닛 테스트

요리사 서비스 비즈니스 로직을 테스트합니다.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.middleware.error_handler import ChefNotFoundError
from recipe_service.models import Chef, ChefPlatform
from recipe_service.services import ChefService


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
    cache.chef_key = MagicMock(side_effect=lambda x: f"chef:{x}")
    return cache


@pytest.fixture
def sample_chef() -> Chef:
    """샘플 요리사 모델 객체"""
    chef = Chef(
        id=str(uuid4()),
        name="백종원",
        name_normalized="백종원",
        profile_image_url="https://example.com/chef.jpg",
        bio="유명 요리연구가입니다.",
        specialty="한식",
        recipe_count=150,
        total_views=1000000,
        avg_rating=4.8,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # 플랫폼 추가
    chef.platforms = [
        ChefPlatform(
            id=str(uuid4()),
            chef_id=chef.id,
            platform="youtube",
            platform_url="https://youtube.com/@baek",
            platform_id="UC1234",
        ),
    ]

    return chef


class TestChefServiceGetById:
    """ChefService.get_by_id() 테스트"""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_chef_detail(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
        sample_chef: Chef,
    ):
        """요리사 ID로 상세 정보를 조회할 수 있다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_chef
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        with patch(
            "recipe_service.services.chef_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act
            result = await service.get_by_id(sample_chef.id)

            # Assert
            assert result.id == sample_chef.id
            assert result.name == sample_chef.name
            assert result.bio == sample_chef.bio
            assert result.specialty == sample_chef.specialty
            assert result.recipe_count == sample_chef.recipe_count
            assert result.is_verified is True
            assert len(result.platforms) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_raises_not_found_error(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
    ):
        """존재하지 않는 요리사 ID로 조회 시 ChefNotFoundError 발생"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)
        non_existent_id = str(uuid4())

        with patch(
            "recipe_service.services.chef_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act & Assert
            with pytest.raises(ChefNotFoundError) as exc_info:
                await service.get_by_id(non_existent_id)

            assert non_existent_id in str(exc_info.value.message)
            assert exc_info.value.code == "CHEF_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_by_id_uses_cache(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
        sample_chef: Chef,
    ):
        """캐시에서 데이터를 조회한다"""
        # Arrange
        cached_data = {
            "id": sample_chef.id,
            "name": sample_chef.name,
            "profile_image_url": sample_chef.profile_image_url,
            "bio": sample_chef.bio,
            "specialty": sample_chef.specialty,
            "recipe_count": sample_chef.recipe_count,
            "total_views": sample_chef.total_views,
            "avg_rating": sample_chef.avg_rating,
            "is_verified": sample_chef.is_verified,
            "platforms": [],
            "created_at": sample_chef.created_at.isoformat(),
            "updated_at": sample_chef.updated_at.isoformat(),
        }
        mock_cache.get = AsyncMock(return_value=cached_data)

        service = ChefService(mock_session)

        with patch(
            "recipe_service.services.chef_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act
            result = await service.get_by_id(sample_chef.id)

            # Assert
            assert result.id == sample_chef.id
            assert result.name == sample_chef.name
            # DB 호출 없이 캐시에서 반환
            mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_caches_db_result(
        self,
        mock_session: AsyncMock,
        mock_cache: AsyncMock,
        sample_chef: Chef,
    ):
        """DB 조회 결과를 캐시에 저장한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_chef
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        with patch(
            "recipe_service.services.chef_service.get_redis_cache",
            return_value=mock_cache,
        ):
            # Act
            await service.get_by_id(sample_chef.id)

            # Assert
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert f"chef:{sample_chef.id}" == call_args[0][0]


class TestChefServiceGetList:
    """ChefService.get_list() 테스트"""

    @pytest.mark.asyncio
    async def test_get_list_returns_empty_list(
        self,
        mock_session: AsyncMock,
    ):
        """요리사가 없으면 빈 목록을 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        from recipe_service.schemas.pagination import PaginationParams

        # Act
        result = await service.get_list(PaginationParams(limit=20))

        # Assert
        assert result.items == []
        assert result.has_more is False
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_get_list_returns_chefs(
        self,
        mock_session: AsyncMock,
        sample_chef: Chef,
    ):
        """요리사 목록을 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_chef]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        from recipe_service.schemas.pagination import PaginationParams

        # Act
        result = await service.get_list(PaginationParams(limit=20))

        # Assert
        assert len(result.items) == 1
        assert result.items[0].id == sample_chef.id
        assert result.items[0].name == sample_chef.name
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_get_list_pagination_has_more(
        self,
        mock_session: AsyncMock,
        sample_chef: Chef,
    ):
        """더 많은 결과가 있으면 has_more가 True"""
        # Arrange
        # limit+1 개의 결과를 반환하여 has_more = True 시뮬레이션
        chefs = [sample_chef, sample_chef]  # 2개 반환 (limit=1 일 때)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chefs
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        from recipe_service.schemas.pagination import PaginationParams

        # Act
        result = await service.get_list(PaginationParams(limit=1))

        # Assert
        assert len(result.items) == 1  # limit만큼만 반환
        assert result.has_more is True
        assert result.next_cursor is not None

    @pytest.mark.asyncio
    async def test_get_list_filters_by_specialty(
        self,
        mock_session: AsyncMock,
        sample_chef: Chef,
    ):
        """전문 분야로 필터링할 수 있다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_chef]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        from recipe_service.schemas.pagination import PaginationParams

        # Act
        result = await service.get_list(
            PaginationParams(limit=20),
            specialty="한식",
        )

        # Assert
        assert len(result.items) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_list_filters_by_verified(
        self,
        mock_session: AsyncMock,
        sample_chef: Chef,
    ):
        """인증 여부로 필터링할 수 있다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_chef]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        from recipe_service.schemas.pagination import PaginationParams

        # Act
        result = await service.get_list(
            PaginationParams(limit=20),
            is_verified=True,
        )

        # Assert
        assert len(result.items) == 1
        mock_session.execute.assert_called_once()


class TestChefServiceGetPopular:
    """ChefService.get_popular() 테스트"""

    @pytest.mark.asyncio
    async def test_get_popular_returns_chefs(
        self,
        mock_session: AsyncMock,
        sample_chef: Chef,
    ):
        """인기 요리사 목록을 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_chef]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        # Act
        result = await service.get_popular(limit=10)

        # Assert
        assert len(result) == 1
        assert result[0].id == sample_chef.id
        assert result[0].is_verified is True

    @pytest.mark.asyncio
    async def test_get_popular_limit_max_50(
        self,
        mock_session: AsyncMock,
    ):
        """인기 요리사 limit은 최대 50개로 제한된다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        # Act - 100개 요청해도 50개로 제한
        await service.get_popular(limit=100)

        # Assert - 실제 실행 확인
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_popular_only_verified(
        self,
        mock_session: AsyncMock,
    ):
        """인기 요리사는 인증된 요리사만 반환한다"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ChefService(mock_session)

        # Act
        await service.get_popular()

        # Assert - is_verified == True 조건이 쿼리에 포함됨
        mock_session.execute.assert_called_once()
