"""
PubMedIQ — Agent Node: Semantic Search (Tool, No LLM)

Retrieves articles from Pinecone using dense vector similarity.
The biomedical embedding model catches semantic equivalences that
keyword search misses (e.g., "physical activity" ↔ "exercise").
"""
from __future__ import annotations

from app.agents.state import ResearchState
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.vectorstore.embeddings import embedding_service
from app.infrastructure.vectorstore.pinecone_client import pinecone_client

logger = get_logger(__name__)


async def semantic_search_node(state: ResearchState) -> dict:
    """
    LangGraph node: Semantic vector search via Pinecone.

    Input state:  semantic_query, filters, top_k
    Output state: semantic_results
    """
    semantic_query = state.get("semantic_query", "")
    filters = state.get("filters", {})
    top_k = state.get("top_k", settings.DEFAULT_TOP_K)

    if not semantic_query:
        return {"semantic_results": []}

    if not pinecone_client.is_available:
        print(f"\n  ┌──────────────────────────────────────")
        print(f"  │ [Node 4c/9] 🧠 SEMANTIC SEARCH — SKIPPED (Pinecone unavailable)")
        print(f"  └──────────────────────────────────────")
        logger.warning("semantic_search_pinecone_unavailable")
        return {"semantic_results": []}

    print(f"\n  ┌──────────────────────────────────────")
    print(f"  │ [Node 4c/9] 🧠 SEMANTIC SEARCH (Pinecone + S-PubMedBert)")
    print(f"  │ Query: '{semantic_query[:80]}'")
    print(f"  ├──────────────────────────────────────")
    print(f"  │ Embedding query and querying Pinecone...")
    logger.info("node_semantic_search", query=semantic_query[:80])

    try:
        # Embed the query using the local biomedical model
        query_vector = await embedding_service.embed_query(semantic_query)

        # Build Pinecone metadata filter
        pinecone_filter: dict = {}
        if filters.get("year_from") or filters.get("year_to"):
            year_filter: dict = {}
            if filters.get("year_from"):
                year_filter["$gte"] = filters["year_from"]
            if filters.get("year_to"):
                year_filter["$lte"] = filters["year_to"]
            pinecone_filter["year"] = year_filter

        matches = await pinecone_client.query(
            vector=query_vector,
            top_k=top_k * 2,
            filter=pinecone_filter if pinecone_filter else None,
        )

        results = [
            {
                "pmid": m.pmid,
                "title": m.metadata.get("title"),
                "journal": m.metadata.get("journal"),
                "year": m.metadata.get("year"),
                "pub_types": m.metadata.get("pub_types", []),
                "mesh_terms": m.metadata.get("mesh_terms", []),
                "source": "semantic",
                "semantic_score": m.score,
                "semantic_rank": i + 1,
            }
            for i, m in enumerate(matches)
        ]

        print(f"  │ ✅ Pinecone returned {len(results)} semantic results.")
        if results:
            print(f"  │    Top scores: {[round(r['semantic_score'],4) for r in results[:5]]}")
        print(f"  └──────────────────────────────────────")
        logger.info("semantic_search_complete", result_count=len(results))
        return {"semantic_results": results}

    except Exception as e:
        print(f"  │ ❌ Semantic search FAILED: {e}")
        print(f"  └──────────────────────────────────────")
        logger.error("semantic_search_failed", error=str(e))
        return {
            "semantic_results": [],
            "errors": state.get("errors", []) + [f"semantic_search: {e}"],
        }
