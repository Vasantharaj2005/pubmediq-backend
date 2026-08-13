"""
Tests for app.agents.state

Verifies the ResearchState TypedDict structure.
"""
from __future__ import annotations

from typing import get_type_hints

from app.agents.state import ResearchState


class TestResearchState:
    def test_is_typed_dict(self):
        """ResearchState should be a TypedDict."""
        assert hasattr(ResearchState, "__annotations__")

    def test_expected_fields_exist(self):
        hints = get_type_hints(ResearchState)
        expected_fields = [
            "query", "session_id", "top_k", "filters",
            "intent", "facets", "mesh_terms",
            "keyword_query", "mesh_query", "semantic_query",
            "pubmed_results", "mesh_results", "semantic_results",
            "fused_results", "reranked_results",
            "quality_score", "quality_level",
            "refinement_count", "refined_query",
            "final_answer", "citations", "search_strategy",
            "errors",
        ]
        for field in expected_fields:
            assert field in hints, f"Missing field: {field}"

    def test_total_false(self):
        """ResearchState uses total=False so nodes only update their own fields."""
        assert ResearchState.__total__ is False

    def test_can_construct_minimal_state(self):
        """Should be able to create with only a subset of fields."""
        state: ResearchState = {
            "query": "test query",
            "session_id": "sess-1",
            "errors": [],
        }
        assert state["query"] == "test query"

    def test_can_construct_full_state(self):
        """Full state dict should work."""
        state: ResearchState = {
            "query": "test",
            "session_id": "s",
            "top_k": 20,
            "filters": {},
            "intent": {"population": "elderly"},
            "facets": {"condition": ["depression", "major depressive disorder"]},
            "mesh_terms": ["Depression"],
            "keyword_query": "depression elderly",
            "mesh_query": "Depression[MeSH]",
            "semantic_query": "effect of exercise on depression",
            "pubmed_results": [],
            "mesh_results": [],
            "semantic_results": [],
            "fused_results": [],
            "reranked_results": [],
            "quality_score": 0.75,
            "quality_level": "medium",
            "refinement_count": 0,
            "refined_query": "",
            "final_answer": "Evidence suggests...",
            "citations": ["12345"],
            "search_strategy": {},
            "errors": [],
        }
        assert state["quality_score"] == 0.75
