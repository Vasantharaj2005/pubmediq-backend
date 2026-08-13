"""
Tests for app.agents.nodes.fusion

Verifies the Reciprocal Rank Fusion (RRF) algorithm:
  - Mathematical correctness of _rrf_score
  - Deduplication by PMID across sources
  - Source tracking (keyword, mesh, semantic)
  - Edge cases (empty inputs, single source)
"""
from __future__ import annotations

import pytest

from app.agents.nodes.fusion import _rrf_score, fusion_node
from app.core.constants import RRF_K


class TestRRFScore:
    def test_formula(self):
        """score = 1 / (k + rank)"""
        assert _rrf_score(1) == 1.0 / (RRF_K + 1)

    def test_rank_1_highest(self):
        """Rank 1 should produce the highest score."""
        s1 = _rrf_score(1)
        s2 = _rrf_score(2)
        s10 = _rrf_score(10)
        assert s1 > s2 > s10

    def test_all_positive(self):
        for rank in range(1, 101):
            assert _rrf_score(rank) > 0

    def test_custom_k(self):
        assert _rrf_score(1, k=0) == 1.0
        assert _rrf_score(1, k=100) == 1.0 / 101


@pytest.mark.asyncio
class TestFusionNode:
    async def test_empty_inputs(self):
        state = {"pubmed_results": [], "mesh_results": [], "semantic_results": []}
        result = await fusion_node(state)
        assert result["fused_results"] == []

    async def test_single_source(self):
        state = {
            "pubmed_results": [
                {"pmid": "1", "title": "Paper 1", "abstract": "Abstract 1"},
                {"pmid": "2", "title": "Paper 2", "abstract": "Abstract 2"},
            ],
            "mesh_results": [],
            "semantic_results": [],
        }
        result = await fusion_node(state)
        assert len(result["fused_results"]) == 2

    async def test_deduplication_by_pmid(self):
        """Same PMID from multiple sources should produce one fused result."""
        state = {
            "pubmed_results": [{"pmid": "100", "title": "From keyword"}],
            "mesh_results": [{"pmid": "100", "title": "From MeSH"}],
            "semantic_results": [{"pmid": "100", "title": "From semantic"}],
        }
        result = await fusion_node(state)
        assert len(result["fused_results"]) == 1

    async def test_multi_source_higher_score(self):
        """A paper found by all 3 sources should score higher than one from 1 source."""
        state = {
            "pubmed_results": [
                {"pmid": "1", "title": "Multi-source"},
                {"pmid": "2", "title": "Single-source"},
            ],
            "mesh_results": [{"pmid": "1", "title": "Multi-source"}],
            "semantic_results": [{"pmid": "1", "title": "Multi-source"}],
        }
        result = await fusion_node(state)
        fused = result["fused_results"]
        # Paper 1 (3 sources) should rank above Paper 2 (1 source)
        assert fused[0]["pmid"] == "1"
        assert fused[0]["rrf_score"] > fused[1]["rrf_score"]

    async def test_source_tracking(self):
        """Each fused result should track which sources contributed."""
        state = {
            "pubmed_results": [{"pmid": "1", "title": "P1"}],
            "mesh_results": [{"pmid": "1", "title": "P1"}, {"pmid": "2", "title": "P2"}],
            "semantic_results": [],
        }
        result = await fusion_node(state)
        fused_map = {p["pmid"]: p for p in result["fused_results"]}

        assert "keyword" in fused_map["1"]["retrieval_sources"]
        assert "mesh" in fused_map["1"]["retrieval_sources"]
        assert fused_map["1"]["source_count"] == 2

        assert "mesh" in fused_map["2"]["retrieval_sources"]
        assert fused_map["2"]["source_count"] == 1

    async def test_rrf_scores_are_floats(self):
        state = {
            "pubmed_results": [{"pmid": "1", "title": "T"}],
            "mesh_results": [],
            "semantic_results": [],
        }
        result = await fusion_node(state)
        for paper in result["fused_results"]:
            assert isinstance(paper["rrf_score"], float)
            assert paper["rrf_score"] > 0

    async def test_missing_pmid_skipped(self):
        """Papers without a PMID should be skipped."""
        state = {
            "pubmed_results": [{"title": "No PMID"}, {"pmid": "1", "title": "Has PMID"}],
            "mesh_results": [],
            "semantic_results": [],
        }
        result = await fusion_node(state)
        assert len(result["fused_results"]) == 1
        assert result["fused_results"][0]["pmid"] == "1"

    async def test_keeps_richer_paper_data(self):
        """When the same PMID appears in multiple sources, keep the one with the longer abstract."""
        state = {
            "pubmed_results": [{"pmid": "1", "title": "T", "abstract": "short"}],
            "mesh_results": [],
            "semantic_results": [{"pmid": "1", "title": "T", "abstract": "a much longer abstract text"}],
        }
        result = await fusion_node(state)
        assert len(result["fused_results"]) == 1
        assert "longer" in result["fused_results"][0]["abstract"]

    async def test_sorted_by_rrf_descending(self):
        state = {
            "pubmed_results": [
                {"pmid": "A", "title": "A"},
                {"pmid": "B", "title": "B"},
                {"pmid": "C", "title": "C"},
            ],
            "mesh_results": [{"pmid": "B", "title": "B"}],
            "semantic_results": [{"pmid": "B", "title": "B"}, {"pmid": "C", "title": "C"}],
        }
        result = await fusion_node(state)
        scores = [p["rrf_score"] for p in result["fused_results"]]
        assert scores == sorted(scores, reverse=True)
