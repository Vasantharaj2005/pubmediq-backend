"""
PubMedIQ — Agent Node: Quality Gate (Deterministic)

Evaluates whether the retrieved results meet quality standards.
Routes to answer generation (GOOD) or query refinement (REFINE).

This is a deterministic node — no LLM or model needed.
"""
from __future__ import annotations

from app.agents.state import ResearchState
from app.core.constants import MAX_REFINEMENTS, QUALITY_THRESHOLD
from app.core.logging import get_logger

logger = get_logger(__name__)


def quality_gate_router(state: ResearchState) -> str:
    """
    LangGraph conditional edge function.

    Returns:
        "synthesize" → results are good enough → go to answer_generator
        "refine"     → results are poor → go to query_refinement
        "synthesize" → max refinements reached → accept what we have
    """
    quality_score = state.get("quality_score", 0.0)
    refinement_count = state.get("refinement_count", 0)
    reranked_results = state.get("reranked_results", [])

    # If we have no results at all, check refinement budget
    if not reranked_results:
        if refinement_count < MAX_REFINEMENTS:
            logger.info("quality_gate_no_results_refine", refinements=refinement_count)
            return "refine"
        logger.info("quality_gate_no_results_accept")
        return "synthesize"

    # If quality is sufficient → generate answer
    if quality_score >= QUALITY_THRESHOLD:
        logger.info(
            "quality_gate_pass",
            score=round(quality_score, 4),
            threshold=QUALITY_THRESHOLD,
        )
        return "synthesize"

    # If refinement budget is exhausted → accept current results
    if refinement_count >= MAX_REFINEMENTS:
        logger.info(
            "quality_gate_max_refinements",
            score=round(quality_score, 4),
            refinement_count=refinement_count,
        )
        return "synthesize"

    # Results are poor and we have budget → refine
    logger.info(
        "quality_gate_fail_refine",
        score=round(quality_score, 4),
        threshold=QUALITY_THRESHOLD,
        refinements_remaining=MAX_REFINEMENTS - refinement_count,
    )
    return "refine"


async def quality_gate_node(state: ResearchState) -> dict:
    """
    LangGraph node: Annotate quality level on state.
    The actual routing is done via the conditional edge (quality_gate_router).
    """
    quality_score = state.get("quality_score", 0.0)

    if quality_score >= 0.80:
        quality_level = "high"
    elif quality_score >= QUALITY_THRESHOLD:
        quality_level = "medium"
    else:
        quality_level = "low"

    logger.info(
        "quality_gate_evaluated",
        score=round(quality_score, 4),
        level=quality_level,
    )

    return {"quality_level": quality_level}
