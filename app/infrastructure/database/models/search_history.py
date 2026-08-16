"""
PubMedIQ - Search History ORM Model
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class SearchHistoryModel(Base):
    """
    PostgreSQL table: search_history

    Records every search a user performs, including the extracted intent,
    result count, quality metrics, the full paper list, and AI summary.
    """

    __tablename__ = "search_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(String(2000), nullable=False)
    intent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_strategy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    refined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refinement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Full result payload stored so history can replay complete search results
    results: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SearchHistoryModel id={self.id} query={self.query[:30]!r}>"
