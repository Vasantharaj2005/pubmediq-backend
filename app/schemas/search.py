"""
PubMedIQ — Pydantic Schemas: Search

Request/response contracts for the search pipeline.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import SearchMode, StudyType


class SearchFilters(BaseModel):
    year_from: int | None = Field(None, ge=1800, le=2030)
    year_to: int | None = Field(None, ge=1800, le=2030)
    study_type: StudyType | None = None
    journal: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    filters: SearchFilters | None = None
    top_k: int = Field(default=20, ge=1, le=100)
    mode: SearchMode = SearchMode.HYBRID
    session_id: str | None = None  # for follow-up chat context


class SearchIntent(BaseModel):
    population: str | None = None
    intervention: str | None = None
    condition: str | None = None
    outcome: str | None = None
    study_type: str | None = None
    timeframe: str | None = None


class SearchStrategy(BaseModel):
    keyword_query: str | None = None
    mesh_query: str | None = None
    semantic_search: bool = True
    mesh_terms: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)


class SearchQuality(BaseModel):
    score: float
    level: str              # "high" | "medium" | "low"
    refined: bool = False
    refinement_count: int = 0


class PaperResult(BaseModel):
    pmid: str
    title: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    score: float = 0.0
    semantic_score: float | None = None
    keyword_score: float | None = None
    mesh_score: float | None = None
    pub_types: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    pubmed_url: str | None = None


class SearchResponse(BaseModel):
    session_id: str
    query: str
    intent: SearchIntent | None = None
    results: list[PaperResult] = Field(default_factory=list)
    total_results: int = 0
    search_strategy: SearchStrategy | None = None
    quality: SearchQuality | None = None
    ai_summary: str | None = None
    citations: list[str] = Field(default_factory=list)
    cached: bool = False


class RefineRequest(BaseModel):
    session_id: str
    feedback: str | None = None  # user hint for refinement
