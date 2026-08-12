"""
PubMedIQ — API v1 Router

Registers all v1 endpoint routers.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.papers import router as papers_router
from app.api.v1.endpoints.research import router as research_router
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.users import (
    feedback_router,
    history_router,
    users_router,
)

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(search_router)
v1_router.include_router(papers_router)
v1_router.include_router(research_router)
v1_router.include_router(history_router)
v1_router.include_router(feedback_router)
v1_router.include_router(users_router)
