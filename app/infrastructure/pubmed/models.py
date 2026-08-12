"""
PubMedIQ — PubMed Infrastructure Models

Pydantic data models representing PubMed article data.
These are infrastructure-layer models (not domain models).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PubMedAuthor(BaseModel):
    """Author record from PubMed."""
    last_name: str | None = None
    fore_name: str | None = None
    affiliation: str | None = None

    @property
    def full_name(self) -> str:
        parts = [self.fore_name, self.last_name]
        return " ".join(p for p in parts if p)


class PubMedArticle(BaseModel):
    """
    Structured representation of a PubMed article fetched via E-Utils.
    All fields are optional because not all articles have complete metadata.
    """
    pmid: str
    title: str | None = None
    abstract: str | None = None
    authors: list[PubMedAuthor] = Field(default_factory=list)
    journal: str | None = None
    journal_abbr: str | None = None
    year: int | None = None
    pub_date: str | None = None
    pub_types: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    doi: str | None = None
    pmc_id: str | None = None
    issn: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    language: str | None = None

    @property
    def author_string(self) -> str:
        """First author + et al. for display."""
        if not self.authors:
            return "Unknown"
        first = self.authors[0].full_name
        if len(self.authors) > 1:
            return f"{first} et al."
        return first

    @property
    def full_text_for_embedding(self) -> str:
        """Concatenated title + abstract for embedding generation."""
        parts = []
        if self.title:
            parts.append(self.title)
        if self.abstract:
            parts.append(self.abstract)
        return " ".join(parts)

    @property
    def pubmed_url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
