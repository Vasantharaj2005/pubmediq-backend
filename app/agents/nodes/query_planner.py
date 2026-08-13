"""
PubMedIQ — Agent Node: Query Planner (Logic, No LLM)

Builds structured PubMed queries from concepts and MeSH terms.
This is a deterministic logic node — no LLM needed.
"""
from __future__ import annotations

from app.agents.state import ResearchState
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_keyword_query(
    facets: dict[str, list[str]],
    filters: dict,
) -> str:
    """
    Build a PubMed keyword query with Boolean operators using a facet-based approach.

    Strategy:
      Terms within the same facet (e.g., condition) are ORed together.
      Different facets (e.g., condition AND intervention) are ANDed together.

    Example:
      ("Alzheimer's disease" OR "Alzheimer disease" OR "senile dementia")
      AND (treatment OR therapy OR intervention)
    """
    groups: list[str] = []

    for facet, terms in facets.items():
        if not terms:
            continue
        # Limit to top 5 terms per facet to avoid excessively long queries
        facet_terms = terms[:5]
        
        # Quote multi-word terms
        quoted = [f'"{t}"' if " " in t else t for t in facet_terms]
        group = " OR ".join(quoted)
        groups.append(f"({group})")

    if len(groups) > 1:
        query = " AND ".join(groups)
    elif len(groups) == 1:
        query = groups[0]
    else:
        query = ""

    return query


def _build_mesh_query(mesh_terms: list[str]) -> str:
    """
    Build a MeSH-tagged PubMed query.
    Uses the [MeSH Terms] field tag for precise indexing.
    """
    if not mesh_terms:
        return ""
    tagged = [f'"{term}"[MeSH]' for term in mesh_terms[:8]]
    return " AND ".join(tagged)


async def query_planner_node(state: ResearchState) -> dict:
    """
    LangGraph node: Build keyword, MeSH, and semantic queries.

    Input state:  concepts, synonyms, mesh_terms, filters
    Output state: keyword_query, mesh_query, semantic_query, search_strategy
    """
    facets = state.get("facets", {})
    mesh_terms = state.get("mesh_terms", [])
    filters = state.get("filters", {})
    query = state.get("query", "")

    logger.info(
        "node_query_planner",
        facets_count=len(facets),
        mesh_terms=len(mesh_terms),
    )

    keyword_query = _build_keyword_query(facets, filters)
    mesh_query = _build_mesh_query(mesh_terms)

    # If we couldn't build queries from concepts, fall back to raw query
    if not keyword_query:
        keyword_query = query
    if not mesh_query and mesh_terms:
        mesh_query = " AND ".join(f'"{t}"[MeSH]' for t in mesh_terms[:5])

    # Semantic query = original query (will be embedded by semantic_search node)
    semantic_query = query

    search_strategy = {
        "keyword_query": keyword_query,
        "mesh_query": mesh_query,
        "semantic_search": True,
        "mesh_terms": mesh_terms,
        "facets": facets,
    }

    logger.info(
        "query_planner_complete",
        keyword_len=len(keyword_query),
        mesh_len=len(mesh_query),
    )

    return {
        "keyword_query": keyword_query,
        "mesh_query": mesh_query,
        "semantic_query": semantic_query,
        "search_strategy": search_strategy,
    }
