"""
PubMedIQ — Agent Node: MeSH Search (Tool, No LLM)

Retrieves PubMed articles using MeSH controlled vocabulary terms.
MeSH search is more precise than keyword search and catches
indexed synonyms automatically.
"""
from __future__ import annotations

from app.agents.state import ResearchState
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.pubmed.efetch import efetch
from app.infrastructure.pubmed.esearch import esearch, esearch_mesh

logger = get_logger(__name__)


async def mesh_search_node(state: ResearchState) -> dict:
    """
    LangGraph node: MeSH-based PubMed search.

    Input state:  mesh_query, mesh_terms, filters, top_k
    Output state: mesh_results
    """
    mesh_query = state.get("mesh_query", "")
    mesh_terms = state.get("mesh_terms", [])
    filters = state.get("filters", {})
    top_k = state.get("top_k", settings.DEFAULT_TOP_K)

    if not mesh_query and not mesh_terms:
        logger.warning("mesh_search_no_query")
        return {"mesh_results": []}

    logger.info("node_mesh_search", mesh_terms=len(mesh_terms))

    try:
        # Prefer the pre-built mesh_query if available; fall back to mesh_terms
        query = mesh_query if mesh_query else ""
        if not query and mesh_terms:
            from app.infrastructure.pubmed.esearch import esearch_mesh
            pmids = await esearch_mesh(mesh_terms, retmax=top_k * 2)
        else:
            pmids = await esearch(
                query=query,
                retmax=top_k * 2,
                year_from=filters.get("year_from"),
                year_to=filters.get("year_to"),
            )

        if not pmids:
            return {"mesh_results": []}

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
                "source": "mesh",
                "mesh_rank": i + 1,
            }
            for i, a in enumerate(articles)
        ]

        logger.info("mesh_search_complete", result_count=len(results))
        return {"mesh_results": results}

    except Exception as e:
        logger.error("mesh_search_failed", error=str(e))
        return {
            "mesh_results": [],
            "errors": state.get("errors", []) + [f"mesh_search: {e}"],
        }
