"""
PubMedIQ — Agent Tools: PubMed

LangChain @tool wrappers for PubMed E-Utils operations.
Used when agent nodes need to call PubMed as a LangChain tool.
"""
from __future__ import annotations

from langchain_core.tools import tool

from app.infrastructure.pubmed.efetch import efetch
from app.infrastructure.pubmed.esearch import esearch


@tool
async def pubmed_search(query: str, max_results: int = 20) -> str:
    """
    Search PubMed using a keyword query.
    Returns a list of PMIDs and their titles.

    Args:
        query: PubMed search query string.
        max_results: Maximum number of results to return (default: 20).
    """
    pmids = await esearch(query, retmax=max_results)
    if not pmids:
        return "No results found."

    articles = await efetch(pmids[:10])
    lines = [f"Found {len(pmids)} results:"]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. PMID:{a.pmid} - {a.title or 'No title'} ({a.year or 'N/A'})")

    return "\n".join(lines)


@tool
async def pubmed_fetch_article(pmid: str) -> str:
    """
    Fetch full metadata for a specific PubMed article.

    Args:
        pmid: The PubMed ID of the article.
    """
    articles = await efetch([pmid])
    if not articles:
        return f"Article {pmid} not found."

    a = articles[0]
    return (
        f"PMID: {a.pmid}\n"
        f"Title: {a.title}\n"
        f"Authors: {a.author_string}\n"
        f"Journal: {a.journal} ({a.year})\n"
        f"MeSH: {', '.join(a.mesh_terms[:5])}\n"
        f"Abstract: {(a.abstract or '')[:500]}"
    )
