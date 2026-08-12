"""
PubMedIQ — Agent Node: Re-ranker (Model-based, No LLM API)

Uses a local cross-encoder model to score (query, abstract) pairs.
cross-encoder/ms-marco-MiniLM-L-6-v2 is free, open-source, and fast.

Cross-encoder advantage over bi-encoder:
- Sees both query and document simultaneously → better relevance judgment
- More accurate than cosine similarity for retrieval re-ranking
"""
from __future__ import annotations

import asyncio
from functools import lru_cache

from app.agents.state import ResearchState
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_reranker():
    """Lazy-load the cross-encoder model (cached after first call)."""
    try:
        from sentence_transformers import CrossEncoder

        logger.info("reranker_loading", model=settings.RERANKER_MODEL)
        model = CrossEncoder(
            settings.RERANKER_MODEL,
            device=settings.RERANKER_DEVICE,
            max_length=512,
        )
        logger.info("reranker_loaded")
        return model
    except Exception as e:
        logger.error("reranker_load_failed", error=str(e))
        return None


def _rerank_sync(query: str, candidates: list[dict]) -> list[dict]:
    """Synchronous reranking (run in executor to avoid event loop blocking)."""
    model = _load_reranker()

    if model is None:
        # Fallback: use RRF score as the rerank score
        logger.warning("reranker_unavailable_using_rrf")
        for paper in candidates:
            paper["rerank_score"] = paper.get("rrf_score", 0.0)
        return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

    # Build input pairs: [(query, title + abstract), ...]
    pairs = []
    for paper in candidates:
        title = paper.get("title", "") or ""
        abstract = (paper.get("abstract", "") or "")[:400]  # truncate for speed
        doc_text = f"{title}. {abstract}".strip()
        pairs.append([query, doc_text])

    try:
        scores = model.predict(pairs, show_progress_bar=False)
        for paper, score in zip(candidates, scores):
            paper["rerank_score"] = float(score)
    except Exception as e:
        logger.error("reranker_predict_failed", error=str(e))
        for paper in candidates:
            paper["rerank_score"] = paper.get("rrf_score", 0.0)

    return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)


async def reranker_node(state: ResearchState) -> dict:
    """
    LangGraph node: Re-rank fused results using cross-encoder.

    Input state:  fused_results, query
    Output state: reranked_results, quality_score
    """
    fused_results = state.get("fused_results", [])
    query = state.get("query", "")
    top_k = state.get("top_k", settings.DEFAULT_TOP_K)

    if not fused_results:
        return {"reranked_results": [], "quality_score": 0.0}

    logger.info("node_reranker", candidates=len(fused_results))

    # Limit candidates to avoid slow reranking of huge lists
    candidates = fused_results[: top_k * 3]

    loop = asyncio.get_event_loop()
    reranked = await loop.run_in_executor(None, _rerank_sync, query, candidates)

    # Normalize rerank scores to [0, 1] using sigmoid
    import math
    for paper in reranked:
        raw = paper.get("rerank_score", 0.0)
        paper["rerank_score"] = 1.0 / (1.0 + math.exp(-raw))

    # Calculate quality score as average of top-10 rerank scores
    top_results = reranked[:10]
    quality_score = (
        sum(p.get("rerank_score", 0.0) for p in top_results) / len(top_results)
        if top_results else 0.0
    )

    logger.info(
        "reranker_complete",
        reranked_count=len(reranked),
        quality_score=round(quality_score, 4),
    )

    return {
        "reranked_results": reranked[:top_k],
        "quality_score": quality_score,
    }
