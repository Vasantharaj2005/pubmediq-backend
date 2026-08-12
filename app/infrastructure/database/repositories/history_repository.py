"""
PubMedIQ — History Repository
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.search_history import SearchHistoryModel


class HistoryRepository:
    """Repository for search_history table operations."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        user_id: str | uuid.UUID,
        query: str,
        intent: dict | None = None,
        search_strategy: dict | None = None,
        results_count: int = 0,
        quality_score: float | None = None,
        refined: bool = False,
        refinement_count: int = 0,
    ) -> SearchHistoryModel:
        """Persist a search history record."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        record = SearchHistoryModel(
            id=uuid.uuid4(),
            user_id=uid,
            query=query,
            intent=intent,
            search_strategy=search_strategy,
            results_count=results_count,
            quality_score=quality_score,
            refined=refined,
            refinement_count=refinement_count,
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return record

    async def get_by_user(
        self,
        user_id: str | uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SearchHistoryModel]:
        """Return search history for a user, newest first."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            select(SearchHistoryModel)
            .where(SearchHistoryModel.user_id == uid)
            .order_by(SearchHistoryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, record_id: str | uuid.UUID
    ) -> SearchHistoryModel | None:
        """Fetch a single history record by ID."""
        rid = uuid.UUID(str(record_id)) if isinstance(record_id, str) else record_id
        result = await self._db.execute(
            select(SearchHistoryModel).where(SearchHistoryModel.id == rid)
        )
        return result.scalar_one_or_none()

    async def delete(
        self,
        record_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> bool:
        """Delete a history record if it belongs to the given user."""
        rid = uuid.UUID(str(record_id)) if isinstance(record_id, str) else record_id
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            delete(SearchHistoryModel)
            .where(SearchHistoryModel.id == rid)
            .where(SearchHistoryModel.user_id == uid)
        )
        return result.rowcount > 0
