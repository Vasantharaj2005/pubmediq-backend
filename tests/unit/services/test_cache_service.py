"""
Tests for app.infrastructure.cache.cache_service

Verifies:
  - Deterministic cache key generation
  - Search cache hit / miss logic
  - Article and session caching
  - Cache invalidation
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.cache.cache_service import CacheService


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def cache(mock_redis):
    return CacheService(redis=mock_redis)


class TestSearchKeyGeneration:
    def test_deterministic_key(self, cache):
        """Same query + filters should produce the same cache key."""
        key1 = cache._search_key("test query", {"year_from": 2020})
        key2 = cache._search_key("test query", {"year_from": 2020})
        assert key1 == key2

    def test_different_queries_different_keys(self, cache):
        key1 = cache._search_key("query A", None)
        key2 = cache._search_key("query B", None)
        assert key1 != key2

    def test_case_insensitive(self, cache):
        key1 = cache._search_key("Test Query", None)
        key2 = cache._search_key("test query", None)
        assert key1 == key2

    def test_whitespace_trimmed(self, cache):
        key1 = cache._search_key("  test query  ", None)
        key2 = cache._search_key("test query", None)
        assert key1 == key2

    def test_key_starts_with_prefix(self, cache):
        key = cache._search_key("test", None)
        assert key.startswith("search:")

    def test_filters_affect_key(self, cache):
        key1 = cache._search_key("query", {"year_from": 2020})
        key2 = cache._search_key("query", {"year_from": 2021})
        assert key1 != key2

    def test_none_filters_same_as_empty(self, cache):
        key1 = cache._search_key("query", None)
        key2 = cache._search_key("query", {})
        assert key1 == key2


class TestSearchCaching:
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        result = await cache.get_cached_search("query", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache, mock_redis):
        cached = {"session_id": "s1", "query": "q", "results": []}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached))
        result = await cache.get_cached_search("q", None)
        assert result is not None
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_cache_write(self, cache, mock_redis):
        await cache.cache_search_results("query", None, {"results": []})
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_corrupted_cache_returns_none(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value="not valid json{{{")
        result = await cache.get_cached_search("query", None)
        assert result is None


class TestArticleCaching:
    @pytest.mark.asyncio
    async def test_cache_article(self, cache, mock_redis):
        await cache.cache_article("12345", {"title": "Test"})
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_article_miss(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        assert await cache.get_cached_article("12345") is None

    @pytest.mark.asyncio
    async def test_get_cached_article_hit(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value='{"title": "Test"}')
        result = await cache.get_cached_article("12345")
        assert result["title"] == "Test"


class TestSessionCaching:
    @pytest.mark.asyncio
    async def test_cache_session(self, cache, mock_redis):
        await cache.cache_session("sess-1", {"query": "test"})
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_session_miss(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        assert await cache.get_cached_session("sess-1") is None

    @pytest.mark.asyncio
    async def test_get_cached_session_hit(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value='{"query": "test"}')
        result = await cache.get_cached_session("sess-1")
        assert result["query"] == "test"


class TestCacheInvalidation:
    @pytest.mark.asyncio
    async def test_invalidate_search(self, cache, mock_redis):
        await cache.invalidate_search("query", None)
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_article(self, cache, mock_redis):
        await cache.invalidate_article("12345")
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_write_failure_does_not_raise(self, cache, mock_redis):
        """Cache write failures should be swallowed (logged, not raised)."""
        mock_redis.set = AsyncMock(side_effect=Exception("Redis down"))
        # Should not raise
        await cache.cache_search_results("query", None, {"results": []})
