"""
PubMedIQ — Pydantic Schemas: Feedback
"""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating from 1 (worst) to 5 (best)")
    comment: str | None = Field(None, max_length=2000)
    session_id: str | None = None
    query: str | None = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    rating: int
    created_at: datetime
    message: str = "Thank you for your feedback!"

    model_config = {"from_attributes": True}
