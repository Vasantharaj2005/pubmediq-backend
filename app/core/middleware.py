"""
PubMedIQ — ASGI Middleware

RequestLoggingMiddleware  — logs every HTTP request with method, path, status, and latency.
CorrelationIDMiddleware   — attaches X-Request-ID to every request/response.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Attaches a unique X-Request-ID header to every request.
    If the client sends one, it is preserved; otherwise a new UUID4 is generated.
    The ID is available via structlog context for the lifetime of the request.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context so all log lines include request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request state for use in endpoints
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            logger.error("unhandled_exception_in_middleware", path=request.url.path, exc_info=True)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred.",
                    }
                },
                headers={"X-Request-ID": request_id},
            )
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request:
      - method, path, status code, latency (ms)
      - skips /health endpoints to avoid log noise
    """

    SKIP_PATHS = {"/health", "/health/ready", "/health/live"}

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
        )

        if response.status_code >= 500:
            log.error("request_error")
        elif response.status_code >= 400:
            log.warning("request_client_error")
        else:
            log.info("request_completed")

        return response
