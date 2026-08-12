"""
PubMedIQ — Agent Node: Answer Generator (LLM)

Synthesizes an evidence-grounded answer from the top reranked papers.
Every factual claim must be cited with its PMID.

This is the final node in the pipeline for successful searches.
"""
from __future__ import annotations

import re

from app.agents.prompts.answer_generation import build_answer_prompt
from app.agents.state import ResearchState
from app.core.constants import SYNTHESIS_MAX_PAPERS
from app.core.logging import get_logger
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.model_router import ModelTask

logger = get_logger(__name__)

_PMID_RE = re.compile(r"\[PMID:\s*(\d+)\]")


async def answer_generator_node(state: ResearchState) -> dict:
    """
    LangGraph node: Generate a cited evidence-based answer.

    Input state:  reranked_results, query
    Output state: final_answer, citations
    """
    reranked_results = state.get("reranked_results", [])
    query = state.get("query", "")

    if not reranked_results:
        logger.warning("answer_generator_no_results")
        return {
            "final_answer": (
                "No relevant PubMed articles were found for this query. "
                "Please try rephrasing or broadening your search."
            ),
            "citations": [],
        }

    papers = reranked_results[:SYNTHESIS_MAX_PAPERS]
    logger.info("node_answer_generator", paper_count=len(papers))

    system, human = build_answer_prompt(query=query, papers=papers)
    client = LLMClient()

    try:
        answer = await client.invoke(
            system=system,
            human=human,
            task=ModelTask.REASONING,  # use the best available model for synthesis
        )

        # Extract cited PMIDs from the answer
        cited_pmids = list(dict.fromkeys(_PMID_RE.findall(answer)))  # deduplicated

        logger.info(
            "answer_generator_complete",
            answer_len=len(answer),
            citations=len(cited_pmids),
        )

        return {
            "final_answer": answer,
            "citations": cited_pmids,
        }

    except Exception as e:
        logger.error("answer_generator_failed", error=str(e))
        # Graceful fallback: return structured list of top papers
        fallback = _build_fallback_answer(papers)
        return {
            "final_answer": fallback,
            "citations": [p.get("pmid", "") for p in papers if p.get("pmid")],
            "errors": state.get("errors", []) + [f"answer_generator: {e}"],
        }


def _build_fallback_answer(papers: list[dict]) -> str:
    """Build a structured text summary without LLM when generation fails."""
    lines = ["**Top relevant papers found:**\n"]
    for i, p in enumerate(papers[:5], 1):
        title = p.get("title", "No title")
        pmid = p.get("pmid", "")
        year = p.get("year", "")
        journal = p.get("journal", "")
        lines.append(f"{i}. {title} [PMID: {pmid}] ({journal}, {year})")
    return "\n".join(lines)
