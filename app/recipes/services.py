"""
Recipes 모듈 서비스

레시피, 요리사, 검색 비즈니스 로직을 담당합니다.
"""

import base64
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.infra.redis import get_redis_cache
from app.recipes.models import (
    Chef,
    ChefPlatform,
    CookingStep,
    Recipe,
    RecipeIngredient,
    RecipeTag,
    Tag,
)
from app.recipes.schemas import (
    ChefDetail,
    ChefListItem,
    ChefListResponse,
    ChefPlatformSchema,
    ChefSummary,
    CursorData,
    PaginationParams,
    RecipeDetail,
    RecipeListItem,
    RecipeListResponse,
    SearchQueryParams,
    SearchResult,
    SearchResultItem,
    TagSchema,
    TagSummary,
)

logger = logging.getLogger(__name__)


# ==========================================================================
# 커서 유틸리티
# ==========================================================================


class CursorError(Exception):
    """커서 관련 예외"""

    pass


def encode_cursor_simple(sort: str, value: Any, recipe_id: str) -> str:
    """커서 인코딩 (검색용)"""
    if isinstance(value, datetime):
        value = value.isoformat()
    data = {"s": sort, "v": value, "i": recipe_id}
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor_simple(cursor: str) -> tuple[str, Any, str]:
    """커서 디코딩 (검색용)"""
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)
        return data["s"], data["v"], data["i"]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise CursorError(f"잘못된 커서 형식: {e}") from e


def encode_cursor(data: CursorData) -> str:
    """커서 데이터를 Base64 문자열로 인코딩"""
    json_str = data.model_dump_json()
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor_str: str) -> CursorData | None:
    """Base64 커서 문자열을 CursorData로 디코딩"""
    try:
        json_str = base64.urlsafe_b64decode(cursor_str.encode()).decode()
        data = json.loads(json_str)
        return CursorData.model_validate(data)
    except Exception:
        return None


