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
    CategoryPopularItem,
    CategoryPopularListResponse,
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
    RelatedByTagsItem,
    RelatedByTagsListResponse,
    SameChefRecipeItem,
    SameChefRecipeListResponse,
    SearchQueryParams,
    SearchResult,
    SearchResultItem,
    SimilarRecipeItem,
    SimilarRecipeListResponse,
    TagSchema,
    TagSummary,
    TagSummarySchema,
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

    # 유사 레시피 TTL 설정 (초)
    SIMILAR_RECIPES_TTL = 600  # 10분
    SAME_CHEF_RECIPES_TTL = 600  # 10분
    RELATED_BY_TAGS_TTL = 600  # 10분
    CATEGORY_POPULAR_TTL = 600  # 10분

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
    # 유사 레시피 캐시 키
    # ==========================================================================

    @staticmethod
    def similar_recipes_key(
        recipe_id: str, cursor: str | None = None, limit: int = 10
    ) -> str:
        """유사 레시피 캐시 키"""
        cursor_part = cursor or "first"
        return f"recipes:{recipe_id}:similar:{cursor_part}:{limit}"

    @staticmethod
    def same_chef_recipes_key(
        recipe_id: str, cursor: str | None = None, limit: int = 10
    ) -> str:
        """같은 요리사 레시피 캐시 키"""
        cursor_part = cursor or "first"
        return f"recipes:{recipe_id}:same-chef:{cursor_part}:{limit}"

    @staticmethod
    def related_by_tags_key(
        recipe_id: str, cursor: str | None = None, limit: int = 10
    ) -> str:
        """태그 기반 관련 레시피 캐시 키"""
        cursor_part = cursor or "first"
        return f"recipes:{recipe_id}:related-by-tags:{cursor_part}:{limit}"

    @staticmethod
    def category_popular_key(
        recipe_id: str, category: str, cursor: str | None = None, limit: int = 10
    ) -> str:
        """카테고리 인기 레시피 캐시 키"""
        cursor_part = cursor or "first"
        return f"recipes:{recipe_id}:category-popular:{category}:{cursor_part}:{limit}"

    @staticmethod
    def invalidate_similar_recipes_pattern(recipe_id: str) -> str:
        """유사 레시피 캐시 무효화 패턴 (레시피 수정/삭제 시)"""
        return f"recipes:{recipe_id}:*"


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


# =============================================================================
# 유사 레시피 추천 서비스
# =============================================================================


