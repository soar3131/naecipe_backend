"""
SavedRecipe CRUD 통합 테스트 (SPEC-008)

저장된 레시피 API 엔드포인트 통합 테스트
"""

import pytest
from httpx import AsyncClient

from app.cookbooks.models import Cookbook, SavedRecipe
from app.recipes.models import Chef, Recipe
from app.users.models import User


# ==========================================================================
# User Story 1: 레시피 저장 (POST /cookbooks/{cookbook_id}/recipes)
# ==========================================================================


@pytest.mark.asyncio
class TestSaveRecipe:
    """레시피 저장 (User Story 1) 통합 테스트"""

    async def test_save_recipe_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """T009: 레시피 저장 성공"""
        # Given: 저장할 레시피와 레시피북이 존재
        data = {"recipe_id": sample_recipe.id}

        # When: 레시피 저장 API 호출
        response = await client.post(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then: 201 Created, 저장된 레시피 정보 반환
        assert response.status_code == 201
        result = response.json()

        assert result["cookbook_id"] == default_cookbook.id
        assert result["recipe"]["id"] == sample_recipe.id
        assert result["recipe"]["title"] == sample_recipe.title
        assert result["memo"] is None
        assert result["cook_count"] == 0
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    async def test_save_recipe_with_memo(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """T010: 메모와 함께 레시피 저장"""
        # Given: 메모 포함 요청
        data = {
            "recipe_id": sample_recipe.id,
            "memo": "백종원 레시피! 돼지고기 300g 필요",
        }

        # When
        response = await client.post(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 201
        result = response.json()

        assert result["memo"] == "백종원 레시피! 돼지고기 300g 필요"

    async def test_save_recipe_duplicate_conflict(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
        sample_recipe: Recipe,
    ):
        """T011: 중복 저장 시 409 Conflict"""
        # Given: 이미 저장된 레시피가 존재
        data = {"recipe_id": sample_recipe.id}

        # When: 같은 레시피 다시 저장 시도
        response = await client.post(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then: 409 Conflict
        assert response.status_code == 409
        result = response.json()
        assert result["type"].endswith("/saved-recipe/already-saved")

    async def test_save_recipe_nonexistent_recipe(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """T012: 존재하지 않는 레시피 저장 시도 - 404"""
        # Given: 존재하지 않는 레시피 ID
        data = {"recipe_id": "00000000-0000-0000-0000-000000000000"}

        # When
        response = await client.post(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then: 404 Not Found (Recipe)
        assert response.status_code == 404

    async def test_save_recipe_other_user_cookbook(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """T013: 다른 사용자 레시피북에 저장 시도 - 404"""
        # Given: 다른 사용자의 레시피북 ID
        data = {"recipe_id": sample_recipe.id}

        # When
        response = await client.post(
            f"/api/v1/cookbooks/{other_user_cookbook.id}/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then: 404 (보안상 존재 여부 숨김)
        assert response.status_code == 404

    async def test_save_recipe_nonexistent_cookbook(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        sample_recipe: Recipe,
    ):
        """존재하지 않는 레시피북에 저장 시도 - 404"""
        # Given: 존재하지 않는 레시피북 ID
        data = {"recipe_id": sample_recipe.id}

        # When
        response = await client.post(
            "/api/v1/cookbooks/00000000-0000-0000-0000-000000000000/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_save_recipe_without_auth(
        self,
        client: AsyncClient,
        default_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """인증 없이 저장 시도 - 401"""
        # When: 인증 헤더 없이 요청
        response = await client.post(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            json={"recipe_id": sample_recipe.id},
        )

        # Then
        assert response.status_code == 401

    async def test_save_recipe_memo_too_long(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """메모 길이 초과 (1000자 초과) - 422"""
        # Given: 1001자 메모
        data = {
            "recipe_id": sample_recipe.id,
            "memo": "가" * 1001,
        }

        # When
        response = await client.post(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            json=data,
            headers=auth_headers,
        )

        # Then: 422 Validation Error
        assert response.status_code == 422


# ==========================================================================
# User Story 2: 저장된 레시피 목록 조회 (GET /cookbooks/{cookbook_id}/recipes)
# ==========================================================================


@pytest.mark.asyncio
class TestListSavedRecipes:
    """저장된 레시피 목록 조회 (User Story 2) 통합 테스트"""

    async def test_list_saved_recipes_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        multiple_saved_recipes: list[SavedRecipe],
    ):
        """T018: 저장된 레시피 목록 조회 성공"""
        # When
        response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        assert "items" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert result["total"] == len(multiple_saved_recipes)

        # 각 항목에 recipe 정보 포함 확인
        for item in result["items"]:
            assert "recipe" in item
            assert item["recipe"]["id"] is not None
            assert item["recipe"]["title"] is not None

    async def test_list_saved_recipes_empty(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """T019: 빈 목록 조회"""
        # Given: 저장된 레시피가 없음

        # When
        response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_saved_recipes_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        multiple_saved_recipes: list[SavedRecipe],
    ):
        """T020: 페이지네이션"""
        # When: limit=1로 요청
        response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            params={"limit": 1, "offset": 0},
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        assert result["limit"] == 1
        assert result["offset"] == 0
        assert len(result["items"]) == 1
        assert result["total"] == len(multiple_saved_recipes)

    async def test_list_saved_recipes_other_user_cookbook(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
    ):
        """T021: 다른 사용자 레시피북 목록 조회 시도 - 404"""
        # When
        response = await client.get(
            f"/api/v1/cookbooks/{other_user_cookbook.id}/recipes",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_list_saved_recipes_sorted_by_created_at(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        multiple_saved_recipes: list[SavedRecipe],
    ):
        """T022: created_at 내림차순 정렬 (최신순)"""
        # When
        response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        items = result["items"]
        if len(items) > 1:
            # 최신순 정렬 확인
            for i in range(len(items) - 1):
                assert items[i]["created_at"] >= items[i + 1]["created_at"]


# ==========================================================================
# User Story 3: 저장된 레시피 상세 조회
# (GET /cookbooks/{cookbook_id}/recipes/{saved_recipe_id})
# ==========================================================================


@pytest.mark.asyncio
class TestGetSavedRecipe:
    """저장된 레시피 상세 조회 (User Story 3) 통합 테스트"""

    async def test_get_saved_recipe_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
        sample_recipe: Recipe,
    ):
        """T026: 저장된 레시피 상세 조회 성공"""
        # When
        response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        assert result["id"] == saved_recipe.id
        assert result["cookbook_id"] == default_cookbook.id
        assert result["recipe"]["id"] == sample_recipe.id
        assert result["recipe"]["title"] == sample_recipe.title
        assert result["memo"] == saved_recipe.memo
        assert "created_at" in result
        assert "updated_at" in result

    async def test_get_saved_recipe_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """T027: 존재하지 않는 저장 레시피 조회 - 404"""
        # When
        response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/"
            "00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_get_saved_recipe_wrong_cookbook(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        sample_cookbook: Cookbook,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T028: 다른 레시피북에서 조회 시도 - 404"""
        # Given: saved_recipe는 default_cookbook에 속함
        # When: sample_cookbook ID로 조회 시도
        response = await client.get(
            f"/api/v1/cookbooks/{sample_cookbook.id}/recipes/{saved_recipe.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_get_saved_recipe_other_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T029: 다른 사용자의 저장 레시피 조회 - 404"""
        # When: 다른 사용자의 레시피북으로 조회
        response = await client.get(
            f"/api/v1/cookbooks/{other_user_cookbook.id}/recipes/{saved_recipe.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404


# ==========================================================================
# User Story 4: 저장된 레시피 수정 (메모)
# (PATCH /cookbooks/{cookbook_id}/recipes/{saved_recipe_id})
# ==========================================================================


@pytest.mark.asyncio
class TestUpdateSavedRecipe:
    """저장된 레시피 수정 (User Story 4) 통합 테스트"""

    async def test_update_saved_recipe_memo(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T032: 메모 수정 성공"""
        # Given: 새로운 메모
        data = {"memo": "수정된 메모입니다. 청양고추 추가!"}

        # When
        response = await client.patch(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
            json=data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        assert result["memo"] == "수정된 메모입니다. 청양고추 추가!"

    async def test_update_saved_recipe_clear_memo(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T033: 메모 삭제 (null로 설정)"""
        # Given: 빈 메모
        data = {"memo": None}

        # When
        response = await client.patch(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
            json=data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        result = response.json()

        assert result["memo"] is None

    async def test_update_saved_recipe_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """T034: 존재하지 않는 저장 레시피 수정 - 404"""
        # When
        response = await client.patch(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/"
            "00000000-0000-0000-0000-000000000000",
            json={"memo": "새 메모"},
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_update_saved_recipe_other_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T035: 다른 사용자의 저장 레시피 수정 시도 - 404"""
        # When
        response = await client.patch(
            f"/api/v1/cookbooks/{other_user_cookbook.id}/recipes/{saved_recipe.id}",
            json={"memo": "해킹 시도"},
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_update_saved_recipe_memo_too_long(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T036: 메모 길이 초과 - 422"""
        # Given: 1001자 메모
        data = {"memo": "가" * 1001}

        # When
        response = await client.patch(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
            json=data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 422


# ==========================================================================
# User Story 5: 저장된 레시피 삭제
# (DELETE /cookbooks/{cookbook_id}/recipes/{saved_recipe_id})
# ==========================================================================


@pytest.mark.asyncio
class TestDeleteSavedRecipe:
    """저장된 레시피 삭제 (User Story 5) 통합 테스트"""

    async def test_delete_saved_recipe_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T039: 저장된 레시피 삭제 성공"""
        # When
        response = await client.delete(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
            headers=auth_headers,
        )

        # Then: 204 No Content
        assert response.status_code == 204

        # 삭제 확인
        get_response = await client.get(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_saved_recipe_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """T040: 존재하지 않는 저장 레시피 삭제 - 404"""
        # When
        response = await client.delete(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/"
            "00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_delete_saved_recipe_other_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """T041: 다른 사용자의 저장 레시피 삭제 시도 - 404"""
        # When
        response = await client.delete(
            f"/api/v1/cookbooks/{other_user_cookbook.id}/recipes/{saved_recipe.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_delete_saved_recipe_without_auth(
        self,
        client: AsyncClient,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """인증 없이 삭제 시도 - 401"""
        # When
        response = await client.delete(
            f"/api/v1/cookbooks/{default_cookbook.id}/recipes/{saved_recipe.id}",
        )

        # Then
        assert response.status_code == 401
