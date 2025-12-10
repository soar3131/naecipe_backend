"""
Redis 클라이언트 관리

연결 풀 기반 Redis 클라이언트를 제공합니다.
"""

from typing import Any

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

# 전역 연결 풀 및 클라이언트
_pool: ConnectionPool | None = None
_client: redis.Redis | None = None


async def get_redis_pool() -> ConnectionPool:
    """Redis 연결 풀 생성 또는 반환"""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> redis.Redis:
    """원시 Redis 클라이언트 반환"""
    global _client
    if _client is None:
        pool = await get_redis_pool()
        _client = redis.Redis(connection_pool=pool)
    return _client


async def close_redis() -> None:
    """Redis 연결 종료"""
    global _client, _pool
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


class RedisClient:
    """세션/캐시 관리를 위한 Redis 클라이언트 래퍼"""

    def __init__(self, client: redis.Redis):
        self._client = client

    # ==========================================================================
    # 기본 문자열 연산
    # ==========================================================================

    async def ping(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def set(
        self,
        key: str,
        value: str | dict | list,
        ex: int | None = None,
        ttl: int | None = None,
    ) -> bool:
        """키 설정 (선택적 만료 시간, 초 단위)

        Args:
            key: 키 이름
            value: 값 (문자열, dict, list 가능)
            ex: 만료 시간 (초 단위)
            ttl: 만료 시간 (초 단위, ex의 별칭)
        """
        import json

        expire = ex or ttl
        # dict나 list인 경우 JSON 직렬화
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        return await self._client.set(key, value, ex=expire)

    async def get(self, key: str, parse_json: bool = True) -> str | dict | list | None:
        """키로 값 조회

        Args:
            key: 키 이름
            parse_json: True일 경우 JSON 문자열을 자동으로 파싱
        """
        import json

        value = await self._client.get(key)
        if value is None:
            return None

        if parse_json:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return value

    async def delete(self, key: str) -> int:
        """키 삭제"""
        return await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return bool(await self._client.exists(key))

    async def incr(self, key: str) -> int:
        """값 증가"""
        return await self._client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """키 만료 시간 설정"""
        return await self._client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """키의 남은 수명 조회"""
        return await self._client.ttl(key)

    async def keys(self, pattern: str) -> list[str]:
        """패턴과 일치하는 키 목록 조회"""
        return await self._client.keys(pattern)

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """만료 시간과 함께 키 설정"""
        return await self._client.setex(key, seconds, value)

    # ==========================================================================
    # 해시 연산
    # ==========================================================================

    async def hset(self, name: str, mapping: dict[str, Any]) -> int:
        """해시 필드 설정"""
        return await self._client.hset(name, mapping=mapping)

    async def hget(self, name: str, key: str) -> str | None:
        """해시 필드 조회"""
        return await self._client.hget(name, key)

    async def hgetall(self, name: str) -> dict[str, str]:
        """해시의 모든 필드 조회"""
        return await self._client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """해시 필드 삭제"""
        return await self._client.hdel(name, *keys)

    # ==========================================================================
    # JSON 연산 (편의 메서드)
    # ==========================================================================

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ex: int | None = None,
    ) -> bool:
        """JSON 객체 저장"""
        import json

        return await self.set(key, json.dumps(value, ensure_ascii=False), ex=ex)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """JSON 객체 조회"""
        import json

        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None


async def get_redis_client() -> RedisClient:
    """RedisClient 인스턴스 반환"""
    client = await get_redis()
    return RedisClient(client)


# 캐시용 별칭
async def get_redis_cache() -> RedisClient:
    """캐시용 RedisClient 인스턴스 반환 (get_redis_client의 별칭)"""
    return await get_redis_client()
