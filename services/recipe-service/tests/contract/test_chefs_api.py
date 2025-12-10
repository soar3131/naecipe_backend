"""
요리사 API 계약 테스트

API 응답 스키마가 명세와 일치하는지 검증합니다.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from recipe_service.main import app
from recipe_service.schemas import (
    ChefDetail,
    ChefListItem,
    ChefListResponse,
    ChefPlatformSchema,
    RecipeListItem,
    RecipeListResponse,
)


@pytest.fixture
def client():
    """테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def sample_chef_detail() -> ChefDetail:
    """샘플 요리사 상세 정보"""
    return ChefDetail(
        id=str(uuid4()),
        name="백종원",
        profile_image_url="https://example.com/chef.jpg",
        bio="유명 요리연구가입니다.",
        specialty="한식",
        recipe_count=150,
        total_views=1000000,
        avg_rating=4.8,
        is_verified=True,
        platforms=[
            ChefPlatformSchema(
                id=str(uuid4()),
                platform="youtube",
                platform_url="https://youtube.com/@baek",
                platform_id="UC1234",
            )
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_chef_list_item() -> ChefListItem:
    """샘플 요리사 목록 아이템"""
    return ChefListItem(
        id=str(uuid4()),
        name="백종원",
        profile_image_url="https://example.com/chef.jpg",
        specialty="한식",
        recipe_count=150,
        is_verified=True,
    )


class TestGetChefContract:
    """GET /chefs/{chef_id} 계약 테스트"""

    def test_chef_detail_response_schema(
        self,
        client: TestClient,
        sample_chef_detail: ChefDetail,
    ):
        """응답 스키마가 ChefDetail과 일치한다"""
        chef_id = sample_chef_detail.id

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(return_value=sample_chef_detail)
            mock_get_service.return_value = mock_service

            response = client.get(f"/chefs/{chef_id}")

            assert response.status_code == 200
            data = response.json()

            # 필수 필드 검증
            assert "id" in data
            assert "name" in data
            assert "profile_image_url" in data
            assert "bio" in data
            assert "specialty" in data
            assert "recipe_count" in data
            assert "total_views" in data
            assert "avg_rating" in data
            assert "is_verified" in data
            assert "platforms" in data
            assert "created_at" in data
            assert "updated_at" in data

            # 타입 검증
            assert isinstance(data["id"], str)
            assert isinstance(data["name"], str)
            assert isinstance(data["recipe_count"], int)
            assert isinstance(data["is_verified"], bool)
            assert isinstance(data["platforms"], list)

    def test_chef_not_found_returns_404(self, client: TestClient):
        """존재하지 않는 요리사는 404를 반환한다"""
        chef_id = str(uuid4())

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            from recipe_service.middleware.error_handler import ChefNotFoundError

            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(
                side_effect=ChefNotFoundError(chef_id)
            )
            mock_get_service.return_value = mock_service

            response = client.get(f"/chefs/{chef_id}")

            assert response.status_code == 404
            data = response.json()
            assert "code" in data
            assert data["code"] == "CHEF_NOT_FOUND"


class TestGetChefsListContract:
    """GET /chefs 계약 테스트"""

    def test_chefs_list_response_schema(
        self,
        client: TestClient,
        sample_chef_list_item: ChefListItem,
    ):
        """응답 스키마가 ChefListResponse와 일치한다"""
        response_data = ChefListResponse(
            items=[sample_chef_list_item],
            next_cursor=None,
            has_more=False,
            total_count=None,
        )

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(return_value=response_data)
            mock_get_service.return_value = mock_service

            response = client.get("/chefs")

            assert response.status_code == 200
            data = response.json()

            # 필수 필드 검증
            assert "items" in data
            assert "has_more" in data
            assert "next_cursor" in data

            # items 필드 검증
            assert isinstance(data["items"], list)
            if data["items"]:
                item = data["items"][0]
                assert "id" in item
                assert "name" in item
                assert "profile_image_url" in item
                assert "specialty" in item
                assert "recipe_count" in item
                assert "is_verified" in item

    def test_chefs_list_with_pagination(
        self,
        client: TestClient,
        sample_chef_list_item: ChefListItem,
    ):
        """페이지네이션 파라미터가 올바르게 처리된다"""
        response_data = ChefListResponse(
            items=[sample_chef_list_item],
            next_cursor="some_cursor",
            has_more=True,
            total_count=None,
        )

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(return_value=response_data)
            mock_get_service.return_value = mock_service

            response = client.get("/chefs?limit=10&cursor=prev_cursor")

            assert response.status_code == 200
            data = response.json()
            assert data["has_more"] is True
            assert data["next_cursor"] == "some_cursor"

    def test_chefs_list_with_filters(
        self,
        client: TestClient,
        sample_chef_list_item: ChefListItem,
    ):
        """필터 파라미터가 올바르게 처리된다"""
        response_data = ChefListResponse(
            items=[sample_chef_list_item],
            next_cursor=None,
            has_more=False,
            total_count=None,
        )

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(return_value=response_data)
            mock_get_service.return_value = mock_service

            response = client.get("/chefs?specialty=한식&is_verified=true")

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1


class TestGetPopularChefsContract:
    """GET /chefs/popular 계약 테스트"""

    def test_popular_chefs_response_schema(
        self,
        client: TestClient,
        sample_chef_list_item: ChefListItem,
    ):
        """응답 스키마가 list[ChefListItem]과 일치한다"""
        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_popular = AsyncMock(return_value=[sample_chef_list_item])
            mock_get_service.return_value = mock_service

            response = client.get("/chefs/popular")

            assert response.status_code == 200
            data = response.json()

            # 리스트 검증
            assert isinstance(data, list)
            if data:
                item = data[0]
                assert "id" in item
                assert "name" in item
                assert "recipe_count" in item
                assert "is_verified" in item

    def test_popular_chefs_with_limit(
        self,
        client: TestClient,
        sample_chef_list_item: ChefListItem,
    ):
        """limit 파라미터가 올바르게 처리된다"""
        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_popular = AsyncMock(return_value=[sample_chef_list_item])
            mock_get_service.return_value = mock_service

            response = client.get("/chefs/popular?limit=5")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestGetChefRecipesContract:
    """GET /chefs/{chef_id}/recipes 계약 테스트"""

    @pytest.fixture
    def sample_recipe_list_item(self) -> RecipeListItem:
        """샘플 레시피 목록 아이템"""
        from recipe_service.schemas import ChefSummary

        return RecipeListItem(
            id=str(uuid4()),
            title="김치찌개",
            description="맛있는 김치찌개",
            thumbnail_url="https://example.com/kimchi.jpg",
            prep_time_minutes=10,
            cook_time_minutes=30,
            difficulty="easy",
            exposure_score=85.5,
            chef=ChefSummary(
                id=str(uuid4()),
                name="백종원",
                profile_image_url="https://example.com/chef.jpg",
                specialty="한식",
                is_verified=True,
            ),
            tags=[],
            created_at=datetime.now(timezone.utc),
        )

    def test_chef_recipes_response_schema(
        self,
        client: TestClient,
        sample_chef_detail: ChefDetail,
        sample_recipe_list_item: RecipeListItem,
    ):
        """응답 스키마가 RecipeListResponse와 일치한다"""
        chef_id = sample_chef_detail.id
        response_data = RecipeListResponse(
            items=[sample_recipe_list_item],
            next_cursor=None,
            has_more=False,
            total_count=None,
        )

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_chef_service, patch(
            "recipe_service.api.chefs.get_recipe_service"
        ) as mock_get_recipe_service:
            # Chef 서비스 모킹
            mock_chef_service = AsyncMock()
            mock_chef_service.get_by_id = AsyncMock(return_value=sample_chef_detail)
            mock_get_chef_service.return_value = mock_chef_service

            # Recipe 서비스 모킹
            mock_recipe_service = AsyncMock()
            mock_recipe_service.get_by_chef = AsyncMock(return_value=response_data)
            mock_get_recipe_service.return_value = mock_recipe_service

            response = client.get(f"/chefs/{chef_id}/recipes")

            assert response.status_code == 200
            data = response.json()

            # 필수 필드 검증
            assert "items" in data
            assert "has_more" in data
            assert "next_cursor" in data

            # items 필드 검증
            if data["items"]:
                item = data["items"][0]
                assert "id" in item
                assert "title" in item
                assert "thumbnail_url" in item
                assert "difficulty" in item

    def test_chef_recipes_not_found(
        self,
        client: TestClient,
    ):
        """존재하지 않는 요리사의 레시피 조회 시 404 반환"""
        chef_id = str(uuid4())

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_chef_service:
            from recipe_service.middleware.error_handler import ChefNotFoundError

            mock_chef_service = AsyncMock()
            mock_chef_service.get_by_id = AsyncMock(
                side_effect=ChefNotFoundError(chef_id)
            )
            mock_get_chef_service.return_value = mock_chef_service

            response = client.get(f"/chefs/{chef_id}/recipes")

            assert response.status_code == 404
