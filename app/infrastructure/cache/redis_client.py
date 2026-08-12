"""
PubMedIQ — Redis Async Client

Provides a thin async Redis wrapper with connection pooling.
Gracefully degrades when Redis is unavailable.
"""
from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """
    Async Redis client backed by a connection pool.
    Falls back gracefully when Redis is unreachable.
    """

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None
        self._available = False

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            await self._client.ping()
            self._available = True
            logger.info("redis_connected", url=settings.REDIS_URL.split("@")[-1])
        except Exception as e:
            logger.warning("redis_unavailable", error=str(e), fallback="disabled")
            self._available = False

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.aclose()
            self._available = False

    async def get(self, key: str) -> str | None:
        if not self._available or not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning("redis_get_failed", key=key, error=str(e))
            return None

    async def set(
        self, key: str, value: str, ex: int | None = None
    ) -> bool:
        if not self._available or not self._client:
            return False
        try:
            await self._client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.warning("redis_set_failed", key=key, error=str(e))
            return False

    async def delete(self, *keys: str) -> int:
        if not self._available or not self._client:
            return 0
        try:
            return await self._client.delete(*keys)
        except Exception as e:
            logger.warning("redis_delete_failed", error=str(e))
            return 0

    async def exists(self, *keys: str) -> int:
        if not self._available or not self._client:
            return 0
        try:
            return await self._client.exists(*keys)
        except Exception as e:
            logger.warning("redis_exists_failed", error=str(e))
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        if not self._available or not self._client:
            return False
        try:
            return bool(await self._client.expire(key, seconds))
        except Exception as e:
            logger.warning("redis_expire_failed", key=key, error=str(e))
            return False

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        return await self.set(key, value, ex=seconds)

    async def ping(self) -> bool:
        if not self._client:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def raw(self) -> aioredis.Redis | None:
        """Direct access to underlying redis client (for token blacklist)."""
        return self._client


# Module-level singleton — initialised during app lifespan
redis_client = RedisClient()
