"""
PubMedIQ — Feedback Repository
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.feedback import FeedbackModel


class FeedbackRepository:
    """Repository for the feedback table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        rating: int,
        user_id: str | uuid.UUID | None = None,
        session_id: str | None = None,
        comment: str | None = None,
        query: str | None = None,
    ) -> FeedbackModel:
        """Persist a feedback record."""
        uid = None
        if user_id is not None:
            uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id

        record = FeedbackModel(
            id=uuid.uuid4(),
            user_id=uid,
            session_id=session_id,
            rating=rating,
            comment=comment,
            query=query,
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return record

    async def get_by_session(self, session_id: str) -> list[FeedbackModel]:
        """Retrieve all feedback records for a search session."""
        result = await self._db.execute(
            select(FeedbackModel)
            .where(FeedbackModel.session_id == session_id)
            .order_by(FeedbackModel.created_at.desc())
        )
        return list(result.scalars().all())
