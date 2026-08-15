"""
PubMedIQ — LangSmith Observability Integration

Configures LangSmith for tracing LangGraph pipeline executions.
Provides context managers and decorators for structured tracing.
"""
from __future__ import annotations

import functools
from typing import Any, Callable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_langsmith() -> None:
    """Configure LangSmith environment for the application."""
    if not settings.langsmith_enabled:
        logger.info("langsmith_disabled")
        return

    try:
        import os
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
        logger.info("langsmith_configured", project=settings.LANGCHAIN_PROJECT)
    except Exception as e:
        logger.warning("langsmith_setup_failed", error=str(e))


def trace(name: str | None = None, tags: list[str] | None = None) -> Callable:
    """
    Decorator to trace a function in LangSmith.

    Usage:
        @trace(name="my_function", tags=["search", "retrieval"])
        async def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.langsmith_enabled:
                return await func(*args, **kwargs)

            try:
                from langsmith import traceable
                traced = traceable(name=name or func.__name__, tags=tags or [])(func)
                return await traced(*args, **kwargs)
            except ImportError:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning("langsmith_trace_failed", error=str(e))
                return await func(*args, **kwargs)

        return wrapper
    return decorator


def get_langsmith_client():
    """Return a LangSmith client for dataset and evaluation operations."""
    if not settings.langsmith_enabled:
        return None
    try:
        from langsmith import Client
        return Client(api_key=settings.LANGCHAIN_API_KEY)
    except Exception:
        return None