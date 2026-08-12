"""
PubMedIQ — Database Models Package

Import all ORM models here so Alembic can discover them for autogenerate.
"""
from app.infrastructure.database.models.feedback import FeedbackModel
from app.infrastructure.database.models.saved_paper import SavedPaperModel
from app.infrastructure.database.models.search_history import SearchHistoryModel
from app.infrastructure.database.models.user import UserModel

__all__ = [
    "UserModel",
    "SearchHistoryModel",
    "SavedPaperModel",
    "FeedbackModel",
]
