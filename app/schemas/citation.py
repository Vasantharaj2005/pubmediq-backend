"""
PubMedIQ — Pydantic Schemas: Citation
"""
from __future__ import annotations
from pydantic import BaseModel


class Citation(BaseModel):
    pmid: str
    title: str | None = None
    authors: str | None = None
    journal: str | None = None
    year: int | None = None
    doi: str | None = None
    pubmed_url: str | None = None


class CitationList(BaseModel):
    citations: list[Citation]
    count: int
