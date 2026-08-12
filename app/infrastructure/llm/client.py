"""
PubMedIQ — LLM Client

Thin wrapper around the ModelRouter providing a clean interface
for agent nodes. Adds structured output support via Pydantic.
"""
from __future__ import annotations

from typing import Any, Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.core.logging import get_logger
from app.infrastructure.llm.model_router import ModelRouter, ModelTask, get_model_router

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Convenience wrapper for LangChain models.

    Usage in agent nodes:
        client = LLMClient()
        result = await client.invoke_structured(
            system="You are a biomedical researcher...",
            human="Extract intent from: {query}",
            schema=ResearchIntent,
        )
    """

    def __init__(self, router: ModelRouter | None = None) -> None:
        self._router = router or get_model_router()

    async def invoke(
        self,
        system: str,
        human: str,
        task: ModelTask = ModelTask.FAST,
    ) -> str:
        """
        Simple text-in, text-out invocation.

        Args:
            system: System prompt.
            human: Human message.
            task: Model task type for provider selection.

        Returns:
            Model response as a string.
        """
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=human),
        ]
        return await self._router.ainvoke(messages, task=task)

    async def invoke_structured(
        self,
        system: str,
        human: str,
        schema: Type[T],
        task: ModelTask = ModelTask.STRUCTURED,
    ) -> T:
        """
        Structured output invocation — returns a Pydantic model instance.

        Uses LangChain's with_structured_output where supported.
        Falls back to JSON parsing if not supported.

        Args:
            system: System prompt.
            human: Human message.
            schema: Pydantic BaseModel class.
            task: Model task type.

        Returns:
            Parsed Pydantic model instance.
        """
        model = self._router.get_model(task)

        try:
            structured_model = model.with_structured_output(schema)
            messages = [
                SystemMessage(content=system),
                HumanMessage(content=human),
            ]
            result = await structured_model.ainvoke(messages)
            return result
        except NotImplementedError:
            # Fallback: ask for JSON and parse manually
            logger.debug("structured_output_fallback", schema=schema.__name__)
            json_prompt = (
                f"{human}\n\nRespond with valid JSON matching this schema: "
                f"{schema.model_json_schema()}"
            )
            messages = [
                SystemMessage(content=system),
                HumanMessage(content=json_prompt),
            ]
            raw = await self._router.ainvoke(messages, task=task)
            return _parse_json_to_schema(raw, schema)
        except Exception as e:
            logger.error("structured_invoke_failed", error=str(e), schema=schema.__name__)
            raise


def _parse_json_to_schema(raw: str, schema: Type[T]) -> T:
    """Extract JSON from LLM response and parse into Pydantic schema."""
    import json
    import re

    # Extract JSON block if wrapped in markdown code fences
    json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if json_match:
        raw = json_match.group(1)

    try:
        data = json.loads(raw.strip())
        return schema.model_validate(data)
    except Exception as e:
        logger.error("json_parse_failed", error=str(e), raw=raw[:200])
        # Return a default-initialized model as last resort
        return schema.model_construct()


# Module-level singleton
llm_client = LLMClient()
