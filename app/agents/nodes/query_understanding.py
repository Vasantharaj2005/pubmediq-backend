"""
PubMedIQ — Agent Node: Query Understanding (LLM)

Extracts structured ResearchIntent from the natural language query.
Uses LLM with structured output.
"""
from __future__ import annotations

import json

from app.agents.prompts.query_understanding import build_intent_prompt
from app.agents.state import ResearchState
from app.core.logging import get_logger
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.model_router import ModelTask

logger = get_logger(__name__)


async def query_understanding_node(state: ResearchState) -> dict:
    """
    LangGraph node: Extract structured research intent from query.

    Input state:  query
    Output state: intent
    """
    query = state.get("query", "")
    logger.info("node_query_understanding", query=query[:80])

    system, human = build_intent_prompt(query)
    client = LLMClient()

    try:
        raw = await client.invoke(system=system, human=human, task=ModelTask.FAST)

        # Parse JSON response
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        intent = json.loads(raw)
        logger.info("query_understanding_complete", intent_keys=list(intent.keys()))
        return {"intent": intent}

    except json.JSONDecodeError as e:
        logger.warning("query_understanding_json_failed", error=str(e))
        # Graceful fallback: minimal intent from the query
        return {
            "intent": {
                "population": None,
                "intervention": None,
                "condition": query,
                "outcome": None,
                "study_type": None,
                "timeframe": None,
            }
        }
    except Exception as e:
        logger.error("query_understanding_failed", error=str(e))
        return {
            "intent": {"condition": query},
            "errors": state.get("errors", []) + [f"query_understanding: {e}"],
        }
