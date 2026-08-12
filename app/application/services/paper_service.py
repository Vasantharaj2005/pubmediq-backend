"""
PubMedIQ — Paper Service

Handles individual PubMed article retrieval and bookmark management.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperAlreadySavedError, PaperNotFoundError
from app.core.logging import get_logger
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.database.repositories.paper_repository import PaperRepository
from app.infrastructure.pubmed.efetch import efetch
from app.schemas.paper import PaperDetail, PaperSummary, SavePaperResponse

logger = get_logger(__name__)


class PaperService:
    """Manages paper retrieval and user bookmarks."""

    def __init__(self, db: AsyncSession, cache: CacheService | None = None) -> None:
        self._repo = PaperRepository(db)
        self._cache = cache

    async def get_paper(self, pmid: str, user_id: str | None = None) -> PaperDetail:
        """Fetch full article metadata from PubMed (with cache)."""
        # Check cache
        if self._cache:
            cached = await self._cache.get_cached_article(pmid)
            if cached:
                is_saved = False
                if user_id:
                    is_saved = await self._repo.is_saved(user_id, pmid)
                return PaperDetail(**{**cached, "is_saved": is_saved})

        articles = await efetch([pmid])
        if not articles:
            raise PaperNotFoundError(detail=f"PubMed article {pmid} not found.")

        article = articles[0]
        is_saved = False
        if user_id:
            is_saved = await self._repo.is_saved(user_id, pmid)

        detail = PaperDetail(
            pmid=article.pmid,
            title=article.title,
            abstract=article.abstract,
            authors=[a.full_name for a in article.authors],
            journal=article.journal,
            journal_abbr=article.journal_abbr,
            year=article.year,
            pub_types=article.pub_types,
            mesh_terms=article.mesh_terms,
            keywords=article.keywords,
            doi=article.doi,
            pubmed_url=article.pubmed_url,
            is_saved=is_saved,
        )

        if self._cache:
            await self._cache.cache_article(pmid, detail.model_dump(exclude={"is_saved"}))

        return detail

    async def save_paper(self, user_id: str, pmid: str) -> SavePaperResponse:
        """Bookmark a paper for a user."""
        if await self._repo.is_saved(user_id, pmid):
            raise PaperAlreadySavedError()

        # Fetch metadata to store title/journal/year
        articles = await efetch([pmid])
        title = journal = None
        year = None
        if articles:
            a = articles[0]
            title, journal, year = a.title, a.journal, a.year

        await self._repo.save(user_id, pmid, title=title, journal=journal, year=year)
        return SavePaperResponse(pmid=pmid, saved=True, message="Paper saved to your library.")

    async def unsave_paper(self, user_id: str, pmid: str) -> SavePaperResponse:
        """Remove a paper from a user's bookmarks."""
        deleted = await self._repo.unsave(user_id, pmid)
        return SavePaperResponse(pmid=pmid, saved=False, message="Paper removed from library.")

    async def get_saved_papers(self, user_id: str) -> list[PaperSummary]:
        """Return all papers saved by a user."""
        saved = await self._repo.get_saved_by_user(user_id)
        return [
            PaperSummary(
                pmid=p.pmid,
                title=p.title,
                journal=p.journal,
                year=p.year,
                pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{p.pmid}/",
            )
            for p in saved
        ]
