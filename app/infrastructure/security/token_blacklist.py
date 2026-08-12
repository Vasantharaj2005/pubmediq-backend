"""
PubMedIQ — Token Blacklist (Redis-backed)

When a user logs out, their token's JTI (JWT ID) is added to the blacklist.
Subsequent requests using that token are rejected.

Redis is the primary backend (fast O(1) lookup via SET with TTL).
Falls back to an in-memory set if Redis is unavailable (dev/test convenience).
"""
from __future__ import annotations

from app.core.constants import CACHE_PREFIX_BLACKLIST
from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenBlacklist:
    """
    Redis-backed token blacklist for logout / token revocation.

    Usage:
        blacklist = TokenBlacklist(redis_client)
        await blacklist.add(jti, ttl_seconds=1800)
        is_revoked = await blacklist.is_blacklisted(jti)  # True
    """

    def __init__(self, redis_client=None) -> None:
        """
        Args:
            redis_client: An async Redis client instance.
                          If None, falls back to in-memory set (dev only).
        """
        self._redis = redis_client
        self._memory_set: set[str] = set()  # fallback for tests / no Redis

    @property
    def _using_redis(self) -> bool:
        return self._redis is not None

    def _key(self, jti: str) -> str:
        return f"{CACHE_PREFIX_BLACKLIST}{jti}"

    async def add(self, jti: str, ttl_seconds: int = 1800) -> None:
        """
        Add a JTI to the blacklist with a TTL matching the token expiry.

        Args:
            jti: The JWT ID claim to blacklist.
            ttl_seconds: How long to keep the blacklist entry (should match token TTL).
        """
        if self._using_redis:
            try:
                await self._redis.set(self._key(jti), "1", ex=ttl_seconds)
                logger.info("token_blacklisted", jti=jti[:8] + "...")
                return
            except Exception as e:
                logger.warning("blacklist_redis_error", error=str(e), fallback="memory")

        # Fallback: in-memory
        self._memory_set.add(jti)
        logger.debug("token_blacklisted_memory", jti=jti[:8] + "...")

    async def is_blacklisted(self, jti: str) -> bool:
        """
        Check if a JTI is in the blacklist.

        Args:
            jti: The JWT ID to check.

        Returns:
            True if the token has been revoked.
        """
        if self._using_redis:
            try:
                result = await self._redis.exists(self._key(jti))
                return bool(result)
            except Exception as e:
                logger.warning("blacklist_check_redis_error", error=str(e), fallback="memory")

        # Fallback: in-memory
        return jti in self._memory_set

    async def remove(self, jti: str) -> None:
        """
        Remove a JTI from the blacklist (e.g. for testing).

        Args:
            jti: The JWT ID to remove.
        """
        if self._using_redis:
            try:
                await self._redis.delete(self._key(jti))
                return
            except Exception:
                pass
        self._memory_set.discard(jti)


# ---------------------------------------------------------------------------
# Module-level singleton — configured with Redis in main.py lifespan
# ---------------------------------------------------------------------------
token_blacklist = TokenBlacklist(redis_client=None)  # Redis injected at startup


def configure_blacklist(redis_client) -> None:
    """Called from app lifespan to inject the Redis client."""
    global token_blacklist
    token_blacklist = TokenBlacklist(redis_client=redis_client)
