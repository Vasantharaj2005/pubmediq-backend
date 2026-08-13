"""
PubMedIQ — Agent Node: Result Fusion (Logic, No LLM)

Combines keyword, MeSH, and semantic results using
Reciprocal Rank Fusion (RRF) — a parameter-free fusion method
that consistently outperforms score-based interpolation.

RRF formula:
  score(d) = sum(1 / (k + rank(d, list)))
  where k=60 is a smoothing constant (Cormack et al., 2009)
"""
from __future__ import annotations

from app.agents.state import ResearchState
from app.core.constants import RRF_K
from app.core.logging import get_logger

logger = get_logger(__name__)


def _rrf_score(rank: int, k: int = RRF_K) -> float:
    """Reciprocal Rank Fusion score for a single ranked result."""
    return 1.0 / (k + rank)


async def fusion_node(state: ResearchState) -> dict:
    """
    LangGraph node: Fuse results from three retrieval sources.

    Input state:  pubmed_results, mesh_results, semantic_results
    Output state: fused_results (deduplicated, RRF-scored)
    """
    keyword_results = state.get("pubmed_results", [])
    mesh_results = state.get("mesh_results", [])
    semantic_results = state.get("semantic_results", [])

    print(f"\n  ┌──────────────────────────────────────")
    print(f"  │ [Node 5/9] 🧲 FUSION (Reciprocal Rank Fusion)")
    print(f"  │ Keyword={len(keyword_results)}, MeSH={len(mesh_results)}, Semantic={len(semantic_results)}")
    print(f"  ├──────────────────────────────────────")
    logger.info(
        "node_fusion",
        keyword=len(keyword_results),
        mesh=len(mesh_results),
        semantic=len(semantic_results),
    )

    # Accumulate RRF scores by PMID
    rrf_scores: dict[str, float] = {}
    paper_data: dict[str, dict] = {}  # best available paper data per PMID

    def add_results(results: list[dict], rank_field: str) -> None:
        for i, paper in enumerate(results):
            pmid = paper.get("pmid")
            if not pmid:
                continue
            rank = paper.get(rank_field, i + 1)
            rrf = _rrf_score(rank)
            rrf_scores[pmid] = rrf_scores.get(pmid, 0.0) + rrf

            # Keep the most data-rich version of the paper
            if pmid not in paper_data or len(paper.get("abstract", "") or "") > len(
                paper_data[pmid].get("abstract", "") or ""
            ):
                paper_data[pmid] = paper

    add_results(keyword_results, "keyword_rank")
    add_results(mesh_results, "mesh_rank")
    add_results(semantic_results, "semantic_rank")

    # Sort by RRF score descending
    sorted_pmids = sorted(rrf_scores.keys(), key=lambda p: rrf_scores[p], reverse=True)

    fused = []
    for pmid in sorted_pmids:
        paper = dict(paper_data[pmid])
        paper["rrf_score"] = round(rrf_scores[pmid], 6)

        # Track which sources contributed
        sources = []
        if any(p.get("pmid") == pmid for p in keyword_results):
            sources.append("keyword")
        if any(p.get("pmid") == pmid for p in mesh_results):
            sources.append("mesh")
        if any(p.get("pmid") == pmid for p in semantic_results):
            sources.append("semantic")
        paper["retrieval_sources"] = sources
        paper["source_count"] = len(sources)

        fused.append(paper)

    print(f"  │ ✅ Fused {len(fused)} unique articles. RRF scoring complete.")
    if fused:
        print(f"  │    Top PMIDs by RRF: {[f['pmid'] for f in fused[:5]]}")
        print(f"  │    Sources: {[f.get('retrieval_sources') for f in fused[:3]]}")
    print(f"  └──────────────────────────────────────")
    logger.info("fusion_complete", fused_count=len(fused))
    return {"fused_results": fused}
