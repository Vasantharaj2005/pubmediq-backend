"""
PubMedIQ - History Service
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import HistoryNotFoundError, PermissionDeniedError
from app.infrastructure.database.repositories.history_repository import HistoryRepository


class HistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = HistoryRepository(db)

    async def get_history(self, user_id: str, limit: int = 50) -> list:
        """Return list of history records for the user (summary rows)."""
        return await self._repo.get_by_user(user_id, limit=limit)

    async def get_by_id(self, user_id: str, record_id: str):
        """Return a single history record including full results, verified to the user."""
        record = await self._repo.get_by_id(record_id)
        if not record:
            raise HistoryNotFoundError()
        if str(record.user_id) != user_id:
            raise PermissionDeniedError()
        return record

    async def delete(self, user_id: str, record_id: str) -> None:
        deleted = await self._repo.delete(record_id, user_id)
        if not deleted:
            raise HistoryNotFoundError()
