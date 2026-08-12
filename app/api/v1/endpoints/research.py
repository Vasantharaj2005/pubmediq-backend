"""
PubMedIQ — Research Endpoints

POST /research/summarize    → Summarize multiple papers
POST /research/compare      → Compare multiple papers
POST /research/gap-analysis → Identify research gaps
POST /research/ask          → Follow-up question on search session
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_active_user
from app.application.services.research_service import ResearchService
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.schemas.research import (
    AskRequest,
    CompareRequest,
    GapAnalysisRequest,
    ResearchResponse,
    SummarizeRequest,
)

router = APIRouter(prefix="/research", tags=["Research"])


def _get_cache() -> CacheService:
    return CacheService(redis_client)


@router.post("/summarize", response_model=ResearchResponse, summary="Summarize multiple papers")
async def summarize(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_active_user),
) -> ResearchResponse:
    """Generate a concise evidence-based summary for 1-10 PubMed articles."""
    service = ResearchService(db=db)
    return await service.summarize(request)


@router.post("/compare", response_model=ResearchResponse, summary="Compare multiple papers")
async def compare(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_active_user),
) -> ResearchResponse:
    """Systematically compare 2-5 PubMed articles on key dimensions."""
    service = ResearchService(db=db)
    return await service.compare(request)


@router.post("/gap-analysis", response_model=ResearchResponse, summary="Research gap analysis")
async def gap_analysis(
    request: GapAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_active_user),
) -> ResearchResponse:
    """Identify research gaps and unanswered questions from a set of papers."""
    service = ResearchService(db=db)
    return await service.gap_analysis(request)


@router.post("/ask", response_model=ResearchResponse, summary="Ask a follow-up question")
async def ask(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_active_user),
    cache: CacheService = Depends(_get_cache),
) -> ResearchResponse:
    """
    Ask a follow-up question about a previous search session.

    Example: "Which study had the largest sample size?"
    """
    service = ResearchService(db=db, cache=cache)
    return await service.ask(request, cache=cache)
