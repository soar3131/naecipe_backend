"""
레시피 서비스

레시피 조회 비즈니스 로직을 담당합니다.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from recipe_service.cache.redis_cache import RedisCache, get_redis_cache
from recipe_service.middleware.error_handler import RecipeNotFoundError
from recipe_service.models import Recipe, RecipeIngredient, CookingStep, RecipeTag
from recipe_service.schemas import RecipeDetail, RecipeListItem, RecipeListResponse
from recipe_service.schemas.pagination import (
    CursorData,
    PaginationParams,
    create_next_cursor,
    decode_cursor,
    paginate_response,
)

logger = logging.getLogger(__name__)


class RecipeService:
    """레시피 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: RedisCache | None = None

    async def _get_cache(self) -> RedisCache:
        """Redis 캐시 인스턴스 반환"""
        if self._cache is None:
            self._cache = await get_redis_cache()
        return self._cache

    async def get_by_id(self, recipe_id: str) -> RecipeDetail:
        """
        레시피 상세 조회

        Args:
            recipe_id: 레시피 ID

        Returns:
            RecipeDetail: 레시피 상세 정보

        Raises:
            RecipeNotFoundError: 레시피가 존재하지 않는 경우
        """
        cache = await self._get_cache()
        cache_key = cache.recipe_key(recipe_id)

        # 1. 캐시 조회
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for recipe: {recipe_id}")
            return RecipeDetail.model_validate(cached_data)

        # 2. DB 조회 (eager loading)
        logger.debug(f"Cache miss for recipe: {recipe_id}")
        stmt = (
            select(Recipe)
            .where(Recipe.id == recipe_id)
            .where(Recipe.is_active == True)  # noqa: E712
            .options(
                joinedload(Recipe.chef),
                selectinload(Recipe.ingredients),
                selectinload(Recipe.steps),
                selectinload(Recipe.recipe_tags).joinedload(RecipeTag.tag),
            )
        )
        result = await self.session.execute(stmt)
        recipe = result.unique().scalar_one_or_none()

        if not recipe:
            raise RecipeNotFoundError(recipe_id)

        # 3. 스키마 변환
        recipe_detail = RecipeDetail.from_model(recipe)

        # 4. 캐시 저장
        await cache.set(
            cache_key,
            recipe_detail.model_dump(mode="json"),
            ttl=RedisCache.RECIPE_TTL,
        )

        return recipe_detail

    async def get_list(
        self,
        pagination: PaginationParams,
        tag: str | None = None,
        difficulty: str | None = None,
    ) -> RecipeListResponse:
        """
        레시피 목록 조회 (커서 기반 페이지네이션)

        Args:
            pagination: 페이지네이션 파라미터
            tag: 태그 필터 (옵션)
            difficulty: 난이도 필터 (옵션)

        Returns:
            RecipeListResponse: 레시피 목록과 페이지네이션 정보
        """
        cache = await self._get_cache()
        cache_key = cache.recipes_list_key(pagination.cursor, pagination.limit)

        # 필터가 없을 때만 캐시 사용
        if not tag and not difficulty:
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.debug("Cache hit for recipes list")
                return RecipeListResponse.model_validate(cached_data)

        # 기본 쿼리
        stmt = (
            select(Recipe)
            .where(Recipe.is_active == True)  # noqa: E712
            .options(
                joinedload(Recipe.chef),
                selectinload(Recipe.recipe_tags).joinedload(RecipeTag.tag),
            )
        )

        # 필터 적용
        if difficulty:
            stmt = stmt.where(Recipe.difficulty == difficulty)

        if tag:
            stmt = stmt.join(Recipe.recipe_tags).join(RecipeTag.tag)
            from recipe_service.models import Tag
            stmt = stmt.where(Tag.name == tag)

        # 커서 기반 페이지네이션
        if pagination.cursor:
            cursor_data = decode_cursor(pagination.cursor)
            if cursor_data:
                # 노출 점수와 생성일 기준 정렬
                stmt = stmt.where(
                    (Recipe.exposure_score < cursor_data.score) |
                    (
                        (Recipe.exposure_score == cursor_data.score) &
                        (Recipe.created_at < cursor_data.created_at)
                    )
                )

        # 정렬 및 limit
        stmt = stmt.order_by(
            Recipe.exposure_score.desc(),
            Recipe.created_at.desc(),
        ).limit(pagination.limit + 1)  # +1 for has_more check

        result = await self.session.execute(stmt)
        recipes = list(result.unique().scalars().all())

        # has_more 확인
        has_more = len(recipes) > pagination.limit
        if has_more:
            recipes = recipes[:pagination.limit]

        # 스키마 변환
        items = [self._to_list_item(recipe) for recipe in recipes]

        # 다음 커서 생성
        next_cursor = None
        if has_more and recipes:
            next_cursor = create_next_cursor(
                items=recipes,
                id_field="id",
                timestamp_field="created_at",
                score_field="exposure_score",
            )

        response = RecipeListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            total_count=None,  # 커서 기반에서는 total_count 제공 안 함
        )

        # 필터 없을 때만 캐시
        if not tag and not difficulty:
            await cache.set(
                cache_key,
                response.model_dump(mode="json"),
                ttl=RedisCache.RECIPE_LIST_TTL,
            )

        return response

    async def get_popular(
        self,
        limit: int = 10,
        category: str | None = None,
    ) -> list[RecipeListItem]:
        """
        인기 레시피 조회

        Args:
            limit: 조회 개수 (기본 10개, 최대 50개)
            category: 카테고리 필터 (옵션)

        Returns:
            list[RecipeListItem]: 인기 레시피 목록
        """
        limit = min(limit, 50)  # 최대 50개 제한

        cache = await self._get_cache()
        cache_key = cache.popular_recipes_key(category, limit)

        # 캐시 조회
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug("Cache hit for popular recipes")
            return [RecipeListItem.model_validate(item) for item in cached_data]

        # DB 조회
        stmt = (
            select(Recipe)
            .where(Recipe.is_active == True)  # noqa: E712
            .options(
                joinedload(Recipe.chef),
                selectinload(Recipe.recipe_tags).joinedload(RecipeTag.tag),
            )
        )

        if category:
            stmt = stmt.join(Recipe.recipe_tags).join(RecipeTag.tag)
            from recipe_service.models import Tag
            stmt = stmt.where(Tag.category == category)

        stmt = stmt.order_by(
            Recipe.exposure_score.desc(),
            Recipe.view_count.desc(),
        ).limit(limit)

        result = await self.session.execute(stmt)
        recipes = list(result.unique().scalars().all())

        items = [self._to_list_item(recipe) for recipe in recipes]

        # 캐시 저장
        await cache.set(
            cache_key,
            [item.model_dump(mode="json") for item in items],
            ttl=RedisCache.POPULAR_TTL,
        )

        return items

    async def get_by_chef(
        self,
        chef_id: str,
        pagination: PaginationParams,
    ) -> RecipeListResponse:
        """
        요리사별 레시피 조회 (커서 기반 페이지네이션)

        Args:
            chef_id: 요리사 ID
            pagination: 페이지네이션 파라미터

        Returns:
            RecipeListResponse: 레시피 목록과 페이지네이션 정보
        """
        cache = await self._get_cache()
        cache_key = cache.chef_recipes_key(chef_id, pagination.cursor, pagination.limit)

        # 캐시 조회
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for chef recipes: {chef_id}")
            return RecipeListResponse.model_validate(cached_data)

        # 기본 쿼리
        stmt = (
            select(Recipe)
            .where(Recipe.chef_id == chef_id)
            .where(Recipe.is_active == True)  # noqa: E712
            .options(
                joinedload(Recipe.chef),
                selectinload(Recipe.recipe_tags).joinedload(RecipeTag.tag),
            )
        )

        # 커서 기반 페이지네이션
        if pagination.cursor:
            cursor_data = decode_cursor(pagination.cursor)
            if cursor_data:
                stmt = stmt.where(
                    (Recipe.created_at < cursor_data.created_at) |
                    (
                        (Recipe.created_at == cursor_data.created_at) &
                        (Recipe.id < cursor_data.id)
                    )
                )

        # 정렬 및 limit
        stmt = stmt.order_by(
            Recipe.created_at.desc(),
            Recipe.id.desc(),
        ).limit(pagination.limit + 1)

        result = await self.session.execute(stmt)
        recipes = list(result.unique().scalars().all())

        # has_more 확인
        has_more = len(recipes) > pagination.limit
        if has_more:
            recipes = recipes[:pagination.limit]

        # 스키마 변환
        items = [self._to_list_item(recipe) for recipe in recipes]

        # 다음 커서 생성
        next_cursor = None
        if has_more and recipes:
            next_cursor = create_next_cursor(
                items=recipes,
                id_field="id",
                timestamp_field="created_at",
                score_field="exposure_score",
            )

        response = RecipeListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            total_count=None,
        )

        # 캐시 저장
        await cache.set(
            cache_key,
            response.model_dump(mode="json"),
            ttl=RedisCache.RECIPE_LIST_TTL,
        )

        return response

    def _to_list_item(self, recipe: Recipe) -> RecipeListItem:
        """Recipe 모델을 RecipeListItem으로 변환"""
        from recipe_service.schemas import ChefSummary, TagSchema

        chef = None
        if recipe.chef:
            chef = ChefSummary.model_validate(recipe.chef)

        tags = [
            TagSchema.model_validate(rt.tag)
            for rt in recipe.recipe_tags
            if rt.tag
        ]

        return RecipeListItem(
            id=recipe.id,
            title=recipe.title,
            description=recipe.description,
            thumbnail_url=recipe.thumbnail_url,
            prep_time_minutes=recipe.prep_time_minutes,
            cook_time_minutes=recipe.cook_time_minutes,
            difficulty=recipe.difficulty,
            exposure_score=recipe.exposure_score,
            chef=chef,
            tags=tags,
            created_at=recipe.created_at,
        )


async def get_recipe_service(session: AsyncSession) -> RecipeService:
    """RecipeService 의존성 주입"""
    return RecipeService(session)
