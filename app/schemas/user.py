"""
PubMedIQ — Pydantic Schemas: User Profile
"""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)


class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}
