"""
SavedRecipeService 단위 테스트 (SPEC-008)

저장된 레시피 서비스 레이어 비즈니스 로직 테스트
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cookbooks.exceptions import (
    CookbookNotFoundError,
    RecipeAlreadySavedError,
    SavedRecipeNotFoundError,
)
from app.cookbooks.models import Cookbook, SavedRecipe
from app.cookbooks.schemas import SaveRecipeRequest, UpdateSavedRecipeRequest
from app.cookbooks.services import SavedRecipeService
from app.recipes.models import Chef, Recipe
from app.users.models import User


# ==========================================================================
# save_recipe 테스트 (User Story 1)
# ==========================================================================


@pytest.mark.asyncio
class TestSaveRecipe:
    """save_recipe 메서드 테스트 (T014)"""

    async def test_save_recipe_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """레시피 저장 성공"""
        # Given
        service = SavedRecipeService(db_session)
        data = SaveRecipeRequest(recipe_id=sample_recipe.id)

        # When
        result = await service.save_recipe(default_cookbook.id, user_id, data)

        # Then
        assert result.cookbook_id == default_cookbook.id
        assert result.recipe is not None
        assert result.recipe.id == sample_recipe.id
        assert result.recipe.title == sample_recipe.title
        assert result.memo is None
        assert result.cook_count == 0

    async def test_save_recipe_with_memo(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """메모와 함께 레시피 저장"""
        # Given
        service = SavedRecipeService(db_session)
        data = SaveRecipeRequest(
            recipe_id=sample_recipe.id,
            memo="백종원 레시피! 돼지고기 300g 필요",
        )

        # When
        result = await service.save_recipe(default_cookbook.id, user_id, data)

        # Then
        assert result.memo == "백종원 레시피! 돼지고기 300g 필요"

    async def test_save_recipe_duplicate_raises_error(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
        sample_recipe: Recipe,
    ):
        """중복 저장 시 RecipeAlreadySavedError 발생"""
        # Given: 이미 저장된 레시피
        service = SavedRecipeService(db_session)
        data = SaveRecipeRequest(recipe_id=sample_recipe.id)

        # When/Then
        with pytest.raises(RecipeAlreadySavedError):
            await service.save_recipe(default_cookbook.id, user_id, data)

    async def test_save_recipe_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        sample_recipe: Recipe,
    ):
        """존재하지 않는 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)
        data = SaveRecipeRequest(recipe_id=sample_recipe.id)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.save_recipe(
                "00000000-0000-0000-0000-000000000000", user_id, data
            )

    async def test_save_recipe_other_user_cookbook(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        other_user: User,
        other_user_cookbook: Cookbook,
        sample_recipe: Recipe,
    ):
        """다른 사용자의 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)
        data = SaveRecipeRequest(recipe_id=sample_recipe.id)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.save_recipe(other_user_cookbook.id, user_id, data)


# ==========================================================================
# list_saved_recipes 테스트 (User Story 2)
# ==========================================================================


@pytest.mark.asyncio
class TestListSavedRecipes:
    """list_saved_recipes 메서드 테스트"""

    async def test_list_saved_recipes_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        multiple_saved_recipes: list[SavedRecipe],
    ):
        """저장된 레시피 목록 조회 성공"""
        # Given
        service = SavedRecipeService(db_session)

        # When
        result = await service.list_saved_recipes(default_cookbook.id, user_id)

        # Then
        assert result.total == len(multiple_saved_recipes)
        assert result.limit == 20  # 기본값
        assert result.offset == 0  # 기본값
        assert len(result.items) == len(multiple_saved_recipes)

    async def test_list_saved_recipes_empty(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """빈 목록 조회"""
        # Given: 저장된 레시피가 없음
        service = SavedRecipeService(db_session)

        # When
        result = await service.list_saved_recipes(default_cookbook.id, user_id)

        # Then
        assert result.total == 0
        assert result.items == []

    async def test_list_saved_recipes_pagination(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        multiple_saved_recipes: list[SavedRecipe],
    ):
        """페이지네이션"""
        # Given
        service = SavedRecipeService(db_session)

        # When: limit=1, offset=1
        result = await service.list_saved_recipes(
            default_cookbook.id, user_id, limit=1, offset=1
        )

        # Then
        assert result.limit == 1
        assert result.offset == 1
        assert len(result.items) == 1
        assert result.total == len(multiple_saved_recipes)

    async def test_list_saved_recipes_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
    ):
        """존재하지 않는 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.list_saved_recipes(
                "00000000-0000-0000-0000-000000000000", user_id
            )

    async def test_list_saved_recipes_includes_recipe_info(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
        sample_recipe: Recipe,
    ):
        """원본 레시피 정보 포함"""
        # Given
        service = SavedRecipeService(db_session)

        # When
        result = await service.list_saved_recipes(default_cookbook.id, user_id)

        # Then
        assert len(result.items) == 1
        item = result.items[0]
        assert item.recipe is not None
        assert item.recipe.id == sample_recipe.id
        assert item.recipe.title == sample_recipe.title


# ==========================================================================
# get_saved_recipe 테스트 (User Story 3)
# ==========================================================================


