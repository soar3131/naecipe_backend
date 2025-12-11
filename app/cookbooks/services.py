"""
Cookbooks 모듈 서비스

레시피북 및 저장된 레시피 비즈니스 로직을 담당합니다.
"""

import logging
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.cookbooks.exceptions import (
    CannotDeleteDefaultCookbookError,
    CookbookNotFoundError,
    RecipeAlreadySavedError,
    SavedRecipeNotFoundError,
)
from app.cookbooks.models import Cookbook, SavedRecipe
from app.recipes.models import Recipe
from app.cookbooks.schemas import (
    CookbookCreateRequest,
    CookbookListResponse,
    CookbookResponse,
    CookbookUpdateRequest,
    RecipeSummary,
    SavedRecipeDetailResponse,
    SavedRecipeListResponse,
    SavedRecipeResponse,
    SaveRecipeRequest,
    UpdateSavedRecipeRequest,
)

logger = logging.getLogger(__name__)


class CookbookService:
    """레시피북 서비스"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ==========================================================================
    # 기본 레시피북 관리
    # ==========================================================================

    async def ensure_default_cookbook(self, user_id: str) -> Cookbook:
        """
        기본 레시피북이 없으면 생성하고 반환 (Lazy Creation)

        첫 레시피북 조회 또는 레시피 저장 시 자동 호출됨
        """
        # 기존 기본 레시피북 조회
        stmt = select(Cookbook).where(
            Cookbook.user_id == user_id,
            Cookbook.is_default == True,  # noqa: E712
        )
        default_cookbook = await self.session.scalar(stmt)

        if default_cookbook:
            logger.debug(
                "기본 레시피북 존재",
                extra={"user_id": user_id, "cookbook_id": default_cookbook.id},
            )
            return default_cookbook

        # 기본 레시피북 생성
        new_cookbook = Cookbook(
            id=str(uuid4()),
            user_id=user_id,
            name="내 레시피북",
            is_default=True,
            sort_order=0,
        )
        self.session.add(new_cookbook)
        await self.session.flush()

        logger.info(
            "기본 레시피북 생성됨",
            extra={"user_id": user_id, "cookbook_id": new_cookbook.id},
        )
        return new_cookbook

    # ==========================================================================
    # CRUD 메서드
    # ==========================================================================

    async def create_cookbook(
        self,
        user_id: str,
        data: CookbookCreateRequest,
    ) -> CookbookResponse:
        """
        새 레시피북 생성

        is_default=False로 생성, sort_order는 현재 최대값 + 1
        """
        # 기본 레시피북 보장 (없으면 생성)
        await self.ensure_default_cookbook(user_id)

        # 현재 최대 sort_order 조회
        max_sort_stmt = select(func.max(Cookbook.sort_order)).where(
            Cookbook.user_id == user_id
        )
        max_sort = await self.session.scalar(max_sort_stmt) or 0

        # 새 레시피북 생성
        cookbook = Cookbook(
            id=str(uuid4()),
            user_id=user_id,
            name=data.name,
            description=data.description,
            cover_image_url=data.cover_image_url,
            is_default=False,
            sort_order=max_sort + 1,
        )
        self.session.add(cookbook)
        await self.session.flush()

        logger.info(
            "레시피북 생성됨",
            extra={
                "user_id": user_id,
                "cookbook_id": cookbook.id,
                "name": cookbook.name,
            },
        )

        return CookbookResponse(
            id=cookbook.id,
            name=cookbook.name,
            description=cookbook.description,
            cover_image_url=cookbook.cover_image_url,
            sort_order=cookbook.sort_order,
            is_default=cookbook.is_default,
            saved_recipe_count=0,
            created_at=cookbook.created_at,
            updated_at=cookbook.updated_at,
        )

    async def get_cookbooks(self, user_id: str) -> CookbookListResponse:
        """
        사용자의 모든 레시피북 목록 조회

        - 기본 레시피북이 없으면 자동 생성
        - sort_order 오름차순 정렬
        - saved_recipe_count 포함 (서브쿼리 COUNT)
        """
        # 기본 레시피북 보장
        await self.ensure_default_cookbook(user_id)

        # TODO: saved_recipe_count 서브쿼리 추가 (SPEC-008 구현 후)
        # 현재는 0으로 반환
        stmt = (
            select(Cookbook)
            .where(Cookbook.user_id == user_id)
            .order_by(Cookbook.sort_order)
        )
        result = await self.session.scalars(stmt)
        cookbooks = result.all()

        items = [
            CookbookResponse(
                id=cb.id,
                name=cb.name,
                description=cb.description,
                cover_image_url=cb.cover_image_url,
                sort_order=cb.sort_order,
                is_default=cb.is_default,
                saved_recipe_count=0,  # TODO: 실제 카운트로 변경
                created_at=cb.created_at,
                updated_at=cb.updated_at,
            )
            for cb in cookbooks
        ]

        logger.debug(
            "레시피북 목록 조회",
            extra={"user_id": user_id, "count": len(items)},
        )

        return CookbookListResponse(items=items, total=len(items))

    async def get_cookbook_by_id(
        self,
        cookbook_id: str,
        user_id: str,
    ) -> CookbookResponse:
        """
        레시피북 상세 조회

        - 사용자 소유의 레시피북만 조회 가능
        - 없거나 권한 없으면 404 반환 (보안상 존재 여부 숨김)
        """
        stmt = select(Cookbook).where(
            Cookbook.id == cookbook_id,
            Cookbook.user_id == user_id,
        )
        cookbook = await self.session.scalar(stmt)

        if not cookbook:
            logger.warning(
                "레시피북 조회 실패",
                extra={
                    "cookbook_id": cookbook_id,
                    "user_id": user_id,
                    "reason": "not_found_or_unauthorized",
                },
            )
            raise CookbookNotFoundError(cookbook_id)

        logger.debug(
            "레시피북 상세 조회",
            extra={"cookbook_id": cookbook_id, "user_id": user_id},
        )

        return CookbookResponse(
            id=cookbook.id,
            name=cookbook.name,
            description=cookbook.description,
            cover_image_url=cookbook.cover_image_url,
            sort_order=cookbook.sort_order,
            is_default=cookbook.is_default,
            saved_recipe_count=0,  # TODO: 실제 카운트로 변경
            created_at=cookbook.created_at,
            updated_at=cookbook.updated_at,
        )

    async def update_cookbook(
        self,
        cookbook_id: str,
        user_id: str,
        data: CookbookUpdateRequest,
    ) -> CookbookResponse:
        """
        레시피북 수정

        - 사용자 소유의 레시피북만 수정 가능
        - 기본 레시피북도 수정 가능 (이름 변경 포함)
        """
        stmt = select(Cookbook).where(
            Cookbook.id == cookbook_id,
            Cookbook.user_id == user_id,
        )
        cookbook = await self.session.scalar(stmt)

        if not cookbook:
            logger.warning(
                "레시피북 수정 실패",
                extra={
                    "cookbook_id": cookbook_id,
                    "user_id": user_id,
                    "reason": "not_found_or_unauthorized",
                },
            )
            raise CookbookNotFoundError(cookbook_id)

        # 전달된 필드만 업데이트
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cookbook, field, value)

        await self.session.flush()

        logger.info(
            "레시피북 수정됨",
            extra={
                "cookbook_id": cookbook_id,
                "user_id": user_id,
                "updated_fields": list(update_data.keys()),
            },
        )

        return CookbookResponse(
            id=cookbook.id,
            name=cookbook.name,
            description=cookbook.description,
            cover_image_url=cookbook.cover_image_url,
            sort_order=cookbook.sort_order,
            is_default=cookbook.is_default,
            saved_recipe_count=0,  # TODO: 실제 카운트로 변경
            created_at=cookbook.created_at,
            updated_at=cookbook.updated_at,
        )

    async def delete_cookbook(
        self,
        cookbook_id: str,
        user_id: str,
    ) -> None:
        """
        레시피북 삭제

        - 사용자 소유의 레시피북만 삭제 가능
        - 기본 레시피북(is_default=True)은 삭제 불가
        - 삭제 시 CASCADE로 saved_recipes도 함께 삭제됨
        """
        stmt = select(Cookbook).where(
            Cookbook.id == cookbook_id,
            Cookbook.user_id == user_id,
        )
        cookbook = await self.session.scalar(stmt)

        if not cookbook:
            logger.warning(
                "레시피북 삭제 실패",
                extra={
                    "cookbook_id": cookbook_id,
                    "user_id": user_id,
                    "reason": "not_found_or_unauthorized",
                },
            )
            raise CookbookNotFoundError(cookbook_id)

        if cookbook.is_default:
            logger.warning(
                "기본 레시피북 삭제 시도",
                extra={"cookbook_id": cookbook_id, "user_id": user_id},
            )
            raise CannotDeleteDefaultCookbookError()

        await self.session.delete(cookbook)
        await self.session.flush()

        logger.info(
            "레시피북 삭제됨",
            extra={"cookbook_id": cookbook_id, "user_id": user_id},
        )

    async def reorder_cookbooks(
        self,
        user_id: str,
        cookbook_ids: list[str],
    ) -> CookbookListResponse:
        """
        레시피북 순서 변경

        - 전달된 ID 목록 순서대로 1부터 재할당
        - 본인 소유가 아닌 ID는 무시
        - 목록에 없는 레시피북은 순서 유지
        """
        # 사용자 소유 레시피북 ID 목록 조회
        stmt = select(Cookbook.id).where(Cookbook.user_id == user_id)
        result = await self.session.scalars(stmt)
        user_cookbook_ids = set(result.all())

        # 전달된 ID 중 유효한 것만 필터링
        valid_ids = [cid for cid in cookbook_ids if cid in user_cookbook_ids]

        # 순서 재할당 (1부터 시작)
        for index, cookbook_id in enumerate(valid_ids, start=1):
            stmt = (
                update(Cookbook)
                .where(Cookbook.id == cookbook_id, Cookbook.user_id == user_id)
                .values(sort_order=index)
            )
            await self.session.execute(stmt)

        await self.session.flush()

        logger.info(
            "레시피북 순서 변경됨",
            extra={
                "user_id": user_id,
                "new_order": valid_ids,
            },
        )

        # 업데이트된 목록 반환
        return await self.get_cookbooks(user_id)

    # ==========================================================================
    # SavedRecipe 관련 헬퍼 메서드 (SPEC-008)
    # ==========================================================================

    async def get_cookbook_for_user(
        self,
        cookbook_id: str,
        user_id: str,
    ) -> Cookbook:
        """
        사용자 소유의 레시피북 조회 (내부용)

        - 사용자 소유의 레시피북만 조회 가능
        - 없거나 권한 없으면 CookbookNotFoundError 발생
        """
        stmt = select(Cookbook).where(
            Cookbook.id == cookbook_id,
            Cookbook.user_id == user_id,
        )
        cookbook = await self.session.scalar(stmt)

        if not cookbook:
            raise CookbookNotFoundError(cookbook_id)

        return cookbook


# ==========================================================================
# SavedRecipe 서비스 (SPEC-008)
# ==========================================================================


class SavedRecipeService:
    """저장된 레시피 서비스"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cookbook_service = CookbookService(session)

    # ==========================================================================
    # 레시피 저장 (US1)
    # ==========================================================================

    async def save_recipe(
        self,
        cookbook_id: str,
        user_id: str,
        data: SaveRecipeRequest,
    ) -> SavedRecipeResponse:
        """
        레시피를 레시피북에 저장

        - 사용자 소유의 레시피북에만 저장 가능
        - 동일 레시피 중복 저장 시 409 Conflict
        - 존재하지 않는 레시피 저장 시 404 Not Found
        """
        # 레시피북 소유권 확인
        cookbook = await self.cookbook_service.get_cookbook_for_user(
            cookbook_id, user_id
        )

        # 레시피 존재 확인은 FK 제약조건으로 처리
        # (IntegrityError 발생 시 RecipeNotFoundError로 변환)

        # 저장된 레시피 생성
        saved_recipe = SavedRecipe(
            id=str(uuid4()),
            cookbook_id=cookbook.id,
            original_recipe_id=data.recipe_id,
            memo=data.memo,
        )

        try:
            self.session.add(saved_recipe)
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig) if e.orig else str(e)

            # UNIQUE 제약조건 위반 (중복 저장)
            if "uq_saved_recipes_cookbook_recipe" in error_msg:
                logger.warning(
                    "레시피 중복 저장 시도",
                    extra={
                        "cookbook_id": cookbook_id,
                        "recipe_id": data.recipe_id,
                        "user_id": user_id,
                    },
                )
                raise RecipeAlreadySavedError(data.recipe_id, cookbook_id)

            # FK 제약조건 위반 (레시피 미존재)
            if "recipes" in error_msg.lower():
                from app.core.exceptions import RecipeNotFoundError

                raise RecipeNotFoundError(data.recipe_id)

            raise

        logger.info(
            "레시피 저장됨",
            extra={
                "saved_recipe_id": saved_recipe.id,
                "cookbook_id": cookbook_id,
                "recipe_id": data.recipe_id,
                "user_id": user_id,
            },
        )

        # 원본 레시피 정보 조회를 위해 다시 로드
        await self.session.refresh(saved_recipe, ["original_recipe"])

        return self._to_response(saved_recipe)

    # ==========================================================================
    # 목록 조회 (US2)
    # ==========================================================================

    async def list_saved_recipes(
        self,
        cookbook_id: str,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> SavedRecipeListResponse:
        """
        저장된 레시피 목록 조회

        - 사용자 소유의 레시피북만 조회 가능
        - 페이지네이션 지원 (limit/offset)
        - 저장 시간 내림차순 정렬
        """
        # 레시피북 소유권 확인
        await self.cookbook_service.get_cookbook_for_user(cookbook_id, user_id)

        # 전체 개수 조회
        count_stmt = (
            select(func.count())
            .select_from(SavedRecipe)
            .where(SavedRecipe.cookbook_id == cookbook_id)
        )
        total = await self.session.scalar(count_stmt) or 0

        # 목록 조회 (원본 레시피 조인)
        stmt = (
            select(SavedRecipe)
            .options(joinedload(SavedRecipe.original_recipe))
            .where(SavedRecipe.cookbook_id == cookbook_id)
            .order_by(SavedRecipe.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        saved_recipes = result.unique().all()

        items = [self._to_response(sr) for sr in saved_recipes]

        logger.debug(
            "저장된 레시피 목록 조회",
            extra={
                "cookbook_id": cookbook_id,
                "user_id": user_id,
                "count": len(items),
                "total": total,
            },
        )

        return SavedRecipeListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ==========================================================================
    # 상세 조회 (US3)
    # ==========================================================================

    async def get_saved_recipe(
        self,
        cookbook_id: str,
        saved_recipe_id: str,
        user_id: str,
    ) -> SavedRecipeDetailResponse:
        """
        저장된 레시피 상세 조회

        - 사용자 소유의 레시피북만 조회 가능
        - 원본 레시피 상세 정보 포함
        """
        # 레시피북 소유권 확인
        await self.cookbook_service.get_cookbook_for_user(cookbook_id, user_id)

        # 저장된 레시피 조회
        stmt = (
            select(SavedRecipe)
            .options(joinedload(SavedRecipe.original_recipe))
            .where(
                SavedRecipe.id == saved_recipe_id,
                SavedRecipe.cookbook_id == cookbook_id,
            )
        )
        saved_recipe = await self.session.scalar(stmt)

        if not saved_recipe:
            raise SavedRecipeNotFoundError(saved_recipe_id)

        logger.debug(
            "저장된 레시피 상세 조회",
            extra={
                "saved_recipe_id": saved_recipe_id,
                "cookbook_id": cookbook_id,
                "user_id": user_id,
            },
        )

        return self._to_detail_response(saved_recipe)

    # ==========================================================================
    # 수정 (US4)
    # ==========================================================================

    async def update_saved_recipe(
        self,
        cookbook_id: str,
        saved_recipe_id: str,
        user_id: str,
        data: UpdateSavedRecipeRequest,
    ) -> SavedRecipeResponse:
        """
        저장된 레시피 수정 (메모)

        - 사용자 소유의 레시피북만 수정 가능
        - 메모만 수정 가능
        """
        # 레시피북 소유권 확인
        await self.cookbook_service.get_cookbook_for_user(cookbook_id, user_id)

        # 저장된 레시피 조회
        stmt = (
            select(SavedRecipe)
            .options(
                joinedload(SavedRecipe.original_recipe).joinedload(Recipe.chef)
            )
            .where(
                SavedRecipe.id == saved_recipe_id,
                SavedRecipe.cookbook_id == cookbook_id,
            )
        )
        saved_recipe = await self.session.scalar(stmt)

        if not saved_recipe:
            raise SavedRecipeNotFoundError(saved_recipe_id)

        # 메모 업데이트
        saved_recipe.memo = data.memo
        await self.session.flush()

        # flush 후 전체 객체 새로고침 (lazy loading 방지)
        await self.session.refresh(saved_recipe)
        # 관계 다시 로드
        stmt = (
            select(SavedRecipe)
            .options(
                joinedload(SavedRecipe.original_recipe).joinedload(Recipe.chef)
            )
            .where(SavedRecipe.id == saved_recipe_id)
        )
        saved_recipe = await self.session.scalar(stmt)

        logger.info(
            "저장된 레시피 수정됨",
            extra={
                "saved_recipe_id": saved_recipe_id,
                "cookbook_id": cookbook_id,
                "user_id": user_id,
            },
        )

        return self._to_response(saved_recipe)

    # ==========================================================================
    # 삭제 (US5)
    # ==========================================================================

    async def delete_saved_recipe(
        self,
        cookbook_id: str,
        saved_recipe_id: str,
        user_id: str,
    ) -> None:
        """
        저장된 레시피 삭제

        - 사용자 소유의 레시피북만 삭제 가능
        - CASCADE로 연관된 RecipeVariation도 삭제 (SPEC-009)
        """
        # 레시피북 소유권 확인
        await self.cookbook_service.get_cookbook_for_user(cookbook_id, user_id)

        # 저장된 레시피 조회
        stmt = select(SavedRecipe).where(
            SavedRecipe.id == saved_recipe_id,
            SavedRecipe.cookbook_id == cookbook_id,
        )
        saved_recipe = await self.session.scalar(stmt)

        if not saved_recipe:
            raise SavedRecipeNotFoundError(saved_recipe_id)

        await self.session.delete(saved_recipe)
        await self.session.flush()

        logger.info(
            "저장된 레시피 삭제됨",
            extra={
                "saved_recipe_id": saved_recipe_id,
                "cookbook_id": cookbook_id,
                "user_id": user_id,
            },
        )

    # ==========================================================================
    # 응답 변환 헬퍼
    # ==========================================================================

    def _to_response(self, saved_recipe: SavedRecipe) -> SavedRecipeResponse:
        """SavedRecipe 모델을 응답 스키마로 변환"""
        recipe_summary = None
        if saved_recipe.original_recipe:
            recipe = saved_recipe.original_recipe
            chef_name = None
            if hasattr(recipe, "chef") and recipe.chef:
                chef_name = recipe.chef.name

            recipe_summary = RecipeSummary(
                id=recipe.id,
                title=recipe.title,
                thumbnail_url=recipe.thumbnail_url,
                chef_name=chef_name,
            )

        return SavedRecipeResponse(
            id=saved_recipe.id,
            cookbook_id=saved_recipe.cookbook_id,
            recipe=recipe_summary,
            memo=saved_recipe.memo,
            cook_count=saved_recipe.cook_count,
            personal_rating=(
                float(saved_recipe.personal_rating)
                if saved_recipe.personal_rating
                else None
            ),
            last_cooked_at=saved_recipe.last_cooked_at,
            created_at=saved_recipe.created_at,
            updated_at=saved_recipe.updated_at,
        )

    def _to_detail_response(
        self, saved_recipe: SavedRecipe
    ) -> SavedRecipeDetailResponse:
        """SavedRecipe 모델을 상세 응답 스키마로 변환"""
        # 현재는 기본 응답과 동일
        # 추후 RecipeDetail 전체 정보 포함으로 확장
        response = self._to_response(saved_recipe)
        return SavedRecipeDetailResponse(**response.model_dump())
