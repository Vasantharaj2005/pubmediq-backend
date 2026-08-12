"""
PubMedIQ — Structured Logging Configuration

Sets up structlog for JSON-formatted, context-aware logging.
Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("search_started", query="...", user_id="...")
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure structlog + stdlib logging for the application.
    - Development: pretty console output with colors
    - Production: JSON output for log aggregators (CloudWatch, Datadog, etc.)
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Configure stdlib logging (used by uvicorn, sqlalchemy, httpx, etc.)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Suppress noisy loggers in development
    for noisy in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Keep SQLAlchemy at WARNING unless debug
    if not settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,      # requires stdlib LoggerFactory (see below)
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_development:
        # Pretty output for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # JSON output for production / cloud log ingestion
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        # IMPORTANT: use stdlib LoggerFactory so that add_logger_name can
        # access logger.name — PrintLogger does NOT have a .name attribute.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structlog logger.

    Calling configure_logging() first is recommended, but this function
    applies a minimal default config if it has never been called so that
    scripts and tests always work without an explicit bootstrap step.

    Usage:
        logger = get_logger(__name__)
        logger.info("event", key="value")
    """
    # Apply a safe default configuration if structlog has never been configured.
    # This prevents the 'PrintLogger has no attribute name' crash when scripts
    # call get_logger() before configure_logging() has been invoked.
    if not structlog.is_configured():
        configure_logging()

    return structlog.get_logger(name)