@pytest.mark.asyncio
class TestGetSavedRecipe:
    """get_saved_recipe 메서드 테스트"""

    async def test_get_saved_recipe_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
        sample_recipe: Recipe,
    ):
        """저장된 레시피 상세 조회 성공"""
        # Given
        service = SavedRecipeService(db_session)

        # When
        result = await service.get_saved_recipe(
            default_cookbook.id, saved_recipe.id, user_id
        )

        # Then
        assert result.id == saved_recipe.id
        assert result.cookbook_id == default_cookbook.id
        assert result.recipe is not None
        assert result.recipe.id == sample_recipe.id
        assert result.memo == saved_recipe.memo

    async def test_get_saved_recipe_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """존재하지 않는 저장 레시피 - SavedRecipeNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)

        # When/Then
        with pytest.raises(SavedRecipeNotFoundError):
            await service.get_saved_recipe(
                default_cookbook.id,
                "00000000-0000-0000-0000-000000000000",
                user_id,
            )

    async def test_get_saved_recipe_wrong_cookbook(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        sample_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """다른 레시피북에서 조회 - SavedRecipeNotFoundError"""
        # Given: saved_recipe는 default_cookbook에 속함
        service = SavedRecipeService(db_session)

        # When/Then: sample_cookbook으로 조회 시도
        with pytest.raises(SavedRecipeNotFoundError):
            await service.get_saved_recipe(
                sample_cookbook.id, saved_recipe.id, user_id
            )

    async def test_get_saved_recipe_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        saved_recipe: SavedRecipe,
    ):
        """존재하지 않는 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.get_saved_recipe(
                "00000000-0000-0000-0000-000000000000",
                saved_recipe.id,
                user_id,
            )


# ==========================================================================
# update_saved_recipe 테스트 (User Story 4)
# ==========================================================================


@pytest.mark.asyncio
class TestUpdateSavedRecipe:
    """update_saved_recipe 메서드 테스트"""

    async def test_update_saved_recipe_memo(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """메모 수정 성공"""
        # Given
        service = SavedRecipeService(db_session)
        data = UpdateSavedRecipeRequest(memo="수정된 메모입니다")

        # When
        result = await service.update_saved_recipe(
            default_cookbook.id, saved_recipe.id, user_id, data
        )

        # Then
        assert result.memo == "수정된 메모입니다"

    async def test_update_saved_recipe_clear_memo(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """메모 삭제 (null로 설정)"""
        # Given: 기존 메모가 있음
        service = SavedRecipeService(db_session)
        data = UpdateSavedRecipeRequest(memo=None)

        # When
        result = await service.update_saved_recipe(
            default_cookbook.id, saved_recipe.id, user_id, data
        )

        # Then
        assert result.memo is None

    async def test_update_saved_recipe_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """존재하지 않는 저장 레시피 - SavedRecipeNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)
        data = UpdateSavedRecipeRequest(memo="새 메모")

        # When/Then
        with pytest.raises(SavedRecipeNotFoundError):
            await service.update_saved_recipe(
                default_cookbook.id,
                "00000000-0000-0000-0000-000000000000",
                user_id,
                data,
            )

    async def test_update_saved_recipe_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        saved_recipe: SavedRecipe,
    ):
        """존재하지 않는 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)
        data = UpdateSavedRecipeRequest(memo="새 메모")

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.update_saved_recipe(
                "00000000-0000-0000-0000-000000000000",
                saved_recipe.id,
                user_id,
                data,
            )


# ==========================================================================
# delete_saved_recipe 테스트 (User Story 5)
# ==========================================================================


@pytest.mark.asyncio
class TestDeleteSavedRecipe:
    """delete_saved_recipe 메서드 테스트"""

    async def test_delete_saved_recipe_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """저장된 레시피 삭제 성공"""
        # Given
        service = SavedRecipeService(db_session)

        # When
        await service.delete_saved_recipe(
            default_cookbook.id, saved_recipe.id, user_id
        )

        # Then: 다시 조회하면 NotFound
        with pytest.raises(SavedRecipeNotFoundError):
            await service.get_saved_recipe(
                default_cookbook.id, saved_recipe.id, user_id
            )

    async def test_delete_saved_recipe_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        default_cookbook: Cookbook,
    ):
        """존재하지 않는 저장 레시피 - SavedRecipeNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)

        # When/Then
        with pytest.raises(SavedRecipeNotFoundError):
            await service.delete_saved_recipe(
                default_cookbook.id,
                "00000000-0000-0000-0000-000000000000",
                user_id,
            )

    async def test_delete_saved_recipe_cookbook_not_found(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        saved_recipe: SavedRecipe,
    ):
        """존재하지 않는 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.delete_saved_recipe(
                "00000000-0000-0000-0000-000000000000",
                saved_recipe.id,
                user_id,
            )

    async def test_delete_saved_recipe_other_user(
        self,
        db_session: AsyncSession,
        test_user: User,
        user_id: str,
        other_user: User,
        other_user_cookbook: Cookbook,
        saved_recipe: SavedRecipe,
    ):
        """다른 사용자의 레시피북 - CookbookNotFoundError"""
        # Given
        service = SavedRecipeService(db_session)

        # When/Then
        with pytest.raises(CookbookNotFoundError):
            await service.delete_saved_recipe(
                other_user_cookbook.id, saved_recipe.id, user_id
            )
