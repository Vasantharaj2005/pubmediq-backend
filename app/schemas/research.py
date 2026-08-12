"""
PubMedIQ — Pydantic Schemas: Research (Summarize, Compare, Ask)
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    pmids: list[str] = Field(min_length=1, max_length=10)
    focus: str | None = None  # e.g., "methodology" or "outcomes"


class CompareRequest(BaseModel):
    pmids: list[str] = Field(min_length=2, max_length=5)
    aspect: str | None = None  # e.g., "sample size" or "intervention"


class GapAnalysisRequest(BaseModel):
    pmids: list[str] = Field(min_length=3, max_length=20)
    topic: str | None = None


class AskRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=3, max_length=1000)


class ResearchResponse(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    pmids_used: list[str] = Field(default_factory=list)
    confidence: float | None = None
