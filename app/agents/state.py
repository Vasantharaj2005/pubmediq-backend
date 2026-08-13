"""
PubMedIQ — LangGraph Research State

This TypedDict travels through the entire LangGraph workflow.
Every node reads from and writes to this state.

Design principle:
  - Use total=False so nodes only update fields they're responsible for
  - All fields are Optional to avoid forcing every node to populate everything
"""
from __future__ import annotations

from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    """
    Complete state for the PubMedIQ research pipeline.

    Flow:
      query
        → intent (query_understanding node)
        → facets, mesh_terms (concept_mapping node)
        → keyword_query, mesh_query, semantic_query (query_planner node)
        → pubmed_results, mesh_results, semantic_results (retrieval nodes)
        → fused_results (fusion node)
        → reranked_results, quality_score (reranker node)
        → quality_gate routes to: answer_generator | query_refinement
        → final_answer, citations (answer_generator node)
    """

    # ---- Input ----
    query: str
    session_id: str
    top_k: int
    filters: dict[str, Any]  # year_from, year_to, study_type, journal

    # ---- Query Understanding ----
    intent: dict[str, Any]   # {population, intervention, condition, outcome, study_type}

    # ---- Concept Mapping ----
    facets: dict[str, list[str]]   # facet_name → [term, synonyms]
    mesh_terms: list[str]

    # ---- Query Planning ----
    keyword_query: str
    mesh_query: str
    semantic_query: str   # embedded; used for Pinecone

    # ---- Retrieval Results (raw, before fusion) ----
    pubmed_results: list[dict[str, Any]]    # from keyword esearch
    mesh_results: list[dict[str, Any]]      # from MeSH esearch
    semantic_results: list[dict[str, Any]]  # from Pinecone

    # ---- Fusion & Ranking ----
    fused_results: list[dict[str, Any]]
    reranked_results: list[dict[str, Any]]

    # ---- Quality Gate ----
    quality_score: float     # average rerank score of top-10
    quality_level: str       # "high" | "medium" | "low"

    # ---- Refinement ----
    refinement_count: int
    refined_query: str

    # ---- Final Output ----
    final_answer: str
    citations: list[str]     # list of PMID strings
    search_strategy: dict[str, Any]  # what was used

    # ---- Error tracking ----
    errors: list[str]
