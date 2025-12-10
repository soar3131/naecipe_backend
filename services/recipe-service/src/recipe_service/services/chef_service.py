"""
요리사 서비스

요리사 조회 비즈니스 로직을 담당합니다.
"""

import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from recipe_service.cache.redis_cache import RedisCache, get_redis_cache
from recipe_service.middleware.error_handler import ChefNotFoundError
from recipe_service.models import Chef, ChefPlatform
from recipe_service.schemas import (
    ChefDetail,
    ChefListItem,
    ChefListResponse,
    ChefPlatformSchema,
)
from recipe_service.schemas.pagination import (
    CursorData,
    PaginationParams,
    create_next_cursor,
    decode_cursor,
)

logger = logging.getLogger(__name__)


class ChefService:
    """요리사 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: RedisCache | None = None

    async def _get_cache(self) -> RedisCache:
        """Redis 캐시 인스턴스 반환"""
        if self._cache is None:
            self._cache = await get_redis_cache()
        return self._cache

    async def get_by_id(self, chef_id: str) -> ChefDetail:
        """
        요리사 상세 조회

        Args:
            chef_id: 요리사 ID

        Returns:
            ChefDetail: 요리사 상세 정보

        Raises:
            ChefNotFoundError: 요리사가 존재하지 않는 경우
        """
        cache = await self._get_cache()
        cache_key = cache.chef_key(chef_id)

        # 1. 캐시 조회
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for chef: {chef_id}")
            return ChefDetail.model_validate(cached_data)

        # 2. DB 조회
        logger.debug(f"Cache miss for chef: {chef_id}")
        stmt = (
            select(Chef)
            .where(Chef.id == chef_id)
            .options(
                selectinload(Chef.platforms),
            )
        )
        result = await self.session.execute(stmt)
        chef = result.scalar_one_or_none()

        if not chef:
            raise ChefNotFoundError(chef_id)

        # 3. 스키마 변환
        chef_detail = self._to_detail(chef)

        # 4. 캐시 저장
        await cache.set(
            cache_key,
            chef_detail.model_dump(mode="json"),
            ttl=RedisCache.CHEF_TTL,
        )

        return chef_detail

    async def get_list(
        self,
        pagination: PaginationParams,
        specialty: str | None = None,
        is_verified: bool | None = None,
    ) -> ChefListResponse:
        """
        요리사 목록 조회 (커서 기반 페이지네이션)

        Args:
            pagination: 페이지네이션 파라미터
            specialty: 전문 분야 필터 (옵션)
            is_verified: 인증 여부 필터 (옵션)

        Returns:
            ChefListResponse: 요리사 목록과 페이지네이션 정보
        """
        # 기본 쿼리
        stmt = select(Chef)

        # 필터 적용
        if specialty:
            stmt = stmt.where(Chef.specialty == specialty)
        if is_verified is not None:
            stmt = stmt.where(Chef.is_verified == is_verified)

        # 커서 기반 페이지네이션
        if pagination.cursor:
            cursor_data = decode_cursor(pagination.cursor)
            if cursor_data:
                stmt = stmt.where(
                    (Chef.recipe_count < cursor_data.score) |
                    (
                        (Chef.recipe_count == cursor_data.score) &
                        (Chef.created_at < cursor_data.created_at)
                    )
                )

        # 정렬 및 limit
        stmt = stmt.order_by(
            Chef.recipe_count.desc(),
            Chef.created_at.desc(),
        ).limit(pagination.limit + 1)

        result = await self.session.execute(stmt)
        chefs = list(result.scalars().all())

        # has_more 확인
        has_more = len(chefs) > pagination.limit
        if has_more:
            chefs = chefs[:pagination.limit]

        # 스키마 변환
        items = [self._to_list_item(chef) for chef in chefs]

        # 다음 커서 생성
        next_cursor = None
        if has_more and chefs:
            next_cursor = create_next_cursor(
                items=chefs,
                id_field="id",
                timestamp_field="created_at",
                score_field="recipe_count",
            )

        return ChefListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            total_count=None,
        )

    async def get_popular(
        self,
        limit: int = 10,
    ) -> list[ChefListItem]:
        """
        인기 요리사 조회

        Args:
            limit: 조회 개수 (기본 10개, 최대 50개)

        Returns:
            list[ChefListItem]: 인기 요리사 목록
        """
        limit = min(limit, 50)

        # DB 조회 (레시피 수와 총 조회수 기준 정렬)
        stmt = (
            select(Chef)
            .where(Chef.is_verified == True)  # noqa: E712
            .order_by(
                Chef.recipe_count.desc(),
                Chef.total_views.desc(),
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        chefs = list(result.scalars().all())

        return [self._to_list_item(chef) for chef in chefs]

    def _to_detail(self, chef: Chef) -> ChefDetail:
        """Chef 모델을 ChefDetail로 변환"""
        platforms = [
            ChefPlatformSchema.model_validate(p) for p in chef.platforms
        ]

        return ChefDetail(
            id=chef.id,
            name=chef.name,
            profile_image_url=chef.profile_image_url,
            bio=chef.bio,
            specialty=chef.specialty,
            recipe_count=chef.recipe_count,
            total_views=chef.total_views,
            avg_rating=chef.avg_rating,
            is_verified=chef.is_verified,
            platforms=platforms,
            created_at=chef.created_at,
            updated_at=chef.updated_at,
        )

    def _to_list_item(self, chef: Chef) -> ChefListItem:
        """Chef 모델을 ChefListItem으로 변환"""
        return ChefListItem(
            id=chef.id,
            name=chef.name,
            profile_image_url=chef.profile_image_url,
            specialty=chef.specialty,
            recipe_count=chef.recipe_count,
            is_verified=chef.is_verified,
        )


async def get_chef_service(session: AsyncSession) -> ChefService:
    """ChefService 의존성 주입"""
    return ChefService(session)
