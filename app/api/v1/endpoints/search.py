"""
PubMedIQ — Search Endpoints

POST /search          → Run the full LangGraph hybrid search pipeline
POST /search/refine   → Manually refine an existing search
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_optional_user
from app.application.services.search_service import SearchService
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.schemas.search import RefineRequest, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])


def _get_cache() -> CacheService:
    return CacheService(redis_client)


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic hybrid search over PubMed",
    description=(
        "Runs the full PubMedIQ pipeline: query understanding → concept mapping → "
        "hybrid retrieval (keyword + MeSH + semantic) → fusion → re-ranking → "
        "quality gate → evidence synthesis."
    ),
)
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel | None = Depends(get_optional_user),
    cache: CacheService = Depends(_get_cache),
) -> SearchResponse:
    """
    Execute a full PubMedIQ search.

    Example query: "What is the effect of exercise on depression in elderly patients?"

    The pipeline:
    1. Extracts research intent (population, intervention, condition, outcome)
    2. Maps to biomedical concepts and MeSH terms
    3. Runs parallel keyword + MeSH + semantic retrieval
    4. Fuses results using Reciprocal Rank Fusion
    5. Re-ranks using cross-encoder model
    6. Generates evidence-grounded AI summary with PMID citations
    """
    user_id = str(current_user.id) if current_user else None
    service = SearchService(db=db, cache=cache)
    return await service.run(request, user_id=user_id)


@router.post(
    "/refine",
    response_model=SearchResponse,
    summary="Refine an existing search",
)
async def refine_search(
    request: RefineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel | None = Depends(get_optional_user),
    cache: CacheService = Depends(_get_cache),
) -> SearchResponse:
    """
    Manually trigger query refinement for a session with unsatisfactory results.
    """
    session_state = None
    if cache:
        session_state = await cache.get_cached_session(request.session_id)

    if not session_state:
        from app.schemas.search import SearchResponse
        return SearchResponse(
            session_id=request.session_id,
            query="",
            results=[],
            total_results=0,
            ai_summary="Session not found. Please run a new search.",
        )

    search_request = SearchRequest(
        query=session_state.get("query", ""),
        top_k=session_state.get("top_k", 20),
    )
    user_id = str(current_user.id) if current_user else None
    service = SearchService(db=db, cache=cache)
    return await service.run(search_request, user_id=user_id)
