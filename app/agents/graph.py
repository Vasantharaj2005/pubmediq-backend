"""
PubMedIQ — LangGraph Research Pipeline

Wires all 11 nodes into a compiled StateGraph with:
  - Parallel retrieval (keyword + MeSH + semantic run concurrently)
  - Conditional routing at quality gate
  - Bounded refinement loop (max 2 iterations)

Graph topology:
  START
    └─► query_understanding
          └─► concept_mapping
                └─► query_planner
                      ├─► keyword_search ─┐
                      ├─► mesh_search    ─┤─► fusion ─► reranker ─► quality_gate
                      └─► semantic_search─┘                           │       │
                                                                  synthesize  refine
                                                                      │         │
                                                              answer_generator  └──► (loop back to keyword_search)
                                                                      │
                                                                     END
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.answer_generator import answer_generator_node
from app.agents.nodes.concept_mapping import concept_mapping_node
from app.agents.nodes.fusion import fusion_node
from app.agents.nodes.keyword_search import keyword_search_node
from app.agents.nodes.mesh_search import mesh_search_node
from app.agents.nodes.quality_gate import quality_gate_node, quality_gate_router
from app.agents.nodes.query_planner import query_planner_node
from app.agents.nodes.query_refinement import query_refinement_node
from app.agents.nodes.query_understanding import query_understanding_node
from app.agents.nodes.reranker import reranker_node
from app.agents.nodes.semantic_search import semantic_search_node
from app.agents.state import ResearchState
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_research_graph() -> StateGraph:
    """
    Construct the PubMedIQ LangGraph research pipeline.

    Returns a compiled StateGraph ready to invoke.
    """
    graph = StateGraph(ResearchState)

    # ----------------------------------------------------------------
    # Register nodes
    # ----------------------------------------------------------------
    graph.add_node("query_understanding", query_understanding_node)
    graph.add_node("concept_mapping", concept_mapping_node)
    graph.add_node("query_planner", query_planner_node)
    graph.add_node("keyword_search", keyword_search_node)
    graph.add_node("mesh_search", mesh_search_node)
    graph.add_node("semantic_search", semantic_search_node)
    graph.add_node("fusion", fusion_node)
    graph.add_node("reranker", reranker_node)
    graph.add_node("quality_gate", quality_gate_node)
    graph.add_node("query_refinement", query_refinement_node)
    graph.add_node("answer_generator", answer_generator_node)

    # ----------------------------------------------------------------
    # Sequential pipeline: Understanding → Mapping → Planning
    # ----------------------------------------------------------------
    graph.add_edge(START, "query_understanding")
    graph.add_edge("query_understanding", "concept_mapping")
    graph.add_edge("concept_mapping", "query_planner")

    # ----------------------------------------------------------------
    # Parallel retrieval: all three search nodes run after query_planner
    # LangGraph executes nodes with multiple incoming/outgoing edges in parallel
    # ----------------------------------------------------------------
    graph.add_edge("query_planner", "keyword_search")
    graph.add_edge("query_planner", "mesh_search")
    graph.add_edge("query_planner", "semantic_search")

    # ----------------------------------------------------------------
    # Convergence: all three retrieval nodes feed into fusion
    # ----------------------------------------------------------------
    graph.add_edge("keyword_search", "fusion")
    graph.add_edge("mesh_search", "fusion")
    graph.add_edge("semantic_search", "fusion")

    # ----------------------------------------------------------------
    # Ranking pipeline
    # ----------------------------------------------------------------
    graph.add_edge("fusion", "reranker")
    graph.add_edge("reranker", "quality_gate")

    # ----------------------------------------------------------------
    # Quality gate conditional routing
    # ----------------------------------------------------------------
    graph.add_conditional_edges(
        "quality_gate",
        quality_gate_router,
        {
            "synthesize": "answer_generator",
            "refine": "query_refinement",
        },
    )

    # ----------------------------------------------------------------
    # Refinement loop: after refinement, re-run retrieval
    # ----------------------------------------------------------------
    graph.add_edge("query_refinement", "keyword_search")

    # ----------------------------------------------------------------
    # Terminal node
    # ----------------------------------------------------------------
    graph.add_edge("answer_generator", END)

    logger.info("research_graph_built")
    return graph


@lru_cache(maxsize=1)
def get_compiled_graph():
    """
    Return a compiled (cached) LangGraph instance.

    The graph is compiled once and reused across requests for performance.
    """
    graph = build_research_graph()
    compiled = graph.compile()
    logger.info("research_graph_compiled")
    return compiled
