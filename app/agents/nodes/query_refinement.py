"""
PubMedIQ — Agent Node: Query Refinement (LLM)

Generates a refined PubMed query when the quality gate rejects results.
Uses the LLM to diagnose why the initial query underperformed and
suggest a more targeted formulation.

Max refinements = 2 (enforced by quality gate).
"""
from __future__ import annotations

import json

from app.agents.prompts.refinement import build_refinement_prompt
from app.agents.state import ResearchState
from app.core.constants import MAX_REFINEMENTS, QUALITY_THRESHOLD
from app.core.logging import get_logger
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.model_router import ModelTask

logger = get_logger(__name__)


async def query_refinement_node(state: ResearchState) -> dict:
    """
    LangGraph node: Refine the search query using LLM.

    Input state:  query, intent, keyword_query, quality_score, refinement_count
    Output state: refined_query, keyword_query (updated), refinement_count (incremented)
    """
    query = state.get("query", "")
    intent = state.get("intent", {})
    current_query = state.get("keyword_query", query)
    quality_score = state.get("quality_score", 0.0)
    refinement_count = state.get("refinement_count", 0)

    print(f"\n  ┌──────────────────────────────────────")
    print(f"  │ [Node 8/9] 🔄 QUERY REFINEMENT (Attempt {refinement_count+1}/{MAX_REFINEMENTS})")
    print(f"  │ Current query: {current_query[:100]}")
    print(f"  ├──────────────────────────────────────")
    print(f"  │ Asking LLM for better query formulation...")
    logger.info(
        "node_query_refinement",
        attempt=refinement_count + 1,
        quality_score=quality_score,
    )

    system, human = build_refinement_prompt(
        original_query=query,
        intent=intent,
        current_query=current_query,
        quality_score=quality_score,
        refinement_count=refinement_count + 1,
        threshold=QUALITY_THRESHOLD,
        max_refinements=MAX_REFINEMENTS,
    )

    client = LLMClient()

    try:
        raw = await client.invoke(system=system, human=human, task=ModelTask.FAST)

        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        data = json.loads(raw)
        refined_query = data.get("refined_query", current_query)
        reasoning = data.get("reasoning", "")

        print(f"  │ ✅ Refined query: {refined_query[:100]}")
        print(f"  │    Reasoning: {reasoning[:120]}")
        print(f"  └──────────────────────────────────────")
        logger.info(
            "query_refinement_complete",
            refined_query=refined_query[:80],
            reasoning=reasoning[:100],
        )

        return {
            "refined_query": refined_query,
            "keyword_query": refined_query,   # override keyword query for re-search
            "refinement_count": refinement_count + 1,
            # Reset search results so retrieval nodes re-execute
            "pubmed_results": [],
            "mesh_results": [],
            "semantic_results": [],
            "fused_results": [],
            "reranked_results": [],
        }

    except Exception as e:
        print(f"  │ ❌ Query refinement FAILED: {e}")
        print(f"  └──────────────────────────────────────")
        logger.error("query_refinement_failed", error=str(e))
        # Bump count even on failure to avoid infinite loop
        return {
            "refinement_count": refinement_count + 1,
            "errors": state.get("errors", []) + [f"query_refinement: {e}"],
        }
