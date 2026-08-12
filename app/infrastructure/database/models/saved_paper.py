"""
PubMedIQ — Saved Paper ORM Model
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class SavedPaperModel(Base):
    """
    PostgreSQL table: saved_papers

    Tracks which PubMed articles a user has bookmarked.
    PMID is the canonical PubMed identifier.
    """

    __tablename__ = "saved_papers"
    __table_args__ = (
        # A user can only save a given paper once
        UniqueConstraint("user_id", "pmid", name="uq_saved_paper_user_pmid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pmid: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    journal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SavedPaperModel user_id={self.user_id} pmid={self.pmid}>"
