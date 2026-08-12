"""
PubMedIQ — Saved Paper Repository
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.saved_paper import SavedPaperModel


class PaperRepository:
    """Repository for saved_papers table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(
        self,
        user_id: str | uuid.UUID,
        pmid: str,
        title: str | None = None,
        journal: str | None = None,
        year: int | None = None,
    ) -> SavedPaperModel:
        """Bookmark a PubMed article for a user."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        paper = SavedPaperModel(
            id=uuid.uuid4(),
            user_id=uid,
            pmid=pmid,
            title=title,
            journal=journal,
            year=year,
        )
        self._db.add(paper)
        await self._db.flush()
        await self._db.refresh(paper)
        return paper

    async def unsave(
        self, user_id: str | uuid.UUID, pmid: str
    ) -> bool:
        """Remove a bookmarked paper. Returns True if deleted."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            delete(SavedPaperModel)
            .where(SavedPaperModel.user_id == uid)
            .where(SavedPaperModel.pmid == pmid)
        )
        return result.rowcount > 0

    async def is_saved(
        self, user_id: str | uuid.UUID, pmid: str
    ) -> bool:
        """Check whether a user has bookmarked a given paper."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            select(SavedPaperModel)
            .where(SavedPaperModel.user_id == uid)
            .where(SavedPaperModel.pmid == pmid)
        )
        return result.scalar_one_or_none() is not None

    async def get_saved_by_user(
        self,
        user_id: str | uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SavedPaperModel]:
        """Return all papers saved by a user, newest first."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            select(SavedPaperModel)
            .where(SavedPaperModel.user_id == uid)
            .order_by(SavedPaperModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
