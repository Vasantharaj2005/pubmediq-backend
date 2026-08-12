"""History endpoint re-export"""
from app.api.v1.endpoints.users import history_router as router

__all__ = ["router"]
