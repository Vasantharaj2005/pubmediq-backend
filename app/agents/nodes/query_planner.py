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
    concepts: list[str],
    synonyms: dict[str, list[str]],
    filters: dict,
) -> str:
    """
    Build a PubMed keyword query with Boolean operators.

    Strategy:
      Each concept group is ORed, then groups are ANDed together.

    Example:
      (exercise OR "physical activity" OR "aerobic training")
      AND (depression OR "depressive disorder" OR "major depression")
      AND ("older adults" OR elderly OR "aged 65")
    """
    groups: list[str] = []

    for concept in concepts[:5]:  # limit to 5 main concepts
        terms = [concept]
        if concept in synonyms:
            terms.extend(synonyms[concept][:4])  # up to 4 synonyms

        # Quote multi-word terms
        quoted = [f'"{t}"' if " " in t else t for t in terms]
        group = " OR ".join(quoted)
        groups.append(f"({group})")

    query = " AND ".join(groups) if groups else ""
    return query


def _build_mesh_query(mesh_terms: list[str]) -> str:
    """
    Build a MeSH-tagged PubMed query.
    Uses the [MeSH Terms] field tag for precise indexing.
    """
    if not mesh_terms:
        return ""
    tagged = [f'"{term}"[MeSH Terms]' for term in mesh_terms[:8]]
    return " AND ".join(tagged)


async def query_planner_node(state: ResearchState) -> dict:
    """
    LangGraph node: Build keyword, MeSH, and semantic queries.

    Input state:  concepts, synonyms, mesh_terms, filters
    Output state: keyword_query, mesh_query, semantic_query, search_strategy
    """
    concepts = state.get("concepts", [])
    synonyms = state.get("synonyms", {})
    mesh_terms = state.get("mesh_terms", [])
    filters = state.get("filters", {})
    query = state.get("query", "")

    logger.info(
        "node_query_planner",
        concepts=len(concepts),
        mesh_terms=len(mesh_terms),
    )

    keyword_query = _build_keyword_query(concepts, synonyms, filters)
    mesh_query = _build_mesh_query(mesh_terms)

    # If we couldn't build queries from concepts, fall back to raw query
    if not keyword_query:
        keyword_query = query
    if not mesh_query and mesh_terms:
        mesh_query = " AND ".join(f'"{t}"[MeSH Terms]' for t in mesh_terms[:5])

    # Semantic query = original query (will be embedded by semantic_search node)
    semantic_query = query

    search_strategy = {
        "keyword_query": keyword_query,
        "mesh_query": mesh_query,
        "semantic_search": True,
        "mesh_terms": mesh_terms,
        "concepts": concepts,
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
