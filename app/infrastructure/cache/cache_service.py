"""
PubMedIQ — Cache Service

Higher-level caching wrappers built on top of RedisClient.
Uses JSON serialization for complex objects.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import settings
from app.core.constants import (
    CACHE_PREFIX_ARTICLE,
    CACHE_PREFIX_SEARCH,
    CACHE_PREFIX_SESSION,
)
from app.core.logging import get_logger
from app.infrastructure.cache.redis_client import RedisClient

logger = get_logger(__name__)


class CacheService:
    """
    Domain-aware caching service for PubMedIQ.

    Cache hierarchy:
      search:<hash>   → full search response
      article:<pmid>  → individual article metadata
      session:<id>    → chat session state
    """

    def __init__(self, redis: RedisClient) -> None:
        self._redis = redis

    # ------------------------------------------------------------------
    # Search results cache
    # ------------------------------------------------------------------
    def _search_key(self, query: str, filters: dict | None) -> str:
        """Deterministic cache key for a search query + filters."""
        payload = json.dumps({"q": query.lower().strip(), "f": filters or {}}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"{CACHE_PREFIX_SEARCH}{digest}"

    async def cache_search_results(
        self,
        query: str,
        filters: dict | None,
        results: dict,
    ) -> None:
        """Cache a full search response."""
        key = self._search_key(query, filters)
        try:
            value = json.dumps(results, default=str)
            await self._redis.set(key, value, ex=settings.CACHE_TTL_SEARCH)
            logger.debug("search_cached", key=key)
        except Exception as e:
            logger.warning("cache_search_write_failed", error=str(e))

    async def get_cached_search(
        self,
        query: str,
        filters: dict | None,
    ) -> dict | None:
        """Retrieve a cached search response. Returns None on miss."""
        key = self._search_key(query, filters)
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            logger.debug("search_cache_hit", key=key)
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Article metadata cache
    # ------------------------------------------------------------------
    async def cache_article(self, pmid: str, article: dict) -> None:
        """Cache individual article metadata."""
        key = f"{CACHE_PREFIX_ARTICLE}{pmid}"
        try:
            await self._redis.set(key, json.dumps(article, default=str), ex=settings.CACHE_TTL_ARTICLE)
        except Exception as e:
            logger.warning("cache_article_write_failed", pmid=pmid, error=str(e))

    async def get_cached_article(self, pmid: str) -> dict | None:
        """Retrieve cached article metadata."""
        key = f"{CACHE_PREFIX_ARTICLE}{pmid}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Session state cache
    # ------------------------------------------------------------------
    async def cache_session(self, session_id: str, state: dict) -> None:
        """Cache a chat session state (for follow-up questions)."""
        key = f"{CACHE_PREFIX_SESSION}{session_id}"
        try:
            await self._redis.set(key, json.dumps(state, default=str), ex=settings.CACHE_TTL_SESSION)
        except Exception as e:
            logger.warning("cache_session_write_failed", session_id=session_id, error=str(e))

    async def get_cached_session(self, session_id: str) -> dict | None:
        """Retrieve a cached chat session state."""
        key = f"{CACHE_PREFIX_SESSION}{session_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------
    async def invalidate_search(self, query: str, filters: dict | None = None) -> None:
        """Remove a specific search from cache."""
        key = self._search_key(query, filters)
        await self._redis.delete(key)

    async def invalidate_article(self, pmid: str) -> None:
        """Remove a specific article from cache."""
        await self._redis.delete(f"{CACHE_PREFIX_ARTICLE}{pmid}")