def create_next_cursor(
    items: list[Any],
    id_field: str = "id",
    timestamp_field: str | None = "created_at",
    score_field: str | None = None,
) -> str | None:
    """아이템 목록에서 다음 커서 생성"""
    if not items:
        return None

    last_item = items[-1]

    def get_value(obj: Any, field: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

    item_id = get_value(last_item, id_field)
    if item_id is None:
        return None

    if isinstance(item_id, UUID):
        item_id = str(item_id)

    cursor_data = CursorData(
        id=item_id,
        created_at=get_value(last_item, timestamp_field) if timestamp_field else None,
        score=get_value(last_item, score_field) if score_field else None,
    )

    return encode_cursor(cursor_data)


# ==========================================================================
# Redis 캐시 키 생성 헬퍼
# ==========================================================================


class RecipeCacheKeys:
    """레시피 관련 캐시 키 생성"""

    # 기본 TTL 설정 (초)
    RECIPE_TTL = 3600  # 1시간
    RECIPE_LIST_TTL = 300  # 5분
    POPULAR_TTL = 600  # 10분
    CHEF_TTL = 3600  # 1시간
    SEARCH_CACHE_TTL = 300  # 5분

    @staticmethod
    def recipe_key(recipe_id: str) -> str:
        """레시피 캐시 키"""
        return f"recipe:{recipe_id}"

    @staticmethod
    def recipes_list_key(cursor: str | None = None, limit: int = 20) -> str:
        """레시피 목록 캐시 키"""
        cursor_part = cursor or "first"
        return f"recipes:list:{cursor_part}:{limit}"

    @staticmethod
    def popular_recipes_key(category: str | None = None, limit: int = 10) -> str:
        """인기 레시피 캐시 키"""
        category_part = category or "all"
        return f"recipes:popular:{category_part}:{limit}"

    @staticmethod
    def chef_key(chef_id: str) -> str:
        """요리사 캐시 키"""
        return f"chef:{chef_id}"

    @staticmethod
    def chef_recipes_key(
        chef_id: str, cursor: str | None = None, limit: int = 20
    ) -> str:
        """요리사별 레시피 캐시 키"""
        cursor_part = cursor or "first"
        return f"chef:{chef_id}:recipes:{cursor_part}:{limit}"


# ==========================================================================
# 레시피 서비스
# ==========================================================================


class RecipeService:
    """레시피 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, recipe_id: str) -> RecipeDetail:
        """
        레시피 상세 조회

        Args:
            recipe_id: 레시피 ID

        Returns:
            RecipeDetail: 레시피 상세 정보

        Raises:
            NotFoundError: 레시피가 존재하지 않는 경우
        """
        cache = await get_redis_cache()
        cache_key = RecipeCacheKeys.recipe_key(recipe_id)

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
        result = await self.db.execute(stmt)
        recipe = result.unique().scalar_one_or_none()

        if not recipe:
            raise NotFoundError(resource="Recipe", resource_id=recipe_id)

        # 3. 스키마 변환
        recipe_detail = RecipeDetail.from_model(recipe)

        # 4. 캐시 저장
        await cache.set(
            cache_key,
            recipe_detail.model_dump(mode="json"),
            ttl=RecipeCacheKeys.RECIPE_TTL,
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
        """
        cache = await get_redis_cache()
        cache_key = RecipeCacheKeys.recipes_list_key(pagination.cursor, pagination.limit)

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
            stmt = stmt.where(Tag.name == tag)

        # 커서 기반 페이지네이션
        if pagination.cursor:
            cursor_data = decode_cursor(pagination.cursor)
            if cursor_data:
                stmt = stmt.where(
                    (Recipe.exposure_score < cursor_data.score)
                    | (
                        (Recipe.exposure_score == cursor_data.score)
                        & (Recipe.created_at < cursor_data.created_at)
                    )
                )

        # 정렬 및 limit
        stmt = stmt.order_by(
            Recipe.exposure_score.desc(),
            Recipe.created_at.desc(),
        ).limit(pagination.limit + 1)

        result = await self.db.execute(stmt)
        recipes = list(result.unique().scalars().all())

        # has_more 확인
        has_more = len(recipes) > pagination.limit
        if has_more:
            recipes = recipes[: pagination.limit]

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

        # 필터 없을 때만 캐시
        if not tag and not difficulty:
            await cache.set(
                cache_key,
                response.model_dump(mode="json"),
                ttl=RecipeCacheKeys.RECIPE_LIST_TTL,
            )

        return response

    async def get_popular(
        self,
        limit: int = 10,
        category: str | None = None,
    ) -> list[RecipeListItem]:
        """인기 레시피 조회"""
        limit = min(limit, 50)

        cache = await get_redis_cache()
        cache_key = RecipeCacheKeys.popular_recipes_key(category, limit)

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
            stmt = stmt.where(Tag.category == category)

        stmt = stmt.order_by(
            Recipe.exposure_score.desc(),
            Recipe.view_count.desc(),
        ).limit(limit)

        result = await self.db.execute(stmt)
        recipes = list(result.unique().scalars().all())

        items = [self._to_list_item(recipe) for recipe in recipes]

        # 캐시 저장
        await cache.set(
            cache_key,
            [item.model_dump(mode="json") for item in items],
            ttl=RecipeCacheKeys.POPULAR_TTL,
        )

        return items

    async def get_by_chef(
        self,
        chef_id: str,
        pagination: PaginationParams,
    ) -> RecipeListResponse:
        """요리사별 레시피 조회 (커서 기반 페이지네이션)"""
        cache = await get_redis_cache()
        cache_key = RecipeCacheKeys.chef_recipes_key(
            chef_id, pagination.cursor, pagination.limit
        )

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
                    (Recipe.created_at < cursor_data.created_at)
                    | (
                        (Recipe.created_at == cursor_data.created_at)
                        & (Recipe.id < cursor_data.id)
                    )
                )

        # 정렬 및 limit
        stmt = stmt.order_by(
            Recipe.created_at.desc(),
            Recipe.id.desc(),
        ).limit(pagination.limit + 1)

        result = await self.db.execute(stmt)
        recipes = list(result.unique().scalars().all())

        # has_more 확인
        has_more = len(recipes) > pagination.limit
        if has_more:
            recipes = recipes[: pagination.limit]

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
            ttl=RecipeCacheKeys.RECIPE_LIST_TTL,
        )

        return response

    def _to_list_item(self, recipe: Recipe) -> RecipeListItem:
        """Recipe 모델을 RecipeListItem으로 변환"""
        chef = None
        if recipe.chef:
            chef = ChefSummary.model_validate(recipe.chef)

        tags = [
            TagSchema.model_validate(rt.tag) for rt in recipe.recipe_tags if rt.tag
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


# ==========================================================================
# 요리사 서비스
# ==========================================================================


class ChefService:
    """요리사 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, chef_id: str) -> ChefDetail:
        """
        요리사 상세 조회

        Args:
            chef_id: 요리사 ID

        Returns:
            ChefDetail: 요리사 상세 정보

        Raises:
            NotFoundError: 요리사가 존재하지 않는 경우
        """
        cache = await get_redis_cache()
        cache_key = RecipeCacheKeys.chef_key(chef_id)

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
        result = await self.db.execute(stmt)
        chef = result.scalar_one_or_none()

        if not chef:
            raise NotFoundError(resource="Chef", resource_id=chef_id)

        # 3. 스키마 변환
        chef_detail = self._to_detail(chef)

        # 4. 캐시 저장
        await cache.set(
            cache_key,
            chef_detail.model_dump(mode="json"),
            ttl=RecipeCacheKeys.CHEF_TTL,
        )

        return chef_detail

    async def get_list(
        self,
        pagination: PaginationParams,
        specialty: str | None = None,
        is_verified: bool | None = None,
    ) -> ChefListResponse:
        """요리사 목록 조회 (커서 기반 페이지네이션)"""
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
                    (Chef.recipe_count < cursor_data.score)
                    | (
                        (Chef.recipe_count == cursor_data.score)
                        & (Chef.created_at < cursor_data.created_at)
                    )
                )

        # 정렬 및 limit
        stmt = stmt.order_by(
            Chef.recipe_count.desc(),
            Chef.created_at.desc(),
        ).limit(pagination.limit + 1)

        result = await self.db.execute(stmt)
        chefs = list(result.scalars().all())

        # has_more 확인
        has_more = len(chefs) > pagination.limit
        if has_more:
            chefs = chefs[: pagination.limit]

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
        """인기 요리사 조회"""
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

        result = await self.db.execute(stmt)
        chefs = list(result.scalars().all())

        return [self._to_list_item(chef) for chef in chefs]

    def _to_detail(self, chef: Chef) -> ChefDetail:
        """Chef 모델을 ChefDetail로 변환"""
        platforms = [ChefPlatformSchema.model_validate(p) for p in chef.platforms]

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


# ==========================================================================
# 검색 서비스
# ==========================================================================


class SearchService:
    """검색 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_search_cache_key(self, params: SearchQueryParams) -> str:
        """검색 파라미터로 캐시 키 생성"""
        cache_params = {
            "q": params.q or "",
            "d": params.difficulty or "",
            "t": params.max_cook_time or 0,
            "tag": params.tag or "",
            "c": str(params.chef_id) if params.chef_id else "",
            "s": params.sort,
            "cur": params.cursor or "",
            "l": params.limit,
        }
        hash_input = json.dumps(cache_params, sort_keys=True)
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:16]
        return f"search:recipes:{hash_value}"

    def _build_keyword_conditions(self, keyword: str) -> list:
        """키워드 검색 조건 구성"""
        like_pattern = f"%{keyword}%"
        conditions = []

        # 제목, 설명에서 검색
        conditions.append(Recipe.title.ilike(like_pattern))
        conditions.append(Recipe.description.ilike(like_pattern))

        # 재료명 서브쿼리
        ingredient_subq = (
            select(RecipeIngredient.recipe_id)
            .where(RecipeIngredient.name.ilike(like_pattern))
            .distinct()
            .scalar_subquery()
        )
        conditions.append(Recipe.id.in_(ingredient_subq))

        # 요리사명 서브쿼리
        chef_subq = (
            select(Recipe.id)
            .join(Chef, Recipe.chef_id == Chef.id)
            .where(Chef.name.ilike(like_pattern))
            .scalar_subquery()
        )
        conditions.append(Recipe.id.in_(chef_subq))

        return conditions

    def _apply_filters(
        self,
        stmt,
        difficulty: str | None,
        max_cook_time: int | None,
        chef_id: UUID | None,
        tag: str | None,
    ):
        """필터링 조건 적용"""
        if difficulty:
            stmt = stmt.where(Recipe.difficulty == difficulty)

        if max_cook_time:
            stmt = stmt.where(Recipe.cook_time_minutes <= max_cook_time)

        if chef_id:
            stmt = stmt.where(Recipe.chef_id == str(chef_id))

        if tag:
            tag_subq = (
                select(RecipeTag.recipe_id)
                .join(Tag, RecipeTag.tag_id == Tag.id)
                .where(Tag.name == tag)
                .scalar_subquery()
            )
            stmt = stmt.where(Recipe.id.in_(tag_subq))

        return stmt

    def _apply_sort(self, stmt, sort: str):
        """정렬 조건 적용"""
        if sort == "relevance":
            stmt = stmt.order_by(Recipe.exposure_score.desc(), Recipe.id.desc())
        elif sort == "latest":
            stmt = stmt.order_by(Recipe.created_at.desc(), Recipe.id.desc())
        elif sort == "cook_time":
            stmt = stmt.order_by(
                Recipe.cook_time_minutes.asc().nulls_last(), Recipe.id.asc()
            )
        elif sort == "popularity":
            stmt = stmt.order_by(Recipe.view_count.desc(), Recipe.id.desc())

        return stmt

    def _apply_cursor(self, stmt, cursor: str | None, sort: str):
        """커서 조건 적용 (페이지네이션)"""
        if not cursor:
            return stmt

        try:
            cursor_sort, cursor_value, cursor_id = decode_cursor_simple(cursor)

            # 커서의 정렬 기준과 현재 정렬 기준이 일치하는지 확인
            if cursor_sort != sort:
                raise CursorError("커서의 정렬 기준이 현재 요청과 일치하지 않습니다")

            if sort == "relevance":
                stmt = stmt.where(
                    or_(
                        Recipe.exposure_score < cursor_value,
                        (Recipe.exposure_score == cursor_value)
                        & (Recipe.id < cursor_id),
                    )
                )
            elif sort == "latest":
                cursor_dt = datetime.fromisoformat(cursor_value)
                stmt = stmt.where(
                    or_(
                        Recipe.created_at < cursor_dt,
                        (Recipe.created_at == cursor_dt) & (Recipe.id < cursor_id),
                    )
                )
            elif sort == "cook_time":
                stmt = stmt.where(
                    or_(
                        Recipe.cook_time_minutes > cursor_value,
                        (Recipe.cook_time_minutes == cursor_value)
                        & (Recipe.id > cursor_id),
                    )
                )
            elif sort == "popularity":
                stmt = stmt.where(
                    or_(
                        Recipe.view_count < cursor_value,
                        (Recipe.view_count == cursor_value) & (Recipe.id < cursor_id),
                    )
                )

        except CursorError:
            raise
        except Exception as e:
            raise CursorError(f"커서 처리 중 오류: {e}") from e

        return stmt

    def _create_next_cursor(self, recipe: Recipe, sort: str) -> str:
        """다음 페이지 커서 생성"""
        if sort == "relevance":
            return encode_cursor_simple(sort, recipe.exposure_score, recipe.id)
        elif sort == "latest":
            return encode_cursor_simple(sort, recipe.created_at, recipe.id)
        elif sort == "cook_time":
            return encode_cursor_simple(sort, recipe.cook_time_minutes or 0, recipe.id)
        elif sort == "popularity":
            return encode_cursor_simple(sort, recipe.view_count, recipe.id)
        else:
            return encode_cursor_simple(sort, recipe.exposure_score, recipe.id)

    def _recipe_to_search_item(self, recipe: Recipe) -> SearchResultItem:
        """Recipe 모델을 SearchResultItem으로 변환"""
        chef_summary = None
        if recipe.chef:
            chef_summary = ChefSummary(
                id=recipe.chef.id,
                name=recipe.chef.name,
                profile_image_url=recipe.chef.profile_image_url,
            )

        tags = []
        for rt in recipe.recipe_tags:
            if rt.tag:
                tags.append(
                    TagSummary(
                        id=rt.tag.id,
                        name=rt.tag.name,
                        category=rt.tag.category,
                    )
                )

        return SearchResultItem(
            id=recipe.id,
            title=recipe.title,
            description=recipe.description,
            thumbnail_url=recipe.thumbnail_url,
            prep_time_minutes=recipe.prep_time_minutes,
            cook_time_minutes=recipe.cook_time_minutes,
            difficulty=recipe.difficulty,
            exposure_score=recipe.exposure_score,
            chef=chef_summary,
            tags=tags,
            created_at=recipe.created_at,
        )

    async def search(self, params: SearchQueryParams) -> SearchResult:
        """레시피 검색"""
        start_time = time.perf_counter()
        cache_hit = False
        result_count = 0

        # 구조화된 로깅을 위한 파라미터 정보
        search_context = {
            "keyword": params.q,
            "difficulty": params.difficulty,
            "max_cook_time": params.max_cook_time,
            "tag": params.tag,
            "chef_id": str(params.chef_id) if params.chef_id else None,
            "sort": params.sort,
            "limit": params.limit,
            "has_cursor": params.cursor is not None,
        }

        logger.info(
            "Search request started",
            extra={"search_params": search_context},
        )

        # 캐시 확인
        cache_key = ""
        try:
            cache = await get_redis_cache()
            cache_key = self._get_search_cache_key(params)
            cached = await cache.get(cache_key)
            if cached:
                cache_hit = True
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                result = SearchResult.model_validate_json(cached)
                result_count = len(result.items)
                logger.info(
                    "Search completed (cache hit)",
                    extra={
                        "cache_hit": True,
                        "result_count": result_count,
                        "elapsed_ms": round(elapsed_ms, 2),
                        "cache_key": cache_key,
                    },
                )
                return result
        except Exception as e:
            logger.warning(
                "Cache lookup failed",
                extra={
                    "error": str(e),
                    "cache_key": cache_key if cache_key else None,
                },
            )

        # 기본 쿼리 구성
        stmt = (
            select(Recipe)
            .where(Recipe.is_active == True)
            .options(
                joinedload(Recipe.chef),
                selectinload(Recipe.recipe_tags).joinedload(RecipeTag.tag),
            )
        )

        # 키워드 검색 조건
        if params.q:
            keyword_conditions = self._build_keyword_conditions(params.q)
            stmt = stmt.where(or_(*keyword_conditions))

        # 필터링 조건
        stmt = self._apply_filters(
            stmt, params.difficulty, params.max_cook_time, params.chef_id, params.tag
        )

        # 정렬 적용
        stmt = self._apply_sort(stmt, params.sort)

        # 커서 조건 적용
        stmt = self._apply_cursor(stmt, params.cursor, params.sort)

        # limit + 1 로 조회 (has_more 판단용)
        stmt = stmt.limit(params.limit + 1)

        # 쿼리 실행
        db_result = await self.db.execute(stmt)
        recipes = list(db_result.scalars().unique())

        # has_more 판단 및 결과 자르기
        has_more = len(recipes) > params.limit
        if has_more:
            recipes = recipes[: params.limit]

        # 다음 커서 생성
        next_cursor = None
        if has_more and recipes:
            next_cursor = self._create_next_cursor(recipes[-1], params.sort)

        # 결과 변환
        items = [self._recipe_to_search_item(recipe) for recipe in recipes]

        result = SearchResult(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            total_count=None,
        )
        result_count = len(items)

        # 캐시 저장
        try:
            cache = await get_redis_cache()
            await cache.set(
                cache_key, result.model_dump_json(), ttl=RecipeCacheKeys.SEARCH_CACHE_TTL
            )
        except Exception as e:
            logger.warning(
                "Cache set failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 완료 로깅
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Search completed (db query)",
            extra={
                "cache_hit": False,
                "result_count": result_count,
                "has_more": has_more,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )

        return result
