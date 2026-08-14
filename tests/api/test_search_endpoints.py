"""
Tests for search endpoints

POST /api/v1/search        → Run hybrid search pipeline
POST /api/v1/search/refine → Manually refine an existing search
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.search import SearchResponse


def _mock_search_response(**overrides) -> SearchResponse:
    defaults = {
        "session_id": "sess-test",
        "query": "test query",
        "results": [],
        "total_results": 0,
        "ai_summary": "No results found.",
    }
    defaults.update(overrides)
    return SearchResponse(**defaults)


@pytest.mark.asyncio
class TestSearchEndpoint:
    async def test_search_success(self, client):
        mock_response = _mock_search_response(total_results=5)

        with (
            patch("app.api.v1.endpoints.search.SearchService") as MockService,
            patch("app.api.v1.endpoints.search._get_cache"),
        ):
            instance = MockService.return_value
            instance.run = AsyncMock(return_value=mock_response)

            resp = await client.post("/api/v1/search", json={
                "query": "effect of exercise on depression in elderly",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-test"
        assert data["total_results"] == 5

    async def test_search_validation_query_too_short(self, client):
        resp = await client.post("/api/v1/search", json={
            "query": "ab",
        })
        assert resp.status_code == 422

    async def test_search_validation_top_k_out_of_range(self, client):
        resp = await client.post("/api/v1/search", json={
            "query": "valid query here",
            "top_k": 500,
        })
        assert resp.status_code == 422

    async def test_search_with_filters(self, client):
        mock_response = _mock_search_response()

        with (
            patch("app.api.v1.endpoints.search.SearchService") as MockService,
            patch("app.api.v1.endpoints.search._get_cache"),
        ):
            instance = MockService.return_value
            instance.run = AsyncMock(return_value=mock_response)

            resp = await client.post("/api/v1/search", json={
                "query": "CRISPR gene therapy",
                "filters": {
                    "year_from": 2020,
                    "year_to": 2024,
                    "study_type": "systematic_review",
                },
                "top_k": 10,
            })

        assert resp.status_code == 200

    async def test_search_empty_body(self, client):
        resp = await client.post("/api/v1/search", json={})
        assert resp.status_code == 422

    async def test_search_pipeline_error_returns_200(self, client):
        """Even if the pipeline fails, the endpoint should return a 200 with an error summary."""
        error_response = _mock_search_response(
            ai_summary="Search pipeline encountered an error: LLM exploded"
        )

        with (
            patch("app.api.v1.endpoints.search.SearchService") as MockService,
            patch("app.api.v1.endpoints.search._get_cache"),
        ):
            instance = MockService.return_value
            instance.run = AsyncMock(return_value=error_response)

            resp = await client.post("/api/v1/search", json={
                "query": "test query text",
            })

        assert resp.status_code == 200
        assert "error" in resp.json()["ai_summary"].lower()


@pytest.mark.asyncio
class TestRefineEndpoint:
    async def test_refine_session_not_found(self, app, client):
        from app.api.v1.endpoints.search import _get_cache
        mock_cache = AsyncMock()
        mock_cache.get_cached_session = AsyncMock(return_value=None)
        app.dependency_overrides[_get_cache] = lambda: mock_cache

        try:
            resp = await client.post("/api/v1/search/refine", json={
                "session_id": "nonexistent-session",
            })
        finally:
            app.dependency_overrides.pop(_get_cache, None)

        assert resp.status_code == 200
        data = resp.json()
        assert "not found" in data["ai_summary"].lower()

    async def test_refine_missing_session_id(self, client):
        resp = await client.post("/api/v1/search/refine", json={})
        assert resp.status_code == 422
