"""
PubMedIQ — remaining endpoint stubs (history, feedback)
These are already in users.py — re-export routers here.
"""
from app.api.v1.endpoints.users import feedback_router as router

__all__ = ["router"]
