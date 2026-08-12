"""
PubMedIQ — FastAPI Application Entry Point

Creates and configures the FastAPI application with:
  - Lifespan: DB pool, Redis, Pinecone, LangSmith initialization
  - CORS middleware
  - Request logging + correlation ID middleware
  - Global exception handlers
  - API router registration
  - Swagger UI customization
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import PubMedIQError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIDMiddleware, RequestLoggingMiddleware

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Runs startup code before yielding and shutdown code after.
    """
    logger.info("pubmediq_starting", env=settings.APP_ENV, version=settings.APP_VERSION)

    # 1. Configure structured logging
    configure_logging()

    # 2. Connect Redis
    from app.infrastructure.cache.redis_client import redis_client
    await redis_client.connect()

    # 3. Configure token blacklist with Redis
    from app.infrastructure.security.token_blacklist import configure_blacklist
    configure_blacklist(redis_client.raw)

    # 4. Connect Pinecone
    from app.infrastructure.vectorstore.pinecone_client import pinecone_client
    pinecone_client.connect()

    # 5. Configure LangSmith (if enabled)
    if settings.langsmith_enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
        logger.info("langsmith_enabled", project=settings.LANGCHAIN_PROJECT)

    # 6. Pre-warm LangGraph graph (compile once at startup)
    try:
        from app.agents.graph import get_compiled_graph
        get_compiled_graph()
        logger.info("langgraph_compiled")
    except Exception as e:
        logger.warning("langgraph_compile_failed", error=str(e))

    logger.info("pubmediq_ready")

    yield  # Application is running

    # Shutdown
    logger.info("pubmediq_shutting_down")
    await redis_client.disconnect()
    logger.info("pubmediq_stopped")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="PubMedIQ API",
        description=(
            "**PubMedIQ** — AI-powered semantic research assistant on top of PubMed.\n\n"
            "## Features\n"
            "- 🔍 **Hybrid Search**: Keyword + MeSH + Semantic retrieval\n"
            "- 🧠 **LangGraph Pipeline**: Multi-step AI reasoning\n"
            "- 📚 **Evidence-grounded Answers**: All claims cited with PMID\n"
            "- 🔄 **Query Refinement**: Automatic refinement when results are poor\n"
            "- 🔐 **JWT Authentication**: Secure user accounts\n"
            "- ⚡ **Redis Caching**: Fast repeated queries\n\n"
            "## LLM Providers\n"
            "Groq (default, free) → Google Gemini → OpenAI (fallback)\n\n"
            "## Embedding Model\n"
            "`pritamdeka/S-PubMedBert-MS-MARCO` — biomedical-specific (free, local)\n\n"
            "## Reranker\n"
            "`cross-encoder/ms-marco-MiniLM-L-6-v2` — local cross-encoder (free)"
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ----- CORS -----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ----- Custom middleware (order matters — last added = first executed) -----
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    # ----- Exception handlers -----
    @app.exception_handler(PubMedIQError)
    async def pubmediq_exception_handler(request: Request, exc: PubMedIQError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                }
            },
        )

    # ----- Routers -----
    app.include_router(api_router)

    return app


# ---------------------------------------------------------------------------
# Application instance (used by uvicorn: app.main:app)
# ---------------------------------------------------------------------------
app = create_app()
