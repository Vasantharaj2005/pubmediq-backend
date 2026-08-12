"""
PubMedIQ — Pydantic Schemas: Paper
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class PaperDetail(BaseModel):
    pmid: str
    title: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    journal_abbr: str | None = None
    year: int | None = None
    pub_types: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    doi: str | None = None
    pubmed_url: str | None = None
    is_saved: bool = False


class PaperSummary(BaseModel):
    pmid: str
    title: str | None = None
    journal: str | None = None
    year: int | None = None
    pubmed_url: str | None = None

    model_config = {"from_attributes": True}


class SavePaperResponse(BaseModel):
    pmid: str
    saved: bool
    message: str
