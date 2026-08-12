"""
PubMedIQ — Agent Node: Keyword Search (Tool, No LLM)

Retrieves PubMed articles using keyword Boolean query.
Fetches full metadata for the top results.
"""
from __future__ import annotations

from app.agents.state import ResearchState
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.pubmed.efetch import efetch
from app.infrastructure.pubmed.esearch import esearch

logger = get_logger(__name__)


async def keyword_search_node(state: ResearchState) -> dict:
    """
    LangGraph node: Keyword-based PubMed search.

    Input state:  keyword_query, filters, top_k
    Output state: pubmed_results
    """
    keyword_query = state.get("keyword_query", "")
    filters = state.get("filters", {})
    top_k = state.get("top_k", settings.DEFAULT_TOP_K)

    if not keyword_query:
        logger.warning("keyword_search_no_query")
        return {"pubmed_results": []}

    logger.info("node_keyword_search", query=keyword_query[:80])

    try:
        pmids = await esearch(
            query=keyword_query,
            retmax=top_k * 2,  # fetch more than needed for fusion
            year_from=filters.get("year_from"),
            year_to=filters.get("year_to"),
            pub_type=filters.get("study_type"),
        )

        if not pmids:
            logger.info("keyword_search_no_pmids")
            return {"pubmed_results": []}

        articles = await efetch(pmids[:top_k])
        results = [
            {
                "pmid": a.pmid,
                "title": a.title,
                "abstract": a.abstract,
                "authors": [auth.full_name for auth in a.authors],
                "journal": a.journal,
                "year": a.year,
                "pub_types": a.pub_types,
                "mesh_terms": a.mesh_terms,
                "keywords": a.keywords,
                "doi": a.doi,
                "pubmed_url": a.pubmed_url,
                "source": "keyword",
                "keyword_rank": i + 1,
            }
            for i, a in enumerate(articles)
        ]

        logger.info("keyword_search_complete", result_count=len(results))
        return {"pubmed_results": results}

    except Exception as e:
        logger.error("keyword_search_failed", error=str(e))
        return {
            "pubmed_results": [],
            "errors": state.get("errors", []) + [f"keyword_search: {e}"],
        }
