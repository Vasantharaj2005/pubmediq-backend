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
    print(f"\n  ┌──────────────────────────────────────")
    print(f"  │ [Node 1/9] 🧠 QUERY UNDERSTANDING")
    print(f"  │ Input query: '{query[:80]}'")
    print(f"  ├──────────────────────────────────────")
    print(f"  │ Sending query to LLM for PICO intent extraction...")
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
        filled = {k: v for k, v in intent.items() if v is not None}
        print(f"  │ ✅ LLM extracted intent successfully.")
        for k, v in filled.items():
            print(f"  │    {k}: {v}")
        print(f"  └──────────────────────────────────────")
        logger.info("query_understanding_complete", intent_keys=list(intent.keys()))
        return {"intent": intent}

    except json.JSONDecodeError as e:
        print(f"  │ ⚠️  JSON parse failed: {e}. Using fallback intent.")
        print(f"  └──────────────────────────────────────")
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
        print(f"  │ ❌ LLM call FAILED: {e}")
        print(f"  └──────────────────────────────────────")
        logger.error("query_understanding_failed", error=str(e))
        return {
            "intent": {"condition": query},
            "errors": state.get("errors", []) + [f"query_understanding: {e}"],
        }
