"""
PubMedIQ — Search Endpoints

POST /search          → Run the full LangGraph hybrid search pipeline
POST /search/refine   → Manually refine an existing search
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_optional_user
from app.application.services.search_service import SearchService
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.history_repository import HistoryRepository
from app.schemas.search import RefineRequest, SearchFilters, SearchRequest, SearchResponse

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
    description=(
        "Re-runs the search pipeline for a previous session. "
        "Looks up the original query from search_history (DB) "
        "or a Redis session cache, then re-executes with the same filters."
    ),
)
async def refine_search(
    request: RefineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel | None = Depends(get_optional_user),
    cache: CacheService = Depends(_get_cache),
) -> SearchResponse:
    """
    Manually trigger query refinement for a session with unsatisfactory results.

    Resolution order for session lookup:
      1. Redis session cache  (key: session:<id>)
      2. PostgreSQL search_history table  (id = session_id)

    The original query and filters are restored from the saved record.
    The optional `feedback` string is appended to the query to guide the LLM refiner.
    """
    session_query: str | None = None
    session_filters: SearchFilters | None = None
    session_top_k: int = 20

    # ------------------------------------------------------------------
    # 1. Try Redis session cache first (fast path)
    # ------------------------------------------------------------------
    session_state: dict | None = None
    if cache:
        session_state = await cache.get_cached_session(request.session_id)

    if session_state:
        # Security: verify ownership on the cached session too
        cached_user_id = session_state.get("user_id")
        requesting_user_id = str(current_user.id) if current_user else None
        if cached_user_id and requesting_user_id and cached_user_id != requesting_user_id:
            print(f"[Refine] DENY cross-user access via cache. session owner={cached_user_id[:8]}, requester={requesting_user_id[:8]}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to refine this session.",
            )
        session_query = session_state.get("query", "")
        session_top_k = session_state.get("top_k", 20)
        raw_filters = session_state.get("filters")
        if raw_filters:
            try:
                session_filters = SearchFilters(**raw_filters)
            except Exception:
                session_filters = None
        print(f"[Refine] Cache HIT for session '{request.session_id}'. query='{session_query[:60]}'")

    # ------------------------------------------------------------------
    # 2. Fall back to PostgreSQL search_history (persistent store)
    # ------------------------------------------------------------------
    if not session_query:
        print(f"\n[Refine] Cache MISS. Looking up session '{request.session_id}' in search_history DB...")
        history_repo = HistoryRepository(db)
        record = await history_repo.get_by_id(request.session_id)

        if not record:
            print(f"[Refine] ❌ Session '{request.session_id}' not found in DB.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Session '{request.session_id}' not found. "
                    "Please run a new search first."
                ),
            )

        # Security: ensure the session belongs to the requesting user
        if current_user and str(record.user_id) != str(current_user.id):
            print(f"[Refine] 🚫 Access denied — session belongs to a different user.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to refine this session.",
            )

        print(f"[Refine] ✅ Found session in DB. Query='{record.query[:60]}', "
              f"results={record.results_count}, quality={record.quality_score}")

        session_query = record.query

        # Restore filters from saved search_strategy if available
        if record.search_strategy:
            strategy = record.search_strategy
            try:
                session_filters = SearchFilters(
                    year_from=strategy.get("year_from"),
                    year_to=strategy.get("year_to"),
                    study_type=strategy.get("study_type"),
                    journal=strategy.get("journal"),
                )
            except Exception:
                session_filters = None

    # ------------------------------------------------------------------
    # 3. Build refined search request
    # ------------------------------------------------------------------
    # Append user feedback to guide the LLM query refiner
    refined_query = session_query
    if request.feedback:
        refined_query = f"{session_query} — {request.feedback}"
        print(f"[Refine] 📝 Feedback appended: '{request.feedback[:80]}'")

    search_request = SearchRequest(
        query=refined_query,
        filters=session_filters,
        top_k=session_top_k,
        session_id=request.session_id,
    )

    print(f"[Refine] 🚀 Launching refined pipeline for: '{refined_query[:80]}'")
    user_id = str(current_user.id) if current_user else None
    service = SearchService(db=db, cache=cache)
    return await service.run(search_request, user_id=user_id)
