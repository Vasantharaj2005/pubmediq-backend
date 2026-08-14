"""
Tests for app.infrastructure.security.token_blacklist

Verifies the TokenBlacklist with in-memory fallback
(no Redis required — tests the fallback path used in dev/test).
"""
from __future__ import annotations

import pytest

from app.infrastructure.security.token_blacklist import TokenBlacklist


@pytest.fixture
def blacklist():
    """TokenBlacklist with no Redis → uses in-memory set."""
    return TokenBlacklist(redis_client=None)


@pytest.mark.asyncio
class TestTokenBlacklistInMemory:
    async def test_add_and_check(self, blacklist):
        await blacklist.add("jti-123", ttl_seconds=300)
        assert await blacklist.is_blacklisted("jti-123") is True

    async def test_not_blacklisted(self, blacklist):
        assert await blacklist.is_blacklisted("jti-unknown") is False

    async def test_remove(self, blacklist):
        await blacklist.add("jti-to-remove", ttl_seconds=300)
        assert await blacklist.is_blacklisted("jti-to-remove") is True

        await blacklist.remove("jti-to-remove")
        assert await blacklist.is_blacklisted("jti-to-remove") is False

    async def test_multiple_tokens(self, blacklist):
        await blacklist.add("jti-1", ttl_seconds=300)
        await blacklist.add("jti-2", ttl_seconds=300)
        await blacklist.add("jti-3", ttl_seconds=300)

        assert await blacklist.is_blacklisted("jti-1") is True
        assert await blacklist.is_blacklisted("jti-2") is True
        assert await blacklist.is_blacklisted("jti-3") is True
        assert await blacklist.is_blacklisted("jti-4") is False

    async def test_remove_nonexistent_does_not_raise(self, blacklist):
        """Removing a JTI that was never added should not raise."""
        await blacklist.remove("never-added")

    async def test_using_redis_false(self, blacklist):
        assert blacklist._using_redis is False

    async def test_key_format(self, blacklist):
        key = blacklist._key("test-jti")
        assert key.startswith("blacklist:")
        assert "test-jti" in key
