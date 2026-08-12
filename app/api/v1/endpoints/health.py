"""
PubMedIQ — Health Endpoints

GET /health        → basic liveness (always 200 if server is up)
GET /health/ready  → readiness (checks all dependencies)
GET /health/live   → Kubernetes liveness probe
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.database.connection import check_database_connection
from app.infrastructure.vectorstore.pinecone_client import pinecone_client
from app.schemas.common import HealthStatus

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthStatus, summary="Basic health check")
async def health() -> HealthStatus:
    """Returns 200 if the API server is running."""
    return HealthStatus(
        status="ok",
        version=settings.APP_VERSION,
    )


@router.get("/ready", response_model=HealthStatus, summary="Readiness check")
async def readiness() -> HealthStatus:
    """
    Checks all external dependencies.
    Returns 200 with status='ok' if all are healthy,
    or 200 with status='degraded' if some are unavailable.
    """
    db_ok = await check_database_connection()
    redis_ok = await redis_client.ping()
    pinecone_ok = await pinecone_client.ping()

    dependencies = {
        "database": db_ok,
        "redis": redis_ok,
        "pinecone": pinecone_ok,
    }

    all_ok = db_ok  # DB is required; others can degrade gracefully
    status = "ok" if all_ok else "degraded"

    return HealthStatus(
        status=status,
        version=settings.APP_VERSION,
        dependencies=dependencies,
    )


@router.get("/live", summary="Kubernetes liveness probe")
async def liveness() -> dict:
    """Minimal liveness check for container orchestration."""
    return {"status": "alive"}
