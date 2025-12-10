"""Redis client with connection pool"""

from typing import Any

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from user_service.core.config import settings

# Connection pool for Redis
_pool: ConnectionPool | None = None
_client: redis.Redis | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool"""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    global _client
    if _client is None:
        pool = await get_redis_pool()
        _client = redis.Redis(connection_pool=pool)
    return _client


async def close_redis() -> None:
    """Close Redis connection"""
    global _client, _pool
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


class RedisClient:
    """Redis client wrapper for session management"""

    def __init__(self, client: redis.Redis):
        self._client = client

    async def set(
        self, key: str, value: str, ex: int | None = None
    ) -> bool:
        """Set key with optional expiration in seconds"""
        return await self._client.set(key, value, ex=ex)

    async def get(self, key: str) -> str | None:
        """Get value by key"""
        return await self._client.get(key)

    async def delete(self, key: str) -> int:
        """Delete key"""
        return await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(await self._client.exists(key))

    async def incr(self, key: str) -> int:
        """Increment value"""
        return await self._client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration"""
        return await self._client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        return await self._client.ttl(key)

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern"""
        return await self._client.keys(pattern)

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration"""
        return await self._client.setex(key, seconds, value)

    async def hset(self, name: str, mapping: dict[str, Any]) -> int:
        """Set hash fields"""
        return await self._client.hset(name, mapping=mapping)

    async def hget(self, name: str, key: str) -> str | None:
        """Get hash field"""
        return await self._client.hget(name, key)

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all hash fields"""
        return await self._client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        return await self._client.hdel(name, *keys)
