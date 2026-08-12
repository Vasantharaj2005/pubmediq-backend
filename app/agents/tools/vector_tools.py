"""
PubMedIQ — Agent Tools: Vector (Semantic) Search
"""
from __future__ import annotations

from langchain_core.tools import tool

from app.infrastructure.vectorstore.embeddings import embedding_service
from app.infrastructure.vectorstore.pinecone_client import pinecone_client


@tool
async def semantic_search(query: str, top_k: int = 10) -> str:
    """
    Perform semantic vector search over the PubMed article index.
    Returns the most semantically relevant articles.

    Args:
        query: Natural language query text.
        top_k: Number of results to return (default: 10).
    """
    if not pinecone_client.is_available:
        return "Semantic search is unavailable (Pinecone not configured)."

    try:
        vector = await embedding_service.embed_query(query)
        matches = await pinecone_client.query(vector=vector, top_k=top_k)

        if not matches:
            return "No semantically similar articles found."

        lines = [f"Semantic search results for '{query[:50]}':\n"]
        for i, m in enumerate(matches, 1):
            title = m.metadata.get("title", "No title")
            year = m.metadata.get("year", "N/A")
            lines.append(f"{i}. PMID:{m.pmid} (score:{m.score:.3f}) - {title} ({year})")

        return "\n".join(lines)
    except Exception as e:
        return f"Semantic search failed: {e}"
