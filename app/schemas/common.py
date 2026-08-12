"""
PubMedIQ — Pydantic Schemas: Common

Reusable response models shared across all API endpoints.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated wrapper for list responses."""
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_prev: bool = False


class HealthStatus(BaseModel):
    status: str           # "ok" | "degraded" | "unavailable"
    version: str
    dependencies: dict[str, bool] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    message: str


class SuccessResponse(BaseModel):
    success: bool = True
    message: str | None = None
