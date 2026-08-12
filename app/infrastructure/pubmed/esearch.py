"""
PubMedIQ — PubMed ESearch (Keyword / MeSH Search)

Returns a list of PMIDs matching a query.
ESearch supports full PubMed query syntax including MeSH terms.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.constants import PUBMED_DB, PUBMED_RETMODE
from app.core.logging import get_logger
from app.infrastructure.pubmed.client import PubMedClient
from app.infrastructure.pubmed.exceptions import PubMedAPIError

logger = get_logger(__name__)


async def esearch(
    query: str,
    retmax: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    pub_type: str | None = None,
    db: str = PUBMED_DB,
) -> list[str]:
    """
    Search PubMed using the ESearch endpoint.

    Args:
        query: Full PubMed query string (supports MeSH, Boolean operators, field tags).
        retmax: Maximum number of PMIDs to return.
        year_from: Filter to publications from this year onward.
        year_to: Filter to publications up to this year.
        pub_type: Filter by publication type (e.g., "Randomized Controlled Trial").
        db: NCBI database (default: "pubmed").

    Returns:
        List of PMID strings.
    """
    retmax = retmax or settings.PUBMED_MAX_RESULTS

    # Build query with optional filters
    full_query = query

    if year_from or year_to:
        yr_from = year_from or 1900
        yr_to = year_to or 2030
        full_query += f' AND ("{yr_from}"[PDAT] : "{yr_to}"[PDAT])'

    if pub_type:
        full_query += f' AND "{pub_type}"[PT]'

    params = {
        "db": db,
        "term": full_query,
        "retmax": retmax,
        "retmode": PUBMED_RETMODE,
        "usehistory": "n",
    }

    logger.info("pubmed_esearch", query=full_query[:100], retmax=retmax)

    async with PubMedClient() as client:
        try:
            data = await client.get("/esearch.fcgi", params=params)
        except Exception as e:
            logger.error("pubmed_esearch_failed", error=str(e))
            return []

    try:
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = int(data.get("esearchresult", {}).get("count", 0))
        logger.info("pubmed_esearch_complete", pmid_count=len(id_list), total=count)
        return [str(pmid) for pmid in id_list]
    except (KeyError, TypeError, ValueError) as e:
        logger.error("pubmed_esearch_parse_error", error=str(e))
        return []


async def esearch_mesh(mesh_terms: list[str], retmax: int | None = None) -> list[str]:
    """
    Search PubMed using a list of MeSH terms joined with OR.

    Args:
        mesh_terms: List of MeSH term strings.
        retmax: Maximum results.

    Returns:
        List of PMID strings.
    """
    if not mesh_terms:
        return []

    mesh_query = " OR ".join(f'"{term}"[MeSH Terms]' for term in mesh_terms)
    return await esearch(mesh_query, retmax=retmax)
