"""
Cookbooks 모듈 서비스

레시피북 비즈니스 로직을 담당합니다.
"""

import logging
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cookbooks.exceptions import (
    CannotDeleteDefaultCookbookError,
    CookbookNotFoundError,
)
from app.cookbooks.models import Cookbook
from app.cookbooks.schemas import (
    CookbookCreateRequest,
    CookbookListResponse,
    CookbookResponse,
    CookbookUpdateRequest,
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
