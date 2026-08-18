from __future__ import annotations

from typing import Any
from langchain_core.callbacks.base import AsyncCallbackHandler
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_graph_run_config(
    session_id: str,
    user_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Constructs a LangChain/LangGraph runnable config dictionary.
    Pass this into `graph.ainvoke(state, config=get_graph_run_config(...))`.
    """
    run_tags = ["pubmediq", settings.APP_ENV]
    if tags:
        run_tags.extend(tags)

    run_metadata: dict[str, Any] = {
        "session_id": session_id,
        "user_id": user_id or "anonymous",
        "app_version": settings.APP_VERSION,
        "llm_provider": settings.DEFAULT_LLM_PROVIDER,
    }
    if metadata:
        run_metadata.update(metadata)

    return {
        "run_name": f"PubMedIQ_Research_{session_id[:8]}",
        "tags": run_tags,
        "metadata": run_metadata,
    }


class PipelineTracingCallback(AsyncCallbackHandler):
    """Custom callback handler to capture node execution metrics."""

    async def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        pass

    async def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        pass

    async def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.error("pipeline_chain_error", error=str(error))
