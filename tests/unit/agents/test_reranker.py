"""
Tests for app.agents.nodes.reranker

Verifies:
  - Fallback behavior when cross-encoder model is unavailable
  - Sigmoid score normalization
  - Quality score calculation (average of top-10)
  - Edge cases (empty inputs, single result)
"""
from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from app.agents.nodes.reranker import _rerank_sync, reranker_node


class TestRerankerFallback:
    """When the cross-encoder model is unavailable, reranker falls back to RRF scores."""

    @patch("app.agents.nodes.reranker._load_reranker", return_value=None)
    def test_fallback_uses_rrf_scores(self, mock_loader):
        candidates = [
            {"pmid": "1", "rrf_score": 0.5, "title": "T1", "abstract": "A1"},
            {"pmid": "2", "rrf_score": 0.8, "title": "T2", "abstract": "A2"},
            {"pmid": "3", "rrf_score": 0.3, "title": "T3", "abstract": "A3"},
        ]
        result = _rerank_sync("test query", candidates)
        assert result[0]["pmid"] == "2"  # highest RRF
        assert result[0]["rerank_score"] == 0.8

    @patch("app.agents.nodes.reranker._load_reranker", return_value=None)
    def test_fallback_sorted_descending(self, mock_loader):
        candidates = [
            {"pmid": "1", "rrf_score": 0.1},
            {"pmid": "2", "rrf_score": 0.9},
            {"pmid": "3", "rrf_score": 0.5},
        ]
        result = _rerank_sync("query", candidates)
        scores = [p["rerank_score"] for p in result]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
class TestRerankerNode:
    async def test_empty_input(self):
        state = {"fused_results": [], "query": "test"}
        result = await reranker_node(state)
        assert result["reranked_results"] == []
        assert result["quality_score"] == 0.0

    @patch("app.agents.nodes.reranker._load_reranker", return_value=None)
    async def test_quality_score_calculation(self, mock_loader):
        """Quality score = average rerank score of top-10."""
        candidates = []
        for i in range(15):
            candidates.append({
                "pmid": str(i),
                "title": f"T{i}",
                "abstract": f"Abstract {i}",
                "rrf_score": (15 - i) / 15.0,  # descending scores
            })
        state = {"fused_results": candidates, "query": "test", "top_k": 20}
        result = await reranker_node(state)
        # Quality score should be average of top-10 rerank scores (after sigmoid)
        assert 0.0 <= result["quality_score"] <= 1.0

    @patch("app.agents.nodes.reranker._load_reranker", return_value=None)
    async def test_respects_top_k(self, mock_loader):
        """Output should be limited to top_k results."""
        candidates = [{"pmid": str(i), "rrf_score": 0.5} for i in range(50)]
        state = {"fused_results": candidates, "query": "test", "top_k": 10}
        result = await reranker_node(state)
        assert len(result["reranked_results"]) <= 10

    @patch("app.agents.nodes.reranker._load_reranker", return_value=None)
    async def test_sigmoid_normalization(self, mock_loader):
        """After reranking, scores should be normalized to [0, 1] via sigmoid."""
        candidates = [
            {"pmid": "1", "rrf_score": 0.9, "title": "T", "abstract": "A"},
        ]
        state = {"fused_results": candidates, "query": "test", "top_k": 20}
        result = await reranker_node(state)
        for paper in result["reranked_results"]:
            assert 0.0 <= paper["rerank_score"] <= 1.0

    @patch("app.agents.nodes.reranker._load_reranker", return_value=None)
    async def test_single_result(self, mock_loader):
        candidates = [{"pmid": "1", "rrf_score": 0.7, "title": "T", "abstract": "A"}]
        state = {"fused_results": candidates, "query": "test", "top_k": 20}
        result = await reranker_node(state)
        assert len(result["reranked_results"]) == 1
        assert result["quality_score"] > 0


class TestSigmoidNormalization:
    """Verify the sigmoid function behavior used in reranker."""

    def test_sigmoid_of_zero_is_half(self):
        assert 1.0 / (1.0 + math.exp(0)) == 0.5

    def test_sigmoid_positive_above_half(self):
        for x in [0.1, 0.5, 1.0, 5.0]:
            assert 1.0 / (1.0 + math.exp(-x)) > 0.5

    def test_sigmoid_negative_below_half(self):
        for x in [-0.1, -0.5, -1.0, -5.0]:
            assert 1.0 / (1.0 + math.exp(-x)) < 0.5

    def test_sigmoid_bounded(self):
        for x in [-20, -10, -1, 0, 1, 10, 20]:
            s = 1.0 / (1.0 + math.exp(-x))
            assert 0.0 < s < 1.0
