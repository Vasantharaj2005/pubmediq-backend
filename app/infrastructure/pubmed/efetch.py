"""
PubMedIQ — PubMed EFetch (Article Metadata Retrieval)

Fetches full article metadata for a list of PMIDs.
Uses the XML format for richest data (abstracts, MeSH terms, authors).
"""
from __future__ import annotations

import xmltodict

from app.core.logging import get_logger
from app.infrastructure.pubmed.client import PubMedClient
from app.infrastructure.pubmed.exceptions import PubMedParseError
from app.infrastructure.pubmed.models import PubMedArticle, PubMedAuthor

logger = get_logger(__name__)

_BATCH_SIZE = 20  # NCBI recommends batches of ≤200, but 20 is safer with rate limits


async def efetch(pmids: list[str]) -> list[PubMedArticle]:
    """
    Fetch full article metadata for a list of PMIDs.

    Args:
        pmids: List of PubMed IDs to fetch.

    Returns:
        List of PubMedArticle objects (may be smaller than input if some fail).
    """
    if not pmids:
        return []

    articles: list[PubMedArticle] = []

    # Process in batches
    for i in range(0, len(pmids), _BATCH_SIZE):
        batch = pmids[i : i + _BATCH_SIZE]
        batch_articles = await _fetch_batch(batch)
        articles.extend(batch_articles)

    logger.info("efetch_complete", requested=len(pmids), fetched=len(articles))
    return articles


async def _fetch_batch(pmids: list[str]) -> list[PubMedArticle]:
    """Fetch a single batch of PMIDs."""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }

    async with PubMedClient() as client:
        try:
            xml_text = await client.get_raw("/efetch.fcgi", params=params)
        except Exception as e:
            logger.error("efetch_batch_failed", pmids=pmids[:5], error=str(e))
            return []

    return _parse_xml(xml_text)


def _parse_xml(xml_text: str) -> list[PubMedArticle]:
    """Parse PubMed XML response into PubMedArticle objects."""
    try:
        data = xmltodict.parse(xml_text, force_list=("PubmedArticle", "Author", "MeshHeading", "Keyword"))
    except Exception as e:
        logger.error("efetch_xml_parse_failed", error=str(e))
        return []

    pub_articles = (
        data.get("PubmedArticleSet", {})
        .get("PubmedArticle", [])
    )

    articles: list[PubMedArticle] = []
    for raw in pub_articles:
        try:
            article = _extract_article(raw)
            if article:
                articles.append(article)
        except Exception as e:
            logger.warning("efetch_article_extract_failed", error=str(e))
            continue

    return articles


def _extract_article(raw: dict) -> PubMedArticle | None:
    """Extract a PubMedArticle from a parsed XML dict."""
    medline = raw.get("MedlineCitation", {})
    article_data = medline.get("Article", {})

    # PMID
    pmid_raw = medline.get("PMID", {})
    if isinstance(pmid_raw, dict):
        pmid = str(pmid_raw.get("#text", ""))
    else:
        pmid = str(pmid_raw)

    if not pmid:
        return None

    # Title
    title_raw = article_data.get("ArticleTitle", "")
    if isinstance(title_raw, dict):
        title = title_raw.get("#text", "")
    else:
        title = str(title_raw) if title_raw else None

    # Abstract
    abstract_raw = article_data.get("Abstract", {})
    if isinstance(abstract_raw, dict):
        abstract_text = abstract_raw.get("AbstractText", "")
        if isinstance(abstract_text, list):
            # Structured abstract: join sections
            abstract = " ".join(
                (item.get("#text", "") if isinstance(item, dict) else str(item))
                for item in abstract_text
            )
        elif isinstance(abstract_text, dict):
            abstract = abstract_text.get("#text", "")
        else:
            abstract = str(abstract_text) if abstract_text else None
    else:
        abstract = None

    # Authors
    author_list_raw = article_data.get("AuthorList", {})
    authors_raw = author_list_raw.get("Author", []) if isinstance(author_list_raw, dict) else []
    authors = [_extract_author(a) for a in authors_raw if isinstance(a, dict)]

    # Journal
    journal_info = article_data.get("Journal", {})
    journal = None
    journal_abbr = None
    if isinstance(journal_info, dict):
        journal = journal_info.get("Title") or journal_info.get("ISOAbbreviation")
        journal_abbr = journal_info.get("ISOAbbreviation")

    # Year
    pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {}) if isinstance(journal_info, dict) else {}
    year = None
    if isinstance(pub_date, dict):
        year_raw = pub_date.get("Year") or pub_date.get("MedlineDate", "")[:4]
        try:
            year = int(year_raw) if year_raw else None
        except (ValueError, TypeError):
            year = None

    # Publication types
    pub_types_raw = article_data.get("PublicationTypeList", {})
    if isinstance(pub_types_raw, dict):
        pt_list = pub_types_raw.get("PublicationType", [])
        if not isinstance(pt_list, list):
            pt_list = [pt_list]
        pub_types = [
            (item.get("#text", "") if isinstance(item, dict) else str(item))
            for item in pt_list
        ]
    else:
        pub_types = []

    # MeSH terms
    mesh_list = medline.get("MeshHeadingList", {})
    mesh_terms: list[str] = []
    if isinstance(mesh_list, dict):
        headings = mesh_list.get("MeshHeading", [])
        for heading in headings:
            if isinstance(heading, dict):
                desc = heading.get("DescriptorName", {})
                if isinstance(desc, dict):
                    term = desc.get("#text", "")
                else:
                    term = str(desc)
                if term:
                    mesh_terms.append(term)

    # Keywords
    kw_list = medline.get("KeywordList", {})
    keywords: list[str] = []
    if isinstance(kw_list, dict):
        kw_items = kw_list.get("Keyword", [])
        if not isinstance(kw_items, list):
            kw_items = [kw_items]
        keywords = [
            (k.get("#text", "") if isinstance(k, dict) else str(k))
            for k in kw_items
        ]

    # DOI
    article_ids = raw.get("PubmedData", {}).get("ArticleIdList", {})
    doi = None
    if isinstance(article_ids, dict):
        id_list = article_ids.get("ArticleId", [])
        if not isinstance(id_list, list):
            id_list = [id_list]
        for aid in id_list:
            if isinstance(aid, dict) and aid.get("@IdType") == "doi":
                doi = aid.get("#text")

    return PubMedArticle(
        pmid=pmid,
        title=title,
        abstract=abstract,
        authors=authors,
        journal=journal,
        journal_abbr=journal_abbr,
        year=year,
        pub_types=pub_types,
        mesh_terms=mesh_terms,
        keywords=keywords,
        doi=doi,
    )


def _extract_author(raw: dict) -> PubMedAuthor:
    """Extract a PubMedAuthor from XML dict."""
    affiliation = None
    aff_raw = raw.get("AffiliationInfo", {})
    if isinstance(aff_raw, dict):
        affiliation = aff_raw.get("Affiliation")
    elif isinstance(aff_raw, list) and aff_raw:
        first = aff_raw[0]
        if isinstance(first, dict):
            affiliation = first.get("Affiliation")

    return PubMedAuthor(
        last_name=raw.get("LastName"),
        fore_name=raw.get("ForeName") or raw.get("Initials"),
        affiliation=affiliation,
    )
