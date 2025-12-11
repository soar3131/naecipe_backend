"""
Cookbooks CRUD 통합 테스트

레시피북 API 엔드포인트 통합 테스트
"""

import pytest
from httpx import AsyncClient

from app.cookbooks.models import Cookbook
from app.users.models import User


@pytest.mark.asyncio
class TestCreateCookbook:
    """레시피북 생성 (User Story 1) 통합 테스트"""

    async def test_create_cookbook_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        cookbook_create_data: dict,
    ):
        """레시피북 생성 성공"""
        # When: 레시피북 생성 API 호출
        response = await client.post(
            "/api/v1/cookbooks",
            json=cookbook_create_data,
            headers=auth_headers,
        )

        # Then: 201 Created, 생성된 레시피북 정보 반환
        assert response.status_code == 201
        data = response.json()

        assert data["name"] == cookbook_create_data["name"]
        assert data["description"] == cookbook_create_data["description"]
        assert data["cover_image_url"] == cookbook_create_data["cover_image_url"]
        assert data["is_default"] is False
        assert data["saved_recipe_count"] == 0
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_cookbook_minimal(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """최소 필드(이름만)로 레시피북 생성"""
        # Given: 이름만 있는 요청
        data = {"name": "간단한 레시피북"}

        # When
        response = await client.post(
            "/api/v1/cookbooks",
            json=data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "간단한 레시피북"
        assert result["description"] is None
        assert result["cover_image_url"] is None

    async def test_create_cookbook_name_validation(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """이름 유효성 검증 - 빈 문자열 거부"""
        # Given: 빈 이름
        data = {"name": ""}

        # When
        response = await client.post(
            "/api/v1/cookbooks",
            json=data,
            headers=auth_headers,
        )

        # Then: 422 Validation Error
        assert response.status_code == 422

    async def test_create_cookbook_name_too_long(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """이름 유효성 검증 - 100자 초과 거부"""
        # Given: 101자 이름
        data = {"name": "가" * 101}

        # When
        response = await client.post(
            "/api/v1/cookbooks",
            json=data,
            headers=auth_headers,
        )

        # Then: 422 Validation Error
        assert response.status_code == 422

    async def test_create_cookbook_without_auth(
        self,
        client: AsyncClient,
        cookbook_create_data: dict,
    ):
        """인증 없이 레시피북 생성 시도 - 실패"""
        # When: 인증 헤더 없이 요청
        response = await client.post(
            "/api/v1/cookbooks",
            json=cookbook_create_data,
        )

        # Then: 401 Unauthorized
        assert response.status_code == 401

    async def test_create_cookbook_creates_default_first(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        db_session,
    ):
        """첫 레시피북 생성 시 기본 레시피북도 생성됨"""
        # Given: 사용자에게 기본 레시피북이 없음

        # When: 새 레시피북 생성
        response = await client.post(
            "/api/v1/cookbooks",
            json={"name": "새 레시피북"},
            headers=auth_headers,
        )

        # Then: 성공하고 sort_order가 1 (기본이 0이므로)
        assert response.status_code == 201
        data = response.json()
        assert data["sort_order"] == 1  # 기본 레시피북이 0


@pytest.mark.asyncio
class TestListCookbooks:
    """레시피북 목록 조회 (User Story 2) 통합 테스트"""

    async def test_list_cookbooks_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        multiple_cookbooks: list[Cookbook],
    ):
        """레시피북 목록 조회 성공"""
        # When
        response = await client.get(
            "/api/v1/cookbooks",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] == len(multiple_cookbooks)

        # sort_order 순 정렬 확인
        items = data["items"]
        sort_orders = [item["sort_order"] for item in items]
        assert sort_orders == sorted(sort_orders)

    async def test_list_cookbooks_creates_default_if_none(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """레시피북이 없으면 기본 레시피북 자동 생성"""
        # Given: 사용자에게 레시피북이 없음

        # When
        response = await client.get(
            "/api/v1/cookbooks",
            headers=auth_headers,
        )

        # Then: 기본 레시피북 1개 생성됨
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        default = data["items"][0]
        assert default["is_default"] is True
        assert default["name"] == "내 레시피북"

    async def test_list_cookbooks_default_first(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        multiple_cookbooks: list[Cookbook],
    ):
        """기본 레시피북이 첫 번째로 반환됨 (sort_order=0)"""
        # When
        response = await client.get(
            "/api/v1/cookbooks",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        first_item = data["items"][0]
        assert first_item["is_default"] is True
        assert first_item["sort_order"] == 0

    async def test_list_cookbooks_without_auth(
        self,
        client: AsyncClient,
    ):
        """인증 없이 목록 조회 시도 - 실패"""
        # When
        response = await client.get("/api/v1/cookbooks")

        # Then: 401 Unauthorized
        assert response.status_code == 401

    async def test_list_cookbooks_isolation(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
        default_cookbook: Cookbook,
    ):
        """다른 사용자의 레시피북은 조회되지 않음"""
        # When: 현재 사용자의 목록 조회
        response = await client.get(
            "/api/v1/cookbooks",
            headers=auth_headers,
        )

        # Then: 본인 것만 조회됨
        assert response.status_code == 200
        data = response.json()

        cookbook_ids = [item["id"] for item in data["items"]]
        assert default_cookbook.id in cookbook_ids
        assert other_user_cookbook.id not in cookbook_ids


@pytest.mark.asyncio
class TestGetCookbook:
    """레시피북 상세 조회 (User Story 3) 통합 테스트"""

    async def test_get_cookbook_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        sample_cookbook: Cookbook,
    ):
        """레시피북 상세 조회 성공"""
        # When
        response = await client.get(
            f"/api/v1/cookbooks/{sample_cookbook.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_cookbook.id
        assert data["name"] == sample_cookbook.name
        assert data["description"] == sample_cookbook.description

    async def test_get_cookbook_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """존재하지 않는 레시피북 조회 - 404"""
        # When
        response = await client.get(
            "/api/v1/cookbooks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404

    async def test_get_cookbook_other_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
    ):
        """다른 사용자의 레시피북 조회 시도 - 404 (존재 여부 숨김)"""
        # When: 다른 사용자의 레시피북 ID로 조회
        response = await client.get(
            f"/api/v1/cookbooks/{other_user_cookbook.id}",
            headers=auth_headers,
        )

        # Then: 보안상 404 반환 (403 아님)
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateCookbook:
    """레시피북 수정 (User Story 4) 통합 테스트"""

    async def test_update_cookbook_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        sample_cookbook: Cookbook,
        cookbook_update_data: dict,
    ):
        """레시피북 수정 성공"""
        # When
        response = await client.put(
            f"/api/v1/cookbooks/{sample_cookbook.id}",
            json=cookbook_update_data,
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == cookbook_update_data["name"]
        assert data["description"] == cookbook_update_data["description"]

    async def test_update_cookbook_partial(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        sample_cookbook: Cookbook,
    ):
        """부분 수정 - 이름만 변경"""
        # When
        response = await client.put(
            f"/api/v1/cookbooks/{sample_cookbook.id}",
            json={"name": "변경된 이름만"},
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "변경된 이름만"
        assert data["description"] == sample_cookbook.description  # 기존 값 유지

    async def test_update_default_cookbook(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """기본 레시피북도 수정 가능"""
        # When
        response = await client.put(
            f"/api/v1/cookbooks/{default_cookbook.id}",
            json={"name": "수정된 기본 레시피북"},
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 기본 레시피북"
        assert data["is_default"] is True  # 기본 속성 유지

    async def test_update_cookbook_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        cookbook_update_data: dict,
    ):
        """존재하지 않는 레시피북 수정 - 404"""
        response = await client.put(
            "/api/v1/cookbooks/00000000-0000-0000-0000-000000000000",
            json=cookbook_update_data,
            headers=auth_headers,
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteCookbook:
    """레시피북 삭제 (User Story 5) 통합 테스트"""

    async def test_delete_cookbook_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        sample_cookbook: Cookbook,
    ):
        """레시피북 삭제 성공"""
        # When
        response = await client.delete(
            f"/api/v1/cookbooks/{sample_cookbook.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 204

        # 삭제 확인
        get_response = await client.get(
            f"/api/v1/cookbooks/{sample_cookbook.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    async def test_delete_default_cookbook_forbidden(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
    ):
        """기본 레시피북 삭제 시도 - 400 거부"""
        # When
        response = await client.delete(
            f"/api/v1/cookbooks/{default_cookbook.id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 400

    async def test_delete_cookbook_not_found(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """존재하지 않는 레시피북 삭제 - 404"""
        response = await client.delete(
            "/api/v1/cookbooks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_delete_other_user_cookbook(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        other_user: User,
        other_user_cookbook: Cookbook,
    ):
        """다른 사용자의 레시피북 삭제 시도 - 404"""
        response = await client.delete(
            f"/api/v1/cookbooks/{other_user_cookbook.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestReorderCookbooks:
    """레시피북 순서 변경 (User Story 6) 통합 테스트"""

    async def test_reorder_cookbooks_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        multiple_cookbooks: list[Cookbook],
    ):
        """레시피북 순서 변경 성공"""
        # Given: 새로운 순서 (역순)
        new_order = [cb.id for cb in reversed(multiple_cookbooks)]

        # When
        response = await client.patch(
            "/api/v1/cookbooks/reorder",
            json={"cookbook_ids": new_order},
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # 순서 확인
        result_ids = [item["id"] for item in data["items"]]
        result_orders = [item["sort_order"] for item in data["items"]]

        # sort_order 순 정렬되어 반환
        assert result_orders == sorted(result_orders)

    async def test_reorder_cookbooks_partial(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        multiple_cookbooks: list[Cookbook],
    ):
        """일부 레시피북만 순서 변경"""
        # Given: 일부 ID만 포함
        partial_order = [multiple_cookbooks[1].id, multiple_cookbooks[0].id]

        # When
        response = await client.patch(
            "/api/v1/cookbooks/reorder",
            json={"cookbook_ids": partial_order},
            headers=auth_headers,
        )

        # Then: 성공 (목록에 없는 것은 순서 유지)
        assert response.status_code == 200

    async def test_reorder_ignores_other_user_ids(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        default_cookbook: Cookbook,
        other_user: User,
        other_user_cookbook: Cookbook,
    ):
        """다른 사용자의 ID는 무시됨"""
        # Given: 다른 사용자 ID 포함
        order = [other_user_cookbook.id, default_cookbook.id]

        # When
        response = await client.patch(
            "/api/v1/cookbooks/reorder",
            json={"cookbook_ids": order},
            headers=auth_headers,
        )

        # Then: 성공하지만 다른 사용자 ID는 무시됨
        assert response.status_code == 200
