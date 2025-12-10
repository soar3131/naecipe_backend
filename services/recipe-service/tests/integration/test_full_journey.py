"""
전체 사용자 여정 통합 테스트

사용자의 완전한 레시피 탐색 여정을 검증합니다.
이 테스트는 실제 데이터베이스 연결 없이 API 흐름을 검증합니다.

시나리오:
1. 인기 레시피 조회 → 2. 레시피 상세 조회 → 3. 요리사 정보 조회 → 4. 요리사별 레시피 조회
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from recipe_service.main import app
from recipe_service.schemas import (
    ChefDetail,
    ChefPlatformSchema,
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
def sample_chef_id() -> str:
    """샘플 요리사 ID"""
    return str(uuid4())


@pytest.fixture
def sample_recipe_id() -> str:
    """샘플 레시피 ID"""
    return str(uuid4())


@pytest.fixture
def sample_chef_detail(sample_chef_id: str) -> ChefDetail:
    """샘플 요리사 상세 정보"""
    return ChefDetail(
        id=sample_chef_id,
        name="백종원",
        profile_image_url="https://example.com/chef.jpg",
        bio="대한민국을 대표하는 요리연구가",
        specialty="한식",
        recipe_count=150,
        total_views=10000000,
        avg_rating=4.9,
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
def sample_recipe_detail(sample_recipe_id: str, sample_chef_id: str) -> RecipeDetail:
    """샘플 레시피 상세 정보"""
    return RecipeDetail(
        id=sample_recipe_id,
        title="김치찌개",
        description="집에서 간단히 만드는 맛있는 김치찌개",
        thumbnail_url="https://example.com/kimchi.jpg",
        video_url="https://youtube.com/watch?v=abc123",
        prep_time_minutes=10,
        cook_time_minutes=30,
        total_time_minutes=40,
        servings=4,
        difficulty="easy",
        source_url="https://youtube.com/watch?v=abc123",
        source_platform="youtube",
        exposure_score=95.5,
        view_count=50000,
        chef=ChefSummary(
            id=sample_chef_id,
            name="백종원",
            profile_image_url="https://example.com/chef.jpg",
            specialty="한식",
            is_verified=True,
        ),
        ingredients=[
            IngredientSchema(
                id=str(uuid4()),
                name="김치",
                amount="300",
                unit="g",
                preparation="잘게 썰어서",
                is_optional=False,
                order_index=0,
            ),
            IngredientSchema(
                id=str(uuid4()),
                name="돼지고기",
                amount="200",
                unit="g",
                preparation="한입 크기로",
                is_optional=False,
                order_index=1,
            ),
        ],
        steps=[
            CookingStepSchema(
                id=str(uuid4()),
                step_number=1,
                description="재료를 준비합니다.",
                tip="신김치를 사용하면 더 맛있어요",
                duration_seconds=300,
            ),
            CookingStepSchema(
                id=str(uuid4()),
                step_number=2,
                description="냄비에 재료를 넣고 끓입니다.",
                duration_seconds=600,
            ),
        ],
        tags=[
            TagSchema(id=str(uuid4()), name="한식", category="cuisine"),
            TagSchema(id=str(uuid4()), name="찌개", category="type"),
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_recipe_list_item(sample_recipe_id: str, sample_chef_id: str) -> RecipeListItem:
    """샘플 레시피 목록 아이템"""
    return RecipeListItem(
        id=sample_recipe_id,
        title="김치찌개",
        description="집에서 간단히 만드는 맛있는 김치찌개",
        thumbnail_url="https://example.com/kimchi.jpg",
        prep_time_minutes=10,
        cook_time_minutes=30,
        difficulty="easy",
        exposure_score=95.5,
        chef=ChefSummary(
            id=sample_chef_id,
            name="백종원",
            profile_image_url="https://example.com/chef.jpg",
            specialty="한식",
            is_verified=True,
        ),
        tags=[
            TagSchema(id=str(uuid4()), name="한식", category="cuisine"),
        ],
        created_at=datetime.now(timezone.utc),
    )


class TestFullUserJourney:
    """전체 사용자 여정 테스트"""

    def test_journey_discover_popular_recipe(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """
        여정 1단계: 사용자가 인기 레시피 목록을 조회한다
        """
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_popular = AsyncMock(
                return_value=[sample_recipe_list_item]
            )
            mock_get_service.return_value = mock_service

            response = client.get("/recipes/popular")

            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert data[0]["title"] == "김치찌개"
            assert data[0]["chef"]["name"] == "백종원"

    def test_journey_view_recipe_detail(
        self,
        client: TestClient,
        sample_recipe_detail: RecipeDetail,
        sample_recipe_id: str,
    ):
        """
        여정 2단계: 사용자가 레시피 상세 정보를 조회한다
        """
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(return_value=sample_recipe_detail)
            mock_get_service.return_value = mock_service

            response = client.get(f"/recipes/{sample_recipe_id}")

            assert response.status_code == 200
            data = response.json()

            # 레시피 기본 정보
            assert data["title"] == "김치찌개"
            assert data["description"] is not None
            assert data["difficulty"] == "easy"

            # 요리사 정보
            assert data["chef"]["name"] == "백종원"
            assert data["chef"]["is_verified"] is True

            # 재료 정보
            assert len(data["ingredients"]) >= 2
            assert data["ingredients"][0]["name"] == "김치"

            # 조리 단계
            assert len(data["steps"]) >= 2
            assert data["steps"][0]["step_number"] == 1

            # 태그
            assert len(data["tags"]) >= 1

    def test_journey_view_chef_profile(
        self,
        client: TestClient,
        sample_chef_detail: ChefDetail,
        sample_chef_id: str,
    ):
        """
        여정 3단계: 사용자가 레시피의 요리사 프로필을 조회한다
        """
        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(return_value=sample_chef_detail)
            mock_get_service.return_value = mock_service

            response = client.get(f"/chefs/{sample_chef_id}")

            assert response.status_code == 200
            data = response.json()

            # 요리사 기본 정보
            assert data["name"] == "백종원"
            assert data["specialty"] == "한식"
            assert data["is_verified"] is True

            # 통계 정보
            assert data["recipe_count"] == 150
            assert data["total_views"] == 10000000

            # 플랫폼 정보
            assert len(data["platforms"]) >= 1
            assert data["platforms"][0]["platform"] == "youtube"

    def test_journey_browse_chef_recipes(
        self,
        client: TestClient,
        sample_chef_detail: ChefDetail,
        sample_recipe_list_item: RecipeListItem,
        sample_chef_id: str,
    ):
        """
        여정 4단계: 사용자가 요리사의 다른 레시피를 탐색한다
        """
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
            response_data = RecipeListResponse(
                items=[sample_recipe_list_item],
                next_cursor=None,
                has_more=False,
                total_count=None,
            )
            mock_recipe_service = AsyncMock()
            mock_recipe_service.get_by_chef = AsyncMock(return_value=response_data)
            mock_get_recipe_service.return_value = mock_recipe_service

            response = client.get(f"/chefs/{sample_chef_id}/recipes")

            assert response.status_code == 200
            data = response.json()

            # 페이지네이션 응답 구조
            assert "items" in data
            assert "has_more" in data

            # 레시피 목록
            assert len(data["items"]) >= 1
            assert data["items"][0]["title"] == "김치찌개"


class TestNavigationFlows:
    """네비게이션 흐름 테스트"""

    def test_browse_recipes_with_pagination(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """레시피 목록 페이지네이션 탐색"""
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            # 첫 페이지 (더 있음)
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(
                return_value=RecipeListResponse(
                    items=[sample_recipe_list_item],
                    next_cursor="cursor_page_2",
                    has_more=True,
                    total_count=None,
                )
            )
            mock_get_service.return_value = mock_service

            # 첫 페이지 요청
            response = client.get("/recipes?limit=20")
            assert response.status_code == 200
            data = response.json()
            assert data["has_more"] is True
            assert data["next_cursor"] == "cursor_page_2"

    def test_filter_recipes_by_difficulty(
        self,
        client: TestClient,
        sample_recipe_list_item: RecipeListItem,
    ):
        """난이도별 레시피 필터링"""
        with patch(
            "recipe_service.api.recipes.get_recipe_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_list = AsyncMock(
                return_value=RecipeListResponse(
                    items=[sample_recipe_list_item],
                    next_cursor=None,
                    has_more=False,
                    total_count=None,
                )
            )
            mock_get_service.return_value = mock_service

            response = client.get("/recipes?difficulty=easy")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) >= 1


class TestErrorHandling:
    """에러 처리 테스트"""

    def test_recipe_not_found(self, client: TestClient):
        """존재하지 않는 레시피 조회 시 404"""
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

    def test_chef_not_found(self, client: TestClient):
        """존재하지 않는 요리사 조회 시 404"""
        non_existent_id = str(uuid4())

        with patch(
            "recipe_service.api.chefs.get_chef_service"
        ) as mock_get_service:
            from recipe_service.middleware.error_handler import ChefNotFoundError

            mock_service = AsyncMock()
            mock_service.get_by_id = AsyncMock(
                side_effect=ChefNotFoundError(non_existent_id)
            )
            mock_get_service.return_value = mock_service

            response = client.get(f"/chefs/{non_existent_id}")
            assert response.status_code == 404

    def test_health_check_always_available(self, client: TestClient):
        """헬스체크 엔드포인트는 항상 사용 가능"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
