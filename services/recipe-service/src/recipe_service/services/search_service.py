"""
검색 서비스

레시피 검색 비즈니스 로직을 담당합니다.
- 키워드 검색 (제목, 설명, 재료명, 요리사명)
- 필터링 (난이도, 조리시간, 태그, 요리사)
- 정렬 (relevance, latest, cook_time, popularity)
- 커서 기반 페이지네이션
- 검색 결과 캐싱
"""

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

from recipe_service.cache.redis_cache import RedisCache, get_redis_cache
from recipe_service.core.config import get_settings
from recipe_service.models import Chef, Recipe, RecipeIngredient, RecipeTag, Tag
from recipe_service.schemas.search import (
    ChefSummary,
    SearchQueryParams,
    SearchResult,
    SearchResultItem,
    TagSummary,
)
from recipe_service.utils.cursor import CursorError, decode_cursor, encode_cursor

logger = logging.getLogger(__name__)

# 설정에서 캐시 TTL 가져오기
settings = get_settings()


class SearchService:
    """검색 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: RedisCache | None = None

    async def _get_cache(self) -> RedisCache:
        """Redis 캐시 인스턴스 반환"""
        if self._cache is None:
            self._cache = await get_redis_cache()
        return self._cache

    # =========================================================================
    # 캐시 키 생성 (US5)
    # =========================================================================

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

    # =========================================================================
    # 키워드 검색 조건 구성 (US1)
    # =========================================================================

    def _build_keyword_conditions(self, keyword: str) -> list:
        """
        키워드 검색 조건 구성

        검색 대상: 제목, 설명, 재료명, 요리사명
        모든 조건은 OR로 결합
        """
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

    # =========================================================================
    # 필터링 조건 구성 (US2)
    # =========================================================================

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

    # =========================================================================
    # 정렬 적용 (US3)
    # =========================================================================

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

    # =========================================================================
    # 커서 조건 적용 (US4)
    # =========================================================================

    def _apply_cursor(self, stmt, cursor: str | None, sort: str):
        """커서 조건 적용 (페이지네이션)"""
        if not cursor:
            return stmt

        try:
            cursor_sort, cursor_value, cursor_id = decode_cursor(cursor)

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
                # ISO format 문자열을 datetime으로 변환
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
            return encode_cursor(sort, recipe.exposure_score, recipe.id)
        elif sort == "latest":
            return encode_cursor(sort, recipe.created_at, recipe.id)
        elif sort == "cook_time":
            return encode_cursor(sort, recipe.cook_time_minutes or 0, recipe.id)
        elif sort == "popularity":
            return encode_cursor(sort, recipe.view_count, recipe.id)
        else:
            return encode_cursor(sort, recipe.exposure_score, recipe.id)

    # =========================================================================
    # 검색 결과 변환
    # =========================================================================

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

    # =========================================================================
    # 메인 검색 메서드
    # =========================================================================

    async def search(self, params: SearchQueryParams) -> SearchResult:
        """
        레시피 검색

        Args:
            params: 검색 파라미터

        Returns:
            SearchResult: 검색 결과
        """
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

        # 캐시 확인 (US5)
        try:
            cache = await self._get_cache()
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
                extra={"error": str(e), "cache_key": cache_key if 'cache_key' in locals() else None},
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

        # 키워드 검색 조건 (US1)
        if params.q:
            keyword_conditions = self._build_keyword_conditions(params.q)
            stmt = stmt.where(or_(*keyword_conditions))

        # 필터링 조건 (US2)
        stmt = self._apply_filters(
            stmt, params.difficulty, params.max_cook_time, params.chef_id, params.tag
        )

        # 정렬 적용 (US3)
        stmt = self._apply_sort(stmt, params.sort)

        # 커서 조건 적용 (US4)
        stmt = self._apply_cursor(stmt, params.cursor, params.sort)

        # limit + 1 로 조회 (has_more 판단용)
        stmt = stmt.limit(params.limit + 1)

        # 쿼리 실행
        result = await self.session.execute(stmt)
        recipes = list(result.scalars().unique())

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

        # 캐시 저장 (US5)
        try:
            cache = await self._get_cache()
            await cache.set(cache_key, result.model_dump_json(), ex=settings.redis.SEARCH_CACHE_TTL)
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
