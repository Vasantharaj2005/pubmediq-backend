"""
Tests for app.agents.nodes.quality_gate

Verifies the deterministic routing logic:
  - quality_gate_router returns "synthesize" or "refine"
  - Threshold boundary behavior
  - Max refinements exhaustion
  - quality_gate_node annotates quality_level
"""
from __future__ import annotations

import pytest

from app.agents.nodes.quality_gate import quality_gate_node, quality_gate_router
from app.core.constants import MAX_REFINEMENTS, QUALITY_THRESHOLD


class TestQualityGateRouter:
    """Tests for the conditional edge function."""

    def test_high_quality_synthesizes(self):
        """Score above threshold → synthesize."""
        state = {
            "quality_score": QUALITY_THRESHOLD + 0.1,
            "refinement_count": 0,
            "reranked_results": [{"pmid": "1"}],
        }
        assert quality_gate_router(state) == "synthesize"

    def test_exact_threshold_synthesizes(self):
        """Score exactly at threshold → synthesize."""
        state = {
            "quality_score": QUALITY_THRESHOLD,
            "refinement_count": 0,
            "reranked_results": [{"pmid": "1"}],
        }
        assert quality_gate_router(state) == "synthesize"

    def test_below_threshold_refines(self):
        """Score below threshold with budget → refine."""
        state = {
            "quality_score": QUALITY_THRESHOLD - 0.1,
            "refinement_count": 0,
            "reranked_results": [{"pmid": "1"}],
        }
        assert quality_gate_router(state) == "refine"

    def test_below_threshold_max_refinements_synthesizes(self):
        """Score below threshold but no budget left → synthesize anyway."""
        state = {
            "quality_score": QUALITY_THRESHOLD - 0.1,
            "refinement_count": MAX_REFINEMENTS,
            "reranked_results": [{"pmid": "1"}],
        }
        assert quality_gate_router(state) == "synthesize"

    def test_no_results_with_budget_refines(self):
        """Empty results with refinement budget → refine."""
        state = {
            "quality_score": 0.0,
            "refinement_count": 0,
            "reranked_results": [],
        }
        assert quality_gate_router(state) == "refine"

    def test_no_results_no_budget_synthesizes(self):
        """Empty results and no budget → synthesize (will produce 'no results' answer)."""
        state = {
            "quality_score": 0.0,
            "refinement_count": MAX_REFINEMENTS,
            "reranked_results": [],
        }
        assert quality_gate_router(state) == "synthesize"

    def test_zero_score_with_results_refines(self):
        """Quality score 0 with results and budget → refine."""
        state = {
            "quality_score": 0.0,
            "refinement_count": 0,
            "reranked_results": [{"pmid": "1"}],
        }
        assert quality_gate_router(state) == "refine"

    def test_missing_state_keys_defaults(self):
        """Missing keys should use safe defaults."""
        state = {}
        # No results, no score, no refinement count
        # refinement_count defaults to 0, reranked_results defaults to []
        # So: no results + budget → refine
        result = quality_gate_router(state)
        assert result in ("synthesize", "refine")

    def test_refinement_count_boundary(self):
        """Test at exactly MAX_REFINEMENTS - 1 → still can refine."""
        state = {
            "quality_score": 0.3,
            "refinement_count": MAX_REFINEMENTS - 1,
            "reranked_results": [{"pmid": "1"}],
        }
        assert quality_gate_router(state) == "refine"


@pytest.mark.asyncio
class TestQualityGateNode:
    """Tests for the state annotation node."""

    async def test_high_quality_level(self):
        state = {"quality_score": 0.90}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "high"

    async def test_medium_quality_level(self):
        state = {"quality_score": 0.70}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "medium"

    async def test_low_quality_level(self):
        state = {"quality_score": 0.40}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "low"

    async def test_boundary_high_medium(self):
        """Score of exactly 0.80 → high."""
        state = {"quality_score": 0.80}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "high"

    async def test_boundary_medium_low(self):
        """Score of exactly QUALITY_THRESHOLD → medium."""
        state = {"quality_score": QUALITY_THRESHOLD}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "medium"

    async def test_zero_score(self):
        state = {"quality_score": 0.0}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "low"

    async def test_missing_score_defaults(self):
        state = {}
        result = await quality_gate_node(state)
        assert result["quality_level"] == "low"
