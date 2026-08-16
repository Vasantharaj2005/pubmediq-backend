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
        record_id: str | uuid.UUID | None = None,  # use session_id as PK when provided
        intent: dict | None = None,
        search_strategy: dict | None = None,
        results_count: int = 0,
        quality_score: float | None = None,
        refined: bool = False,
        refinement_count: int = 0,
        results: list | None = None,
        ai_summary: str | None = None,
        citations: list | None = None,
    ) -> SearchHistoryModel:
        """Persist a search history record with optional full result payload.

        Args:
            record_id:  Use the search session_id as the PK so the refine
                        endpoint can look it up directly. Falls back to uuid4.
            results:    Full list of serialised PaperResult dicts.
            ai_summary: LLM-generated evidence synthesis text.
            citations:  List of cited PMID strings.
        """
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        rid = (
            uuid.UUID(str(record_id)) if isinstance(record_id, str) else record_id
        ) if record_id else uuid.uuid4()
        record = SearchHistoryModel(
            id=rid,
            user_id=uid,
            query=query,
            intent=intent,
            search_strategy=search_strategy,
            results_count=results_count,
            quality_score=quality_score,
            refined=refined,
            refinement_count=refinement_count,
            results=results,
            ai_summary=ai_summary,
            citations=citations,
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
        """Fetch a single history record by ID (no user ownership check)."""
        rid = uuid.UUID(str(record_id)) if isinstance(record_id, str) else record_id
        result = await self._db.execute(
            select(SearchHistoryModel).where(SearchHistoryModel.id == rid)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self,
        record_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> SearchHistoryModel | None:
        """Fetch a history record only if it belongs to the given user (secure lookup)."""
        rid = uuid.UUID(str(record_id)) if isinstance(record_id, str) else record_id
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            select(SearchHistoryModel)
            .where(SearchHistoryModel.id == rid)
            .where(SearchHistoryModel.user_id == uid)
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
