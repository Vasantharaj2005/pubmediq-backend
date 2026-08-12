"""
PubMedIQ — Feedback Service
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback import FeedbackRequest, FeedbackResponse


class FeedbackService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = FeedbackRepository(db)

    async def submit(self, request: FeedbackRequest, user_id: str | None = None) -> FeedbackResponse:
        record = await self._repo.create(
            rating=request.rating,
            user_id=user_id,
            session_id=request.session_id,
            comment=request.comment,
            query=request.query,
        )
        return FeedbackResponse.model_validate(record)
