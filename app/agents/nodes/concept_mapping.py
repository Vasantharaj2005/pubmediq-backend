"""
PubMedIQ — Agent Node: Concept Mapping (LLM)

Expands research intent into biomedical concepts, synonyms, and MeSH terms.
"""
from __future__ import annotations

import json

from app.agents.prompts.concept_mapping import build_concept_prompt
from app.agents.state import ResearchState
from app.core.logging import get_logger
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.model_router import ModelTask

logger = get_logger(__name__)


async def concept_mapping_node(state: ResearchState) -> dict:
    """
    LangGraph node: Expand intent into concepts, synonyms, MeSH terms.

    Input state:  intent
    Output state: facets, mesh_terms
    """
    intent = state.get("intent", {})
    query = state.get("query", "")
    logger.info("node_concept_mapping", intent=str(intent)[:100])

    system, human = build_concept_prompt(intent)
    client = LLMClient()

    try:
        raw = await client.invoke(system=system, human=human, task=ModelTask.FAST)

        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        data = json.loads(raw)
        facets = data.get("facets", {})
        mesh_terms = data.get("mesh_terms", [])

        logger.info(
            "concept_mapping_complete",
            facets_count=len(facets),
            mesh_terms=len(mesh_terms),
        )
        return {
            "facets": facets,
            "mesh_terms": mesh_terms,
        }

    except json.JSONDecodeError as e:
        logger.warning("concept_mapping_json_failed", error=str(e))
        # Fallback: use query words as concepts
        words = [w for w in query.split() if len(w) > 3]
        return {
            "facets": {"query": words[:5]},
            "mesh_terms": [],
        }
    except Exception as e:
        logger.error("concept_mapping_failed", error=str(e))
        return {
            "facets": {},
            "mesh_terms": [],
            "errors": state.get("errors", []) + [f"concept_mapping: {e}"],
        }
