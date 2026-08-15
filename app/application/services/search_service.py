"""
PubMedIQ — Search Service

Orchestrates the full LangGraph search pipeline.
Handles caching, history persistence, and result formatting.
"""
from __future__ import annotations

import sys
import uuid
from typing import Any

# Force UTF-8 output so emoji print statements don't crash on Windows (CP1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import get_compiled_graph
from app.agents.state import ResearchState
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.database.repositories.history_repository import HistoryRepository
from app.schemas.search import (
    PaperResult,
    SearchIntent,
    SearchQuality,
    SearchRequest,
    SearchResponse,
    SearchStrategy,
)

logger = get_logger(__name__)



class SearchService:
    """
    Orchestrates the complete PubMedIQ search pipeline.

    Flow:
      1. Check cache for repeated queries
      2. Initialize LangGraph state
      3. Run compiled research graph
      4. Format results as SearchResponse
      5. Save to history
      6. Cache results
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheService | None = None,
    ) -> None:
        self._db = db
        self._cache = cache
        self._history_repo = HistoryRepository(db)
        self._graph = get_compiled_graph()

    async def run(
        self,
        request: SearchRequest,
        user_id: str | None = None,
    ) -> SearchResponse:
        """
        Execute the full search pipeline.

        Args:
            request: Validated search request from the API layer.
            user_id: UUID of the authenticated user (optional for anonymous).

        Returns:
            Structured SearchResponse with results, AI summary, and citations.
        """
        session_id = request.session_id or str(uuid.uuid4())

        # 1. Check cache
        print(f"\n{'='*60}")
        print(f"🔍  PUBMEDIQ SEARCH PIPELINE STARTED")
        print(f"{'='*60}")
        print(f"   Query   : {request.query}")
        print(f"   TopK    : {request.top_k}")
        print(f"   Filters : {request.filters.model_dump(mode='json') if request.filters else 'none'}")
        print(f"   Session : {session_id}")
        print(f"{'='*60}")

        if self._cache:
            print(f"\n[Step 1/6] 🗄️  Checking Redis cache...")
            filters_dict = request.filters.model_dump() if request.filters else {}
            cached = await self._cache.get_cached_search(request.query, filters_dict)
            if cached:
                print(f"           ✅  Cache HIT — returning cached results instantly.")
                logger.info("search_cache_hit", session_id=session_id)
                response = SearchResponse(**cached)
                response.cached = True
                return response
            print(f"           ❌  Cache MISS — proceeding with full pipeline.")

        # 2. Build initial state
        print(f"\n[Step 2/6] 🧱  Building initial LangGraph state...")
        initial_state: ResearchState = {
            "query": request.query,
            "session_id": session_id,
            "top_k": request.top_k,
            "filters": request.filters.model_dump() if request.filters else {},
            "refinement_count": 0,
            "errors": [],
        }
        print(f"           ✅  State initialised.")

        # 3. Run LangGraph pipeline
        print(f"\n[Step 3/6] 🤖  Invoking LangGraph research pipeline...")
        print(f"           Graph nodes: query_understanding → concept_mapping → query_planner")
        print(f"                        → [keyword | mesh | semantic] (parallel)")
        print(f"                        → fusion → reranker → quality_gate → [synthesize | refine]")
        logger.info("search_pipeline_start", query=request.query[:80], session_id=session_id)
        try:
            final_state: ResearchState = await self._graph.ainvoke(initial_state)
            print(f"           ✅  Graph execution complete.")
        except Exception as e:
            print(f"           ❌  Graph execution FAILED: {e}")
            logger.error("search_pipeline_failed", error=str(e))
            return SearchResponse(
                session_id=session_id,
                query=request.query,
                results=[],
                total_results=0,
                ai_summary=f"Search pipeline encountered an error: {e}",
            )

        # 4. Format response
        print(f"\n[Step 4/6] 📋  Formatting results...")
        response = self._format_response(final_state, session_id)
        print(f"           ✅  {response.total_results} results formatted. Quality={response.quality.score if response.quality else 0:.4f}")

        # 5. Save to history (use session_id as the record PK so refine can look it up)
        print(f"\n[Step 5/6] Saving to search history...")
        if user_id:
            try:
                await self._history_repo.create(
                    record_id=session_id,         # <-- key fix: PK = session_id
                    user_id=user_id,
                    query=request.query,
                    intent=final_state.get("intent"),
                    search_strategy=final_state.get("search_strategy"),
                    results_count=response.total_results,
                    quality_score=final_state.get("quality_score"),
                    refined=final_state.get("refinement_count", 0) > 0,
                    refinement_count=final_state.get("refinement_count", 0),
                )
                print(f"           OK  History saved. record_id={session_id} user={user_id[:8]}...")
            except Exception as e:
                print(f"           WARN History save failed: {e}")
                logger.warning("history_save_failed", error=str(e))
        else:
            print(f"           --  Anonymous request — DB history not saved.")

        # 6. Cache results + session state
        print(f"\n[Step 6/6] Writing results to Redis cache...")
        if self._cache:
            try:
                filters_dict = request.filters.model_dump(mode="json") if request.filters else {}
                await self._cache.cache_search_results(
                    request.query, filters_dict, response.model_dump(mode="json")
                )
                # Also cache session state so /search/refine can find it (anonymous OR authenticated)
                session_state = {
                    "query": request.query,
                    "top_k": request.top_k,
                    "filters": filters_dict,
                    "user_id": user_id,
                }
                await self._cache.cache_session(session_id, session_state)
                print(f"           OK  Search results + session cached. session_id={session_id}")
            except Exception as e:
                print(f"           WARN Cache write failed: {e}")
                logger.warning("search_cache_write_failed", error=str(e))
        else:
            print(f"           --  Cache not configured — skipping.")  

        print(f"\n{'='*60}")
        print(f"✅  PIPELINE COMPLETE — {response.total_results} results returned")
        print(f"    Quality : {response.quality.score if response.quality else 0:.4f} ({response.quality.level if response.quality else 'n/a'})")
        print(f"    Refined : {response.quality.refined if response.quality else False} (x{response.quality.refinement_count if response.quality else 0})")
        print(f"    AI Summary chars: {len(response.ai_summary or '')}")
        print(f"{'='*60}\n")

        return response

    def _format_response(
        self, state: ResearchState, session_id: str
    ) -> SearchResponse:
        """Convert LangGraph state into a structured SearchResponse."""
        reranked = state.get("reranked_results", [])
        intent_data = state.get("intent")
        strategy_data = state.get("search_strategy")
        quality_score = state.get("quality_score", 0.0)

        # Format paper results
        results = []
        for paper in reranked:
            results.append(
                PaperResult(
                    pmid=paper.get("pmid", ""),
                    title=paper.get("title"),
                    abstract=paper.get("abstract"),
                    authors=paper.get("authors", []),
                    journal=paper.get("journal"),
                    year=paper.get("year"),
                    score=round(paper.get("rerank_score", paper.get("rrf_score", 0.0)), 4),
                    semantic_score=paper.get("semantic_score"),
                    pub_types=paper.get("pub_types", []),
                    mesh_terms=paper.get("mesh_terms", []),
                    match_reasons=paper.get("retrieval_sources", []),
                    pubmed_url=paper.get("pubmed_url") or f"https://pubmed.ncbi.nlm.nih.gov/{paper.get('pmid', '')}/",
                )
            )

        # Format intent
        intent = None
        if intent_data:
            intent = SearchIntent(**{
                k: v for k, v in intent_data.items()
                if k in SearchIntent.model_fields
            })

        # Format strategy
        strategy = None
        if strategy_data:
            strategy = SearchStrategy(
                keyword_query=strategy_data.get("keyword_query"),
                mesh_query=strategy_data.get("mesh_query"),
                semantic_search=True,
                mesh_terms=strategy_data.get("mesh_terms", []),
                concepts=strategy_data.get("concepts", []),
            )

        # Format quality
        quality = SearchQuality(
            score=round(quality_score, 4),
            level=state.get("quality_level", "low"),
            refined=state.get("refinement_count", 0) > 0,
            refinement_count=state.get("refinement_count", 0),
        )

        return SearchResponse(
            session_id=session_id,
            query=state.get("query", ""),
            intent=intent,
            results=results,
            total_results=len(results),
            search_strategy=strategy,
            quality=quality,
            ai_summary=state.get("final_answer"),
            citations=state.get("citations", []),
        )
