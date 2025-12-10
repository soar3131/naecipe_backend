"""
Redis 캐시 유틸리티

Cache-Aside 패턴을 구현합니다.
TTL 기반 자동 만료와 JSON 직렬화/역직렬화를 지원합니다.
"""

import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import redis.asyncio as redis
from pydantic import BaseModel

from recipe_service.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisCache:
    """Redis 캐시 클라이언트"""

    # 기본 TTL 설정 (초)
    DEFAULT_TTL = 3600  # 1시간
    RECIPE_TTL = 3600  # 1시간
    RECIPE_LIST_TTL = 300  # 5분
    POPULAR_TTL = 600  # 10분
    CHEF_TTL = 3600  # 1시간

    def __init__(self):
        self._client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis:
        """Redis 클라이언트 반환 (lazy initialization)"""
        if self._client is None:
            self._client = redis.from_url(
                settings.redis.url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        """Redis 연결 종료"""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Any | None:
        """캐시에서 값 조회"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Redis GET 실패: {key}, 오류: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """캐시에 값 저장"""
        try:
            client = await self.get_client()
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            await client.set(key, serialized, ex=ttl or self.DEFAULT_TTL)
            return True
        except Exception as e:
            logger.warning(f"Redis SET 실패: {key}, 오류: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """캐시에서 키 삭제"""
        try:
            client = await self.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE 실패: {key}, 오류: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """패턴에 매칭되는 모든 키 삭제"""
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Redis DELETE PATTERN 실패: {pattern}, 오류: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis EXISTS 실패: {key}, 오류: {e}")
            return False

    # 캐시 키 생성 헬퍼
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
    def chef_recipes_key(chef_id: str, cursor: str | None = None, limit: int = 20) -> str:
        """요리사별 레시피 캐시 키"""
        cursor_part = cursor or "first"
        return f"chef:{chef_id}:recipes:{cursor_part}:{limit}"


# 전역 캐시 인스턴스
_redis_cache: RedisCache | None = None


async def get_redis_cache() -> RedisCache:
    """Redis 캐시 싱글톤 인스턴스 반환"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def cache_aside(
    key_func: Callable[..., str],
    ttl: int | None = None,
    model_class: type[BaseModel] | None = None,
):
    """
    Cache-Aside 데코레이터

    Args:
        key_func: 캐시 키 생성 함수
        ttl: TTL (초)
        model_class: Pydantic 모델 클래스 (역직렬화용)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = await get_redis_cache()
            cache_key = key_func(*args, **kwargs)

            # 캐시 조회
            cached = await cache.get(cache_key)
            if cached is not None:
                if model_class:
                    if isinstance(cached, list):
                        return [model_class.model_validate(item) for item in cached]
                    return model_class.model_validate(cached)
                return cached

            # 캐시 미스: 원본 함수 호출
            result = await func(*args, **kwargs)

            # 결과 캐싱
            if result is not None:
                if isinstance(result, BaseModel):
                    await cache.set(cache_key, result.model_dump(mode="json"), ttl)
                elif isinstance(result, list) and result and isinstance(result[0], BaseModel):
                    await cache.set(
                        cache_key,
                        [item.model_dump(mode="json") for item in result],
                        ttl,
                    )
                else:
                    await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator
