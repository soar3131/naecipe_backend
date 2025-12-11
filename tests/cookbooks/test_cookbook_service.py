"""
CookbookService 단위 테스트

서비스 레이어 비즈니스 로직 테스트
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cookbooks.exceptions import (
    CannotDeleteDefaultCookbookError,
    CookbookNotFoundError,
)
from app.cookbooks.models import Cookbook
from app.cookbooks.schemas import CookbookCreateRequest, CookbookUpdateRequest
from app.cookbooks.services import CookbookService
from app.users.models import User


@pytest.mark.asyncio
class TestEnsureDefaultCookbook:
    """ensure_default_cookbook 테스트"""

    async def test_creates_default_if_none_exists(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """기본 레시피북이 없으면 생성"""
        # Given: 레시피북이 없는 상태
        service = CookbookService(db_session)

        # When
        cookbook = await service.ensure_default_cookbook(user_id)

        # Then
        assert cookbook is not None
        assert cookbook.is_default is True
        assert cookbook.name == "내 레시피북"
        assert cookbook.sort_order == 0
        assert cookbook.user_id == user_id

    async def test_returns_existing_default(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """기존 기본 레시피북이 있으면 반환"""
        # Given: 기본 레시피북이 존재
        service = CookbookService(db_session)

        # When
        cookbook = await service.ensure_default_cookbook(user_id)

        # Then
        assert cookbook.id == default_cookbook.id


@pytest.mark.asyncio
class TestCreateCookbook:
    """create_cookbook 테스트"""

    async def test_create_cookbook_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """레시피북 생성 성공"""
        service = CookbookService(db_session)
        data = CookbookCreateRequest(
            name="새 레시피북",
            description="테스트 설명",
            cover_image_url="https://example.com/cover.jpg",
        )

        # When
        result = await service.create_cookbook(user_id, data)

        # Then
        assert result.name == "새 레시피북"
        assert result.description == "테스트 설명"
        assert result.is_default is False
        assert result.saved_recipe_count == 0

    async def test_create_cookbook_creates_default_first(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """생성 시 기본 레시피북도 함께 생성"""
        service = CookbookService(db_session)
        data = CookbookCreateRequest(name="새 레시피북")

        # When
        result = await service.create_cookbook(user_id, data)

        # Then: sort_order가 1 (기본이 0)
        assert result.sort_order == 1

    async def test_create_cookbook_increments_sort_order(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """생성 시 sort_order 자동 증가"""
        service = CookbookService(db_session)

        # When: 두 번 생성
        result1 = await service.create_cookbook(
            user_id, CookbookCreateRequest(name="첫 번째")
        )
        result2 = await service.create_cookbook(
            user_id, CookbookCreateRequest(name="두 번째")
        )

        # Then
        assert result1.sort_order == 1
        assert result2.sort_order == 2


@pytest.mark.asyncio
class TestGetCookbooks:
    """get_cookbooks 테스트"""

    async def test_get_cookbooks_returns_sorted_list(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        multiple_cookbooks: list[Cookbook],
    ):
        """sort_order 순 정렬된 목록 반환"""
        service = CookbookService(db_session)

        # When
        result = await service.get_cookbooks(user_id)

        # Then
        assert result.total == len(multiple_cookbooks)
        sort_orders = [item.sort_order for item in result.items]
        assert sort_orders == sorted(sort_orders)

    async def test_get_cookbooks_creates_default_if_none(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """레시피북이 없으면 기본 생성 후 반환"""
        service = CookbookService(db_session)

        # When
        result = await service.get_cookbooks(user_id)

        # Then
        assert result.total == 1
        assert result.items[0].is_default is True


@pytest.mark.asyncio
class TestGetCookbookById:
    """get_cookbook_by_id 테스트"""

    async def test_get_cookbook_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        sample_cookbook: Cookbook,
    ):
        """레시피북 조회 성공"""
        service = CookbookService(db_session)

        # When
        result = await service.get_cookbook_by_id(sample_cookbook.id, user_id)

        # Then
        assert result.id == sample_cookbook.id
        assert result.name == sample_cookbook.name

    async def test_get_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """존재하지 않는 레시피북 - CookbookNotFoundError"""
        service = CookbookService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.get_cookbook_by_id(
                "00000000-0000-0000-0000-000000000000", user_id
            )

    async def test_get_other_user_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        other_user: User,
        other_user_cookbook: Cookbook,
    ):
        """다른 사용자의 레시피북 - CookbookNotFoundError"""
        service = CookbookService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.get_cookbook_by_id(other_user_cookbook.id, user_id)


@pytest.mark.asyncio
class TestUpdateCookbook:
    """update_cookbook 테스트"""

    async def test_update_cookbook_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        sample_cookbook: Cookbook,
    ):
        """레시피북 수정 성공"""
        service = CookbookService(db_session)
        data = CookbookUpdateRequest(name="수정된 이름")

        # When
        result = await service.update_cookbook(sample_cookbook.id, user_id, data)

        # Then
        assert result.name == "수정된 이름"
        assert result.description == sample_cookbook.description  # 변경 안 됨

    async def test_update_cookbook_partial(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        sample_cookbook: Cookbook,
    ):
        """부분 수정 - 전달된 필드만 변경"""
        service = CookbookService(db_session)
        original_description = sample_cookbook.description
        data = CookbookUpdateRequest(name="변경된 이름만")

        # When
        result = await service.update_cookbook(sample_cookbook.id, user_id, data)

        # Then
        assert result.name == "변경된 이름만"
        assert result.description == original_description

    async def test_update_default_cookbook_allowed(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """기본 레시피북도 수정 가능"""
        service = CookbookService(db_session)
        data = CookbookUpdateRequest(name="수정된 기본 레시피북")

        # When
        result = await service.update_cookbook(default_cookbook.id, user_id, data)

        # Then
        assert result.name == "수정된 기본 레시피북"
        assert result.is_default is True


@pytest.mark.asyncio
class TestDeleteCookbook:
    """delete_cookbook 테스트"""

    async def test_delete_cookbook_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        sample_cookbook: Cookbook,
    ):
        """레시피북 삭제 성공"""
        service = CookbookService(db_session)

        # When
        await service.delete_cookbook(sample_cookbook.id, user_id)

        # Then: 조회 시 NotFound
        with pytest.raises(CookbookNotFoundError):
            await service.get_cookbook_by_id(sample_cookbook.id, user_id)

    async def test_delete_default_cookbook_forbidden(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """기본 레시피북 삭제 시도 - CannotDeleteDefaultCookbookError"""
        service = CookbookService(db_session)

        # When/Then
        with pytest.raises(CannotDeleteDefaultCookbookError):
            await service.delete_cookbook(default_cookbook.id, user_id)

    async def test_delete_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """존재하지 않는 레시피북 삭제 - CookbookNotFoundError"""
        service = CookbookService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.delete_cookbook(
                "00000000-0000-0000-0000-000000000000", user_id
            )


@pytest.mark.asyncio
class TestReorderCookbooks:
    """reorder_cookbooks 테스트"""

    async def test_reorder_cookbooks_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        multiple_cookbooks: list[Cookbook],
    ):
        """순서 변경 성공"""
        service = CookbookService(db_session)

        # Given: 역순으로 변경
        new_order = [cb.id for cb in reversed(multiple_cookbooks)]

        # When
        result = await service.reorder_cookbooks(user_id, new_order)

        # Then: 반환된 목록은 sort_order 순 정렬
        sort_orders = [item.sort_order for item in result.items]
        assert sort_orders == sorted(sort_orders)

    async def test_reorder_ignores_invalid_ids(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """유효하지 않은 ID는 무시됨"""
        service = CookbookService(db_session)

        # Given: 존재하지 않는 ID 포함
        order = ["00000000-0000-0000-0000-000000000000", default_cookbook.id]

        # When: 에러 없이 성공
        result = await service.reorder_cookbooks(user_id, order)

        # Then
        assert result.total >= 1

    async def test_reorder_ignores_other_user_ids(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        other_user: User,
        other_user_cookbook: Cookbook,
    ):
        """다른 사용자의 ID는 무시됨"""
        service = CookbookService(db_session)

        # Given: 다른 사용자 ID 포함
        order = [other_user_cookbook.id, default_cookbook.id]

        # When
        result = await service.reorder_cookbooks(user_id, order)

        # Then: 다른 사용자 것은 무시, 본인 것만 순서 변경됨
        assert result.total >= 1
        cookbook_ids = [item.id for item in result.items]
        assert other_user_cookbook.id not in cookbook_ids
