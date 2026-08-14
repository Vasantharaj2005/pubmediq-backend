"""
Tests for health endpoints

GET /api/v1/health       → basic liveness
GET /api/v1/health/live  → Kubernetes liveness probe
GET /api/v1/health/ready → readiness check with dependency status
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestHealthEndpoints:
    async def test_basic_health(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    async def test_liveness_probe(self, client):
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"

    async def test_readiness_all_healthy(self, client):
        with (
            patch("app.api.v1.endpoints.health.check_database_connection",
                  new_callable=AsyncMock, return_value=True),
            patch("app.api.v1.endpoints.health.redis_client") as mock_redis,
            patch("app.api.v1.endpoints.health.pinecone_client") as mock_pinecone,
        ):
            mock_redis.ping = AsyncMock(return_value=True)
            mock_pinecone.ping = AsyncMock(return_value=True)

            resp = await client.get("/api/v1/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["dependencies"]["database"] is True
            assert data["dependencies"]["redis"] is True
            assert data["dependencies"]["pinecone"] is True

    async def test_readiness_db_down(self, client):
        with (
            patch("app.api.v1.endpoints.health.check_database_connection",
                  new_callable=AsyncMock, return_value=False),
            patch("app.api.v1.endpoints.health.redis_client") as mock_redis,
            patch("app.api.v1.endpoints.health.pinecone_client") as mock_pinecone,
        ):
            mock_redis.ping = AsyncMock(return_value=True)
            mock_pinecone.ping = AsyncMock(return_value=True)

            resp = await client.get("/api/v1/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["dependencies"]["database"] is False

    async def test_readiness_redis_down_still_ok(self, client):
        """Redis being down should still return ok (only DB is required)."""
        with (
            patch("app.api.v1.endpoints.health.check_database_connection",
                  new_callable=AsyncMock, return_value=True),
            patch("app.api.v1.endpoints.health.redis_client") as mock_redis,
            patch("app.api.v1.endpoints.health.pinecone_client") as mock_pinecone,
        ):
            mock_redis.ping = AsyncMock(return_value=False)
            mock_pinecone.ping = AsyncMock(return_value=False)

            resp = await client.get("/api/v1/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            # DB is up → status should be "ok"
            assert data["status"] == "ok"
