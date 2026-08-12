"""
PubMedIQ — History Service
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import HistoryNotFoundError, PermissionDeniedError
from app.infrastructure.database.repositories.history_repository import HistoryRepository


class HistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = HistoryRepository(db)

    async def get_history(self, user_id: str, limit: int = 50) -> list:
        return await self._repo.get_by_user(user_id, limit=limit)

    async def delete(self, user_id: str, record_id: str) -> None:
        deleted = await self._repo.delete(record_id, user_id)
        if not deleted:
            raise HistoryNotFoundError()