class SimilarRecipeService:
    """
    유사 레시피 추천 서비스

    4가지 추천 유형 제공:
    - 유사 레시피: 태그/재료/조리방식 기반 유사도 계산
    - 같은 요리사 레시피: 동일 요리사의 다른 레시피
    - 관련 태그 레시피: 공유 태그 기반 추천
    - 카테고리 인기 레시피: 동일 카테고리 내 인기순
    """

    # 유사도 가중치 (총합 = 1.0)
    WEIGHT_TAGS = 0.4
    WEIGHT_INGREDIENTS = 0.4
    WEIGHT_COOKING = 0.2

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 기준 레시피 조회 헬퍼
    # =========================================================================

    async def _get_base_recipe(self, recipe_id: str) -> Recipe:
        """기준 레시피 조회 (태그, 재료 정보 포함)"""
        stmt = (
            select(Recipe)
            .options(
                selectinload(Recipe.recipe_tags).selectinload(RecipeTag.tag),
                selectinload(Recipe.ingredients),
                joinedload(Recipe.chef),
            )
            .where(Recipe.id == recipe_id)
            .where(Recipe.is_active == True)  # noqa: E712
        )

        result = await self.db.execute(stmt)
        recipe = result.unique().scalar_one_or_none()

        if not recipe:
            raise NotFoundError(f"레시피를 찾을 수 없습니다: {recipe_id}")

        return recipe

    # =========================================================================
    # 유사도 계산 헬퍼 메서드 (T011, T012, T013)
    # =========================================================================

    def _calculate_tag_similarity(
        self,
        base_tag_ids: set[str],
        candidate_tag_ids: set[str],
    ) -> float:
        """
        태그 기반 유사도 계산 (Jaccard 유사도)

        T011: 태그 기반 유사도 = 교집합 / 합집합
        """
        if not base_tag_ids or not candidate_tag_ids:
            return 0.0

        intersection = len(base_tag_ids & candidate_tag_ids)
        union = len(base_tag_ids | candidate_tag_ids)

        return intersection / union if union > 0 else 0.0

    def _calculate_ingredient_similarity(
        self,
        base_ingredient_names: set[str],
        candidate_ingredient_names: set[str],
    ) -> float:
        """
        재료 기반 유사도 계산 (Jaccard 유사도)

        T012: 재료 기반 유사도 = 공통 재료 / 전체 재료
        """
        if not base_ingredient_names or not candidate_ingredient_names:
            return 0.0

        # 재료명 정규화 (공백 제거, 소문자화)
        base_normalized = {name.strip().lower() for name in base_ingredient_names}
        candidate_normalized = {name.strip().lower() for name in candidate_ingredient_names}

        intersection = len(base_normalized & candidate_normalized)
        union = len(base_normalized | candidate_normalized)

        return intersection / union if union > 0 else 0.0

    def _calculate_cooking_similarity(
        self,
        base_recipe: Recipe,
        candidate: Recipe,
    ) -> float:
        """
        조리법 유사도 계산 (조리시간 + 난이도)

        T013: 조리법 유사도 = (시간 유사도 * 0.5) + (난이도 유사도 * 0.5)
        """
        time_similarity = 0.0
        difficulty_similarity = 0.0

        # 조리시간 유사도 (차이가 적을수록 높은 점수)
        if base_recipe.cook_time_minutes and candidate.cook_time_minutes:
            time_diff = abs(base_recipe.cook_time_minutes - candidate.cook_time_minutes)
            # 30분 차이까지 선형 감소 (30분 이상이면 0)
            time_similarity = max(0.0, 1.0 - (time_diff / 30.0))
        elif base_recipe.cook_time_minutes is None and candidate.cook_time_minutes is None:
            time_similarity = 0.5  # 둘 다 없으면 중립

        # 난이도 유사도 (동일하면 1.0, 다르면 0.5 또는 0.0)
        if base_recipe.difficulty and candidate.difficulty:
            if base_recipe.difficulty == candidate.difficulty:
                difficulty_similarity = 1.0
            else:
                # 난이도 순서: easy < medium < hard
                difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
                base_order = difficulty_order.get(base_recipe.difficulty, 1)
                candidate_order = difficulty_order.get(candidate.difficulty, 1)
                diff = abs(base_order - candidate_order)
                difficulty_similarity = 1.0 - (diff * 0.5)  # 1단계 차이 0.5, 2단계 차이 0.0
        elif base_recipe.difficulty is None and candidate.difficulty is None:
            difficulty_similarity = 0.5

        return (time_similarity * 0.5) + (difficulty_similarity * 0.5)

    def _calculate_combined_similarity(
        self,
        base_recipe: Recipe,
        candidate: Recipe,
        base_tag_ids: set[str],
        base_ingredient_names: set[str],
    ) -> float:
        """
        통합 유사도 계산

        T014: 태그(40%) + 재료(40%) + 조리법(20%)
        """
        # 후보 레시피의 태그 ID 추출
        candidate_tag_ids = {rt.tag_id for rt in candidate.recipe_tags}

        # 후보 레시피의 재료명 추출
        candidate_ingredient_names = {ing.name for ing in candidate.ingredients}

        # 각 유사도 계산
        tag_sim = self._calculate_tag_similarity(base_tag_ids, candidate_tag_ids)
        ingredient_sim = self._calculate_ingredient_similarity(
            base_ingredient_names, candidate_ingredient_names
        )
        cooking_sim = self._calculate_cooking_similarity(base_recipe, candidate)

        # 가중 합산
        combined = (
            tag_sim * self.WEIGHT_TAGS
            + ingredient_sim * self.WEIGHT_INGREDIENTS
            + cooking_sim * self.WEIGHT_COOKING
        )

        return round(combined, 4)

    # =========================================================================
    # 캐시 헬퍼 메서드 (T039: 캐시 관리)
    # =========================================================================

    # 캐시 TTL (10분)
    CACHE_TTL_SECONDS = 600

    async def _get_from_cache(self, cache_key: str) -> dict | None:
        """캐시에서 데이터 조회"""
        try:
            cache = await get_redis_cache()
            cached = await cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(
                "Cache read failed",
                extra={"error": str(e), "cache_key": cache_key},
            )
        return None

    async def _set_to_cache(self, cache_key: str, data: dict) -> None:
        """캐시에 데이터 저장 (10분 TTL)"""
        try:
            cache = await get_redis_cache()
            await cache.setex(cache_key, self.CACHE_TTL_SECONDS, json.dumps(data))
        except Exception as e:
            logger.warning(
                "Cache write failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

    async def invalidate_recipe_cache(self, recipe_id: str) -> None:
        """
        레시피 관련 캐시 무효화

        레시피 수정/삭제 시 호출하여 관련된 모든 캐시를 삭제합니다.
        """
        try:
            cache = await get_redis_cache()

            # 패턴 기반 캐시 삭제
            patterns = [
                f"similar:*{recipe_id}*",
                f"same_chef:*{recipe_id}*",
                f"related_by_tags:*{recipe_id}*",
                f"category_popular:*{recipe_id}*",
            ]

            deleted_count = 0
            for pattern in patterns:
                keys = await cache.keys(pattern)
                if keys:
                    await cache.delete(*keys)
                    deleted_count += len(keys)

            logger.info(
                "Recipe cache invalidated",
                extra={
                    "recipe_id": recipe_id,
                    "deleted_count": deleted_count,
                },
            )
        except Exception as e:
            logger.warning(
                "Cache invalidation failed",
                extra={"error": str(e), "recipe_id": recipe_id},
            )

    async def invalidate_chef_recipes_cache(self, chef_id: str) -> None:
        """
        요리사 관련 캐시 무효화

        요리사 정보 변경 또는 레시피 추가/삭제 시 호출
        """
        try:
            cache = await get_redis_cache()

            pattern = f"same_chef:*"
            keys = await cache.keys(pattern)
            if keys:
                await cache.delete(*keys)

            logger.info(
                "Chef recipes cache invalidated",
                extra={"chef_id": chef_id, "deleted_count": len(keys) if keys else 0},
            )
        except Exception as e:
            logger.warning(
                "Chef cache invalidation failed",
                extra={"error": str(e), "chef_id": chef_id},
            )

    # =========================================================================
    # 커서 인코딩/디코딩 헬퍼
    # =========================================================================

    def _encode_cursor(self, data: dict) -> str:
        """범용 커서 인코딩 (dict → Base64)"""
        json_str = json.dumps(data, ensure_ascii=False)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    def _decode_cursor(self, cursor: str) -> dict:
        """범용 커서 디코딩 (Base64 → dict)"""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            raise CursorError(f"잘못된 커서 형식: {e}") from e

    def _encode_similarity_cursor(
        self,
        similarity_score: float,
        recipe_id: str,
    ) -> str:
        """유사도 커서 인코딩"""
        data = {"s": similarity_score, "i": recipe_id}
        json_str = json.dumps(data)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    def _decode_similarity_cursor(
        self,
        cursor: str,
    ) -> tuple[float, str]:
        """유사도 커서 디코딩"""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            return float(data["s"]), str(data["i"])
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise CursorError(f"잘못된 커서 형식: {e}") from e

    # =========================================================================
    # 유사 레시피 조회 (T014, T015, T016, T017)
    # =========================================================================

    async def get_similar_recipes(
        self,
        recipe_id: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> SimilarRecipeListResponse:
        """
        유사 레시피 목록 조회

        태그, 재료, 조리방식 기반 복합 유사도 계산
        - 태그 유사도: 40%
        - 재료 유사도: 40%
        - 조리 시간/난이도: 20%

        Args:
            recipe_id: 기준 레시피 ID
            cursor: 페이지네이션 커서
            limit: 조회 개수 (기본 10, 최대 50)

        Returns:
            SimilarRecipeListResponse: 유사 레시피 목록
        """
        start_time = time.perf_counter()
        limit = min(limit, 50)  # 최대 50개 제한

        # T015: Redis 캐시 확인
        cache_key = RecipeCacheKeys.similar_recipes_key(recipe_id, cursor, limit)
        try:
            cache = await get_redis_cache()
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(
                    "Similar recipes cache hit",
                    extra={"recipe_id": recipe_id, "cache_key": cache_key},
                )
                return SimilarRecipeListResponse.model_validate_json(cached)
        except Exception as e:
            logger.warning(
                "Cache read failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 기준 레시피 조회
        base_recipe = await self._get_base_recipe(recipe_id)

        # T017: 태그 없는 경우 처리
        base_tag_ids = {rt.tag_id for rt in base_recipe.recipe_tags}
        base_ingredient_names = {ing.name for ing in base_recipe.ingredients}

        # 후보 레시피 조회 (기준 레시피 제외, 활성 레시피만)
        # 태그가 하나라도 겹치는 레시피를 우선 조회
        if base_tag_ids:
            # 공통 태그가 있는 레시피 서브쿼리
            subquery = (
                select(RecipeTag.recipe_id)
                .where(RecipeTag.tag_id.in_(base_tag_ids))
                .distinct()
            )

            stmt = (
                select(Recipe)
                .options(
                    selectinload(Recipe.recipe_tags).selectinload(RecipeTag.tag),
                    selectinload(Recipe.ingredients),
                    joinedload(Recipe.chef),
                )
                .where(Recipe.id != recipe_id)
                .where(Recipe.is_active == True)  # noqa: E712
                .where(Recipe.id.in_(subquery))
                .limit(200)  # 유사도 계산을 위해 충분히 많이 조회
            )
        else:
            # T017: 태그 없는 경우 - 같은 난이도/조리시간 기반
            stmt = (
                select(Recipe)
                .options(
                    selectinload(Recipe.recipe_tags).selectinload(RecipeTag.tag),
                    selectinload(Recipe.ingredients),
                    joinedload(Recipe.chef),
                )
                .where(Recipe.id != recipe_id)
                .where(Recipe.is_active == True)  # noqa: E712
                .limit(100)
            )

        result = await self.db.execute(stmt)
        candidates = list(result.unique().scalars().all())

        # 유사도 계산 및 정렬
        scored_candidates: list[tuple[Recipe, float]] = []
        for candidate in candidates:
            similarity = self._calculate_combined_similarity(
                base_recipe,
                candidate,
                base_tag_ids,
                base_ingredient_names,
            )
            if similarity > 0:  # 유사도가 0보다 큰 것만 포함
                scored_candidates.append((candidate, similarity))

        # 유사도 내림차순 정렬
        scored_candidates.sort(key=lambda x: (-x[1], x[0].id))

        # 커서 적용
        if cursor:
            try:
                cursor_score, cursor_id = self._decode_similarity_cursor(cursor)
                # 커서 이후 항목 필터링
                filtered = []
                found_cursor = False
                for recipe, score in scored_candidates:
                    if not found_cursor:
                        if score < cursor_score or (score == cursor_score and recipe.id > cursor_id):
                            found_cursor = True
                        else:
                            continue
                    if found_cursor:
                        filtered.append((recipe, score))
                scored_candidates = filtered
            except CursorError:
                logger.warning("Invalid cursor, starting from beginning")

        # limit + 1로 자르기 (has_more 판단)
        has_more = len(scored_candidates) > limit
        scored_candidates = scored_candidates[:limit]

        # 응답 변환
        items: list[SimilarRecipeItem] = []
        for recipe, similarity in scored_candidates:
            # 태그 정보
            tags = [
                TagSummarySchema(
                    name=rt.tag.name,
                    slug=rt.tag.slug if rt.tag.slug else rt.tag.name.lower().replace(" ", "-"),
                )
                for rt in recipe.recipe_tags
            ]

            # 요리사 정보
            chef = None
            if recipe.chef:
                chef = ChefSummary(
                    id=recipe.chef.id,
                    name=recipe.chef.name,
                    profile_image_url=recipe.chef.profile_image_url,
                )

            item = SimilarRecipeItem(
                id=recipe.id,
                title=recipe.title,
                thumbnail_url=recipe.thumbnail_url,
                difficulty=recipe.difficulty,
                cook_time_minutes=recipe.cook_time_minutes,
                chef=chef,
                similarity_score=similarity,
                tags=tags,
            )
            items.append(item)

        # 다음 커서 생성
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = self._encode_similarity_cursor(
                last_item.similarity_score,
                last_item.id,
            )

        response = SimilarRecipeListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

        # T015: Redis 캐시 저장
        try:
            cache = await get_redis_cache()
            await cache.set(
                cache_key,
                response.model_dump_json(),
                ttl=RecipeCacheKeys.SIMILAR_RECIPES_TTL,
            )
        except Exception as e:
            logger.warning(
                "Cache set failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 로깅
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Similar recipes retrieved",
            extra={
                "recipe_id": recipe_id,
                "result_count": len(items),
                "has_more": has_more,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )

        return response

    # =========================================================================
    # 같은 요리사 레시피 조회 (T018~T024)
    # =========================================================================

    def _encode_view_count_cursor(
        self,
        view_count: int,
        recipe_id: str,
    ) -> str:
        """조회수 커서 인코딩"""
        data = {"v": view_count, "i": recipe_id}
        json_str = json.dumps(data)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    def _decode_view_count_cursor(
        self,
        cursor: str,
    ) -> tuple[int, str]:
        """조회수 커서 디코딩"""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            return int(data["v"]), str(data["i"])
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise CursorError(f"잘못된 커서 형식: {e}") from e

    async def get_same_chef_recipes(
        self,
        recipe_id: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> SameChefRecipeListResponse:
        """
        같은 요리사의 다른 레시피 목록 조회

        조회수 내림차순 정렬, 기준 레시피 제외

        Args:
            recipe_id: 기준 레시피 ID
            cursor: 페이지네이션 커서
            limit: 조회 개수 (기본 10, 최대 50)

        Returns:
            SameChefRecipeListResponse: 같은 요리사 레시피 목록
        """
        start_time = time.perf_counter()
        limit = min(limit, 50)

        # Redis 캐시 확인
        cache_key = RecipeCacheKeys.same_chef_recipes_key(recipe_id, cursor, limit)
        try:
            cache = await get_redis_cache()
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(
                    "Same chef recipes cache hit",
                    extra={"recipe_id": recipe_id, "cache_key": cache_key},
                )
                return SameChefRecipeListResponse.model_validate_json(cached)
        except Exception as e:
            logger.warning(
                "Cache read failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 기준 레시피 조회
        base_recipe = await self._get_base_recipe(recipe_id)

        # T024: 요리사 없는 경우 빈 결과 반환
        if not base_recipe.chef_id:
            return SameChefRecipeListResponse(
                items=[],
                next_cursor=None,
                has_more=False,
            )

        # 같은 요리사의 다른 레시피 조회 쿼리
        stmt = (
            select(Recipe)
            .options(
                selectinload(Recipe.recipe_tags).selectinload(RecipeTag.tag),
                joinedload(Recipe.chef),
            )
            .where(Recipe.chef_id == base_recipe.chef_id)
            .where(Recipe.id != recipe_id)
            .where(Recipe.is_active == True)  # noqa: E712
            .order_by(Recipe.view_count.desc(), Recipe.id)
        )

        # 커서 적용
        if cursor:
            try:
                cursor_view_count, cursor_id = self._decode_view_count_cursor(cursor)
                stmt = stmt.where(
                    or_(
                        Recipe.view_count < cursor_view_count,
                        (Recipe.view_count == cursor_view_count) & (Recipe.id > cursor_id),
                    )
                )
            except CursorError:
                logger.warning("Invalid cursor, starting from beginning")

        # limit + 1로 조회
        stmt = stmt.limit(limit + 1)

        result = await self.db.execute(stmt)
        recipes = list(result.unique().scalars().all())

        # has_more 판단
        has_more = len(recipes) > limit
        recipes = recipes[:limit]

        # 응답 변환
        items: list[SameChefRecipeItem] = []
        for recipe in recipes:
            tags = [
                TagSummarySchema(
                    name=rt.tag.name,
                    slug=rt.tag.slug if rt.tag.slug else rt.tag.name.lower().replace(" ", "-"),
                )
                for rt in recipe.recipe_tags
            ]

            chef = None
            if recipe.chef:
                chef = ChefSummary(
                    id=recipe.chef.id,
                    name=recipe.chef.name,
                    profile_image_url=recipe.chef.profile_image_url,
                )

            item = SameChefRecipeItem(
                id=recipe.id,
                title=recipe.title,
                thumbnail_url=recipe.thumbnail_url,
                difficulty=recipe.difficulty,
                cook_time_minutes=recipe.cook_time_minutes,
                chef=chef,
                view_count=recipe.view_count or 0,
                tags=tags,
            )
            items.append(item)

        # 다음 커서 생성
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = self._encode_view_count_cursor(
                last_item.view_count,
                last_item.id,
            )

        response = SameChefRecipeListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

        # Redis 캐시 저장
        try:
            cache = await get_redis_cache()
            await cache.set(
                cache_key,
                response.model_dump_json(),
                ttl=RecipeCacheKeys.SAME_CHEF_RECIPES_TTL,
            )
        except Exception as e:
            logger.warning(
                "Cache set failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 로깅
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Same chef recipes retrieved",
            extra={
                "recipe_id": recipe_id,
                "chef_id": base_recipe.chef_id,
                "result_count": len(items),
                "has_more": has_more,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )

        return response

    # =========================================================================
    # 관련 태그 레시피 조회 (T025~T031)
    # =========================================================================

    def _encode_tag_count_cursor(
        self,
        tag_count: int,
        recipe_id: str,
    ) -> str:
        """태그 개수 커서 인코딩"""
        data = {"t": tag_count, "i": recipe_id}
        json_str = json.dumps(data)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    def _decode_tag_count_cursor(
        self,
        cursor: str,
    ) -> tuple[int, str]:
        """태그 개수 커서 디코딩"""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            return int(data["t"]), str(data["i"])
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise CursorError(f"잘못된 커서 형식: {e}") from e

    async def get_related_by_tags(
        self,
        recipe_id: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> RelatedByTagsListResponse:
        """
        관련 태그 레시피 목록 조회

        공유 태그 개수가 많은 순으로 정렬

        Args:
            recipe_id: 기준 레시피 ID
            cursor: 페이지네이션 커서
            limit: 조회 개수 (기본 10, 최대 50)

        Returns:
            RelatedByTagsListResponse: 관련 태그 레시피 목록
        """
        start_time = time.perf_counter()
        limit = min(limit, 50)

        # Redis 캐시 확인
        cache_key = RecipeCacheKeys.related_by_tags_key(recipe_id, cursor, limit)
        try:
            cache = await get_redis_cache()
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(
                    "Related by tags cache hit",
                    extra={"recipe_id": recipe_id, "cache_key": cache_key},
                )
                return RelatedByTagsListResponse.model_validate_json(cached)
        except Exception as e:
            logger.warning(
                "Cache read failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 기준 레시피 조회
        base_recipe = await self._get_base_recipe(recipe_id)

        # T031: 태그 없는 경우 빈 결과 반환
        base_tag_ids = {rt.tag_id for rt in base_recipe.recipe_tags}
        base_tags_map = {rt.tag_id: rt.tag for rt in base_recipe.recipe_tags}

        if not base_tag_ids:
            return RelatedByTagsListResponse(
                items=[],
                next_cursor=None,
                has_more=False,
            )

        # 공유 태그가 있는 레시피 조회 (서브쿼리)
        subquery = (
            select(RecipeTag.recipe_id)
            .where(RecipeTag.tag_id.in_(base_tag_ids))
            .where(RecipeTag.recipe_id != recipe_id)
            .distinct()
        )

        stmt = (
            select(Recipe)
            .options(
                selectinload(Recipe.recipe_tags).selectinload(RecipeTag.tag),
                joinedload(Recipe.chef),
            )
            .where(Recipe.id.in_(subquery))
            .where(Recipe.is_active == True)  # noqa: E712
            .limit(200)  # 태그 개수 계산을 위해 충분히 조회
        )

        result = await self.db.execute(stmt)
        candidates = list(result.unique().scalars().all())

        # 공유 태그 개수 계산 및 정렬
        scored_candidates: list[tuple[Recipe, int, list[Tag]]] = []
        for candidate in candidates:
            candidate_tag_ids = {rt.tag_id for rt in candidate.recipe_tags}
            shared_tag_ids = base_tag_ids & candidate_tag_ids
            shared_count = len(shared_tag_ids)

            if shared_count > 0:
                # 공유 태그 객체 수집
                shared_tags = [base_tags_map[tid] for tid in shared_tag_ids if tid in base_tags_map]
                scored_candidates.append((candidate, shared_count, shared_tags))

        # 공유 태그 개수 내림차순, ID 오름차순 정렬
        scored_candidates.sort(key=lambda x: (-x[1], x[0].id))

        # 커서 적용
        if cursor:
            try:
                cursor_count, cursor_id = self._decode_tag_count_cursor(cursor)
                filtered = []
                found_cursor = False
                for recipe, count, shared_tags in scored_candidates:
                    if not found_cursor:
                        if count < cursor_count or (count == cursor_count and recipe.id > cursor_id):
                            found_cursor = True
                        else:
                            continue
                    if found_cursor:
                        filtered.append((recipe, count, shared_tags))
                scored_candidates = filtered
            except CursorError:
                logger.warning("Invalid cursor, starting from beginning")

        # has_more 판단
        has_more = len(scored_candidates) > limit
        scored_candidates = scored_candidates[:limit]

        # 응답 변환
        items: list[RelatedByTagsItem] = []
        for recipe, shared_count, shared_tags_list in scored_candidates:
            # 공유 태그 정보
            shared_tags = [
                TagSummarySchema(
                    name=tag.name,
                    slug=tag.slug if tag.slug else tag.name.lower().replace(" ", "-"),
                )
                for tag in shared_tags_list
            ]

            # 전체 태그 정보
            all_tags = [
                TagSummarySchema(
                    name=rt.tag.name,
                    slug=rt.tag.slug if rt.tag.slug else rt.tag.name.lower().replace(" ", "-"),
                )
                for rt in recipe.recipe_tags
            ]

            chef = None
            if recipe.chef:
                chef = ChefSummary(
                    id=recipe.chef.id,
                    name=recipe.chef.name,
                    profile_image_url=recipe.chef.profile_image_url,
                )

            item = RelatedByTagsItem(
                id=recipe.id,
                title=recipe.title,
                thumbnail_url=recipe.thumbnail_url,
                difficulty=recipe.difficulty,
                cook_time_minutes=recipe.cook_time_minutes,
                chef=chef,
                shared_tags_count=shared_count,
                shared_tags=shared_tags,
                tags=all_tags,
            )
            items.append(item)

        # 다음 커서 생성
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = self._encode_tag_count_cursor(
                last_item.shared_tags_count,
                last_item.id,
            )

        response = RelatedByTagsListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

        # Redis 캐시 저장
        try:
            cache = await get_redis_cache()
            await cache.set(
                cache_key,
                response.model_dump_json(),
                ttl=RecipeCacheKeys.RELATED_BY_TAGS_TTL,
            )
        except Exception as e:
            logger.warning(
                "Cache set failed",
                extra={"error": str(e), "cache_key": cache_key},
            )

        # 로깅
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Related by tags recipes retrieved",
            extra={
                "recipe_id": recipe_id,
                "base_tags_count": len(base_tag_ids),
                "result_count": len(items),
                "has_more": has_more,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )

        return response

    # =========================================================================
    # 카테고리 인기 레시피 조회
    # =========================================================================

    def _get_cook_time_range(self, cook_time: int | None) -> tuple[int, int]:
        """
        조리시간 기반 카테고리 범위 계산

        - 15분 이하: 0-15분 (간편 요리)
        - 30분 이하: 16-30분 (일반 요리)
        - 60분 이하: 31-60분 (정성 요리)
        - 60분 초과: 61분 이상 (정통 요리)
        """
        if cook_time is None:
            return (0, 9999)  # 모든 범위

        if cook_time <= 15:
            return (0, 15)
        elif cook_time <= 30:
            return (16, 30)
        elif cook_time <= 60:
            return (31, 60)
        else:
            return (61, 9999)

    def _get_category_name(
        self, difficulty: str | None, cook_time: int | None
    ) -> str:
        """카테고리 이름 생성"""
        # 난이도 이름
        difficulty_names = {
            "easy": "초급",
            "medium": "중급",
            "hard": "고급",
        }
        difficulty_name = difficulty_names.get(difficulty or "", "전체")

        # 조리시간 이름
        if cook_time is None:
            time_name = "전체"
        elif cook_time <= 15:
            time_name = "15분 이하"
        elif cook_time <= 30:
            time_name = "30분 이하"
        elif cook_time <= 60:
            time_name = "1시간 이하"
        else:
            time_name = "1시간 이상"

        return f"{difficulty_name} · {time_name}"

    async def get_category_popular(
        self,
        recipe_id: str,
        cursor: str | None = None,
        limit: int = 10,
    ) -> CategoryPopularListResponse:
        """
        카테고리 인기 레시피 목록 조회

        동일 카테고리(난이도+조리시간 범위) 내 조회수 순 정렬

        Args:
            recipe_id: 기준 레시피 ID
            cursor: 페이지네이션 커서
            limit: 조회 개수 (기본 10, 최대 50)

        Returns:
            CategoryPopularListResponse: 카테고리 인기 레시피 목록
        """
        # 파라미터 검증
        limit = min(max(limit, 1), 50)

        # 캐시 키 생성 (커서 포함)
        cache_key = f"category_popular:{recipe_id}:{cursor or 'first'}:{limit}"

        # 캐시 조회
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.info(
                "Category popular cache hit",
                extra={"recipe_id": recipe_id, "cache_key": cache_key},
            )
            return CategoryPopularListResponse(**cached)

        # 기준 레시피 조회
        base_recipe = await self._get_base_recipe(recipe_id)

        # 카테고리 정보 추출
        base_difficulty = base_recipe.difficulty
        base_cook_time = base_recipe.cook_time
        cook_time_min, cook_time_max = self._get_cook_time_range(base_cook_time)
        category_name = self._get_category_name(base_difficulty, base_cook_time)

        # 커서 디코딩 (view_count, id)
        cursor_view_count = None
        cursor_id = None
        if cursor:
            cursor_data = self._decode_cursor(cursor)
            cursor_view_count = cursor_data.get("view_count")
            cursor_id = cursor_data.get("id")

        # 쿼리 빌드: 같은 카테고리의 레시피
        query = (
            select(Recipe)
            .options(selectinload(Recipe.tags))
            .where(Recipe.id != recipe_id)  # 기준 레시피 제외
        )

        # 난이도 필터 (있는 경우)
        if base_difficulty:
            query = query.where(Recipe.difficulty == base_difficulty)

        # 조리시간 범위 필터 (있는 경우)
        if base_cook_time:
            query = query.where(
                Recipe.cook_time.between(cook_time_min, cook_time_max)
            )

        # 커서 기반 필터링 (view_count DESC, id ASC)
        if cursor_view_count is not None and cursor_id:
            query = query.where(
                or_(
                    Recipe.view_count < cursor_view_count,
                    and_(
                        Recipe.view_count == cursor_view_count,
                        Recipe.id > cursor_id,
                    ),
                )
            )

        # 정렬: 조회수 내림차순, ID 오름차순
        query = query.order_by(Recipe.view_count.desc(), Recipe.id.asc())

        # limit + 1로 조회하여 다음 페이지 존재 여부 확인
        query = query.limit(limit + 1)

        result = await self.db.execute(query)
        recipes = list(result.scalars().all())

        # 다음 페이지 존재 여부 확인
        has_more = len(recipes) > limit
        if has_more:
            recipes = recipes[:limit]

        # 응답 아이템 생성
        items = []
        for recipe in recipes:
            items.append(
                CategoryPopularItem(
                    id=recipe.id,
                    title=recipe.title,
                    thumbnail_url=recipe.thumbnail_url,
                    difficulty=recipe.difficulty,
                    cook_time_minutes=recipe.cook_time,
                    view_count=recipe.view_count or 0,
                    category=category_name,
                    tags=[
                        TagSummarySchema(id=tag.id, name=tag.name)
                        for tag in recipe.tags
                    ],
                )
            )

        # 다음 커서 생성
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = self._encode_cursor(
                {
                    "view_count": last_item.view_count,
                    "id": last_item.id,
                }
            )

        response = CategoryPopularListResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

        # 캐시 저장 (10분)
        await self._set_to_cache(
            cache_key,
            {
                "items": [item.model_dump() for item in items],
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        )

        logger.info(
            "Category popular retrieved",
            extra={
                "recipe_id": recipe_id,
                "category": category_name,
                "result_count": len(items),
                "has_more": has_more,
            },
        )

        return response
