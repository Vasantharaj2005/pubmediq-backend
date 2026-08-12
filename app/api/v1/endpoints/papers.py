"""
PubMedIQ — Paper Endpoints

GET    /papers/{pmid}        → Full article metadata
POST   /papers/{pmid}/save   → Bookmark a paper
DELETE /papers/{pmid}/save   → Remove bookmark
GET    /papers/saved         → List all saved papers
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_optional_user, require_active_user
from app.application.services.paper_service import PaperService
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.schemas.paper import PaperDetail, PaperSummary, SavePaperResponse

router = APIRouter(prefix="/papers", tags=["Papers"])


def _get_cache() -> CacheService:
    return CacheService(redis_client)


@router.get(
    "/saved",
    response_model=list[PaperSummary],
    summary="List all saved papers",
)
async def get_saved_papers(
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache),
) -> list[PaperSummary]:
    """Return all papers bookmarked by the current user."""
    service = PaperService(db=db, cache=cache)
    return await service.get_saved_papers(str(current_user.id))


@router.get(
    "/{pmid}",
    response_model=PaperDetail,
    summary="Get full article metadata",
)
async def get_paper(
    pmid: str,
    current_user: UserModel | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache),
) -> PaperDetail:
    """
    Fetch complete metadata for a PubMed article by PMID.

    Includes: title, abstract, authors, journal, year, MeSH terms, DOI.
    """
    user_id = str(current_user.id) if current_user else None
    service = PaperService(db=db, cache=cache)
    return await service.get_paper(pmid, user_id=user_id)


@router.post(
    "/{pmid}/save",
    response_model=SavePaperResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a paper to library",
)
async def save_paper(
    pmid: str,
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache),
) -> SavePaperResponse:
    """Bookmark a PubMed article for later reference."""
    service = PaperService(db=db, cache=cache)
    return await service.save_paper(str(current_user.id), pmid)


@router.delete(
    "/{pmid}/save",
    response_model=SavePaperResponse,
    summary="Remove a paper from library",
)
async def unsave_paper(
    pmid: str,
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache),
) -> SavePaperResponse:
    """Remove a bookmarked paper from the user's library."""
    service = PaperService(db=db, cache=cache)
    return await service.unsave_paper(str(current_user.id), pmid)
