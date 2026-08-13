"""
Tests for app.application.services.search_service

Verifies SearchService orchestration with mocked:
  - LangGraph compiled graph
  - CacheService
  - HistoryRepository
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.search_service import SearchService
from app.schemas.search import SearchRequest, SearchResponse


def _make_final_state(**overrides):
    """Create a complete LangGraph final state dict."""
    state = {
        "query": "test query",
        "session_id": "sess-1",
        "intent": {"population": "elderly", "intervention": "exercise"},
        "reranked_results": [
            {
                "pmid": "123",
                "title": "Test Paper",
                "abstract": "Test abstract",
                "authors": ["Smith J"],
                "journal": "Nature",
                "year": 2024,
                "rerank_score": 0.85,
                "rrf_score": 0.5,
                "retrieval_sources": ["keyword", "semantic"],
                "pub_types": [],
                "mesh_terms": [],
            }
        ],
        "quality_score": 0.80,
        "quality_level": "high",
        "refinement_count": 0,
        "search_strategy": {"keyword_query": "test", "mesh_terms": []},
        "final_answer": "Evidence suggests...",
        "citations": ["123"],
    }
    state.update(overrides)
    return state


@pytest.fixture
def mock_graph():
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value=_make_final_state())
    return graph


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get_cached_search = AsyncMock(return_value=None)
    cache.cache_search_results = AsyncMock()
    return cache


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestSearchServiceRun:
    @pytest.mark.asyncio
    async def test_successful_search(self, mock_db, mock_cache, mock_graph):
        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db, cache=mock_cache)
            request = SearchRequest(query="effect of exercise on depression")
            result = await service.run(request, user_id=str(uuid.uuid4()))

        assert isinstance(result, SearchResponse)
        assert len(result.results) >= 1
        assert result.results[0].pmid == "123"
        mock_graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self, mock_db, mock_cache, mock_graph):
        cached_data = SearchResponse(
            session_id="cached-sess",
            query="cached query",
            results=[],
            total_results=0,
        ).model_dump()
        mock_cache.get_cached_search = AsyncMock(return_value=cached_data)

        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db, cache=mock_cache)
            request = SearchRequest(query="cached query")
            result = await service.run(request)

        assert result.cached is True
        mock_graph.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_failure_returns_error_response(self, mock_db, mock_cache, mock_graph):
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("LLM exploded"))

        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db, cache=mock_cache)
            request = SearchRequest(query="test query")
            result = await service.run(request)

        assert isinstance(result, SearchResponse)
        assert result.total_results == 0
        assert "error" in result.ai_summary.lower()

    @pytest.mark.asyncio
    async def test_history_save_failure_does_not_crash(self, mock_db, mock_cache, mock_graph):
        """History save failure should log warning but not crash the search."""
        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db, cache=mock_cache)
            # Make history repo fail
            with patch.object(service, "_history_repo") as mock_repo:
                mock_repo.create = AsyncMock(side_effect=Exception("DB down"))

                request = SearchRequest(query="test query")
                result = await service.run(request, user_id=str(uuid.uuid4()))

        # Should still return results despite history failure
        assert isinstance(result, SearchResponse)

    @pytest.mark.asyncio
    async def test_no_cache_service(self, mock_db, mock_graph):
        """SearchService should work without a cache service."""
        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db, cache=None)
            request = SearchRequest(query="test query")
            result = await service.run(request)

        assert isinstance(result, SearchResponse)

    @pytest.mark.asyncio
    async def test_anonymous_search_no_history(self, mock_db, mock_cache, mock_graph):
        """Anonymous user (no user_id) should not save to history."""
        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db, cache=mock_cache)
            with patch.object(service, "_history_repo") as mock_repo:
                mock_repo.create = AsyncMock()
                request = SearchRequest(query="test query")
                await service.run(request, user_id=None)

            mock_repo.create.assert_not_called()


class TestFormatResponse:
    @pytest.mark.asyncio
    async def test_formats_paper_results(self, mock_db, mock_graph):
        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db)
            request = SearchRequest(query="test")
            result = await service.run(request)

        assert len(result.results) == 1
        paper = result.results[0]
        assert paper.pmid == "123"
        assert paper.title == "Test Paper"

    @pytest.mark.asyncio
    async def test_formats_quality(self, mock_db, mock_graph):
        with patch("app.application.services.search_service.get_compiled_graph", return_value=mock_graph):
            service = SearchService(db=mock_db)
            request = SearchRequest(query="test")
            result = await service.run(request)

        assert result.quality is not None
        assert result.quality.score == 0.80
        assert result.quality.level == "high"

    @pytest.mark.asyncio
    async def test_empty_reranked_results(self, mock_db):
        empty_graph = AsyncMock()
        empty_graph.ainvoke = AsyncMock(return_value=_make_final_state(
            reranked_results=[], quality_score=0.0, quality_level="low"
        ))

        with patch("app.application.services.search_service.get_compiled_graph", return_value=empty_graph):
            service = SearchService(db=mock_db)
            request = SearchRequest(query="obscure query")
            result = await service.run(request)

        assert result.total_results == 0
        assert result.results == []
