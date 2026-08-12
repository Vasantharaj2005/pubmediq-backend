"""
PubMedIQ — Agent Tools: MeSH Vocabulary Lookup

Looks up MeSH terms via NCBI E-Utils (no LLM needed).
"""
from __future__ import annotations

from langchain_core.tools import tool

from app.infrastructure.pubmed.client import PubMedClient


@tool
async def lookup_mesh_term(term: str) -> str:
    """
    Look up a biomedical concept in the NCBI MeSH vocabulary.
    Returns the official MeSH descriptor name and related terms.

    Args:
        term: The biomedical concept to look up (e.g., "depression", "exercise").
    """
    params = {
        "db": "mesh",
        "term": term,
        "retmax": 5,
        "retmode": "json",
    }
    try:
        async with PubMedClient() as client:
            data = await client.get("/esearch.fcgi", params=params)
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "0")
        if not id_list:
            return f"No MeSH term found for '{term}'."
        return f"MeSH lookup for '{term}': found {count} matching descriptors. IDs: {id_list[:3]}"
    except Exception as e:
        return f"MeSH lookup failed: {e}"
