"""
레시피 API 계약 테스트

API 엔드포인트의 요청/응답 스펙을 검증합니다.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from recipe_service.main import app
from recipe_service.schemas import (
    ChefSummary,
    CookingStepSchema,
    IngredientSchema,
    RecipeDetail,
    RecipeListItem,
    RecipeListResponse,
    TagSchema,
)


@pytest.fixture
def client():
    """테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def sample_recipe_id() -> str:
    """샘플 레시피 ID"""
    return str(uuid4())


@pytest.fixture
def sample_chef_id() -> str:
    """샘플 요리사 ID"""
    return str(uuid4())


@pytest.fixture
def sample_chef_summary(sample_chef_id: str) -> ChefSummary:
    """샘플 요리사 요약 정보"""
    return ChefSummary(
        id=sample_chef_id,
        name="백종원",
        profile_image_url="https://example.com/chef.jpg",
        specialty="한식",
        is_verified=True,
    )


@pytest.fixture
def sample_recipe_detail(
    sample_recipe_id: str,
    sample_chef_summary: ChefSummary,
) -> RecipeDetail:
    """샘플 레시피 상세 정보"""
    return RecipeDetail(
        id=sample_recipe_id,
        title="김치찌개",
        description="맛있는 김치찌개 레시피",
        thumbnail_url="https://example.com/kimchi.jpg",
        video_url="https://youtube.com/watch?v=abc123",
        prep_time_minutes=10,
        cook_time_minutes=30,
        total_time_minutes=40,
        servings=4,
        difficulty="easy",
        source_url="https://youtube.com/watch?v=abc123",
        source_platform="youtube",
        exposure_score=85.5,
        view_count=1000,
        chef=sample_chef_summary,
        ingredients=[
            IngredientSchema(
                id=str(uuid4()),
                name="김치",
                amount="300",
                unit="g",
                is_optional=False,
                order_index=0,
            ),
        ],
        steps=[
            CookingStepSchema(
                id=str(uuid4()),
                step_number=1,
                description="재료를 준비합니다.",
                duration_seconds=300,
            ),
        ],
        tags=[
            TagSchema(id=str(uuid4()), name="한식", category="cuisine"),
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_recipe_list_item(
    sample_recipe_id: str,
    sample_chef_summary: ChefSummary,
) -> RecipeListItem:
    """샘플 레시피 목록 아이템"""
    return RecipeListItem(
        id=sample_recipe_id,
        title="김치찌개",
        description="맛있는 김치찌개 레시피",
        thumbnail_url="https://example.com/kimchi.jpg",
        prep_time_minutes=10,
        cook_time_minutes=30,
        difficulty="easy",
        exposure_score=85.5,
        chef=sample_chef_summary,
        tags=[
            TagSchema(id=str(uuid4()), name="한식", category="cuisine"),
        ],
        created_at=datetime.now(timezone.utc),
    )


class TestGetRecipeContract:
    """GET /recipes/{recipe_id} 계약 테스트"""

    def test_get_recipe_success_response_schema(
        self,
        client: TestClient,
        sample_recipe_detail: RecipeDetail,
        sample_recipe_id: str,
    ):
        """성공 응답이 RecipeDetail 스키마를 따른다"""
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(return_value=sample_recipe_detail)
            mock_get_service.return_value = mock_service

            response = client.get(f"/recipes/{sample_recipe_id}")

            assert response.status_code == 200
            data = response.json()

            # 필수 필드 검증
            assert "id" in data
            assert "title" in data
            assert "chef" in data
            assert "ingredients" in data
            assert "steps" in data
            assert "tags" in data
            assert "created_at" in data
            assert "updated_at" in data

            # 값 검증
            assert data["id"] == sample_recipe_id
            assert data["title"] == "김치찌개"
            assert data["difficulty"] == "easy"
            assert data["prep_time_minutes"] == 10
            assert data["cook_time_minutes"] == 30

            # chef 구조 검증
            assert data["chef"]["name"] == "백종원"
            assert data["chef"]["is_verified"] is True

            # ingredients 구조 검증
            assert len(data["ingredients"]) == 1
            assert data["ingredients"][0]["name"] == "김치"

            # steps 구조 검증
            assert len(data["steps"]) == 1
            assert data["steps"][0]["step_number"] == 1

            # tags 구조 검증
            assert len(data["tags"]) == 1
            assert data["tags"][0]["name"] == "한식"

    def test_get_recipe_not_found_response_schema(self, client: TestClient):
        """404 응답이 ErrorResponse 스키마를 따른다"""
        non_existent_id = str(uuid4())

        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            from recipe_service.middleware.error_handler import RecipeNotFoundError

            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(
                side_effect=RecipeNotFoundError(non_existent_id)
            )
            mock_get_service.return_value = mock_service

            response = client.get(f"/recipes/{non_existent_id}")

            assert response.status_code == 404
            data = response.json()

            # ErrorResponse 스키마 검증
            assert "code" in data
            assert "message" in data
            assert data["code"] == "RECIPE_NOT_FOUND"

    def test_get_recipe_content_type_json(
        self,
        client: TestClient,
        sample_recipe_detail: RecipeDetail,
        sample_recipe_id: str,
    ):
        """응답의 Content-Type이 application/json이다"""
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(return_value=sample_recipe_detail)
            mock_get_service.return_value = mock_service

            response = client.get(f"/recipes/{sample_recipe_id}")
            assert "application/json" in response.headers["content-type"]


class TestGetRecipesListContract:
    """GET /recipes 계약 테스트"""

    def test_get_recipes_list_response_schema(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """레시피 목록 응답이 RecipeListResponse 스키마를 따른다"""
        response_data = RecipeListResponse(
            items=[sample_recipe_list_item],
            next_cursor=None,
            has_more=False,
            total_count=None,
        )

        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(return_value=response_data)
            mock_get_service.return_value = mock_service

            response = client.get("/recipes")

            assert response.status_code == 200
            data = response.json()

            # RecipeListResponse 스키마 필수 필드
            assert "items" in data
            assert "has_more" in data
            assert isinstance(data["items"], list)
            assert isinstance(data["has_more"], bool)

    def test_get_recipes_pagination_params(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """페이지네이션 파라미터가 올바르게 처리된다"""
        response_data = RecipeListResponse(
            items=[sample_recipe_list_item],
            next_cursor=None,
            has_more=False,
            total_count=None,
        )

        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(return_value=response_data)
            mock_get_service.return_value = mock_service

            # 커스텀 limit으로 요청
            response = client.get("/recipes?limit=10")
            assert response.status_code == 200

            # limit 범위 초과 (1-100)
            response = client.get("/recipes?limit=200")
            assert response.status_code == 422


class TestGetPopularRecipesContract:
    """GET /recipes/popular 계약 테스트"""

    def test_get_popular_recipes_response_schema(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """인기 레시피 응답이 list[RecipeListItem] 스키마를 따른다"""
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_popular = AsyncMock(return_value=[sample_recipe_list_item])
            mock_get_service.return_value = mock_service

            response = client.get("/recipes/popular")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            if data:
                item = data[0]
                assert "id" in item
                assert "title" in item
                assert "chef" in item

    def test_get_popular_recipes_limit_validation(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """인기 레시피 limit 파라미터 검증 (1-50)"""
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_popular = AsyncMock(return_value=[sample_recipe_list_item])
            mock_get_service.return_value = mock_service

            # 유효 범위 내
            response = client.get("/recipes/popular?limit=30")
            assert response.status_code == 200

            # 범위 초과 (최대 50)
            response = client.get("/recipes/popular?limit=100")
            assert response.status_code == 422
