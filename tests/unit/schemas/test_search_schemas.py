"""
Tests for app.schemas.search

Verifies Pydantic validation for search-related schemas.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.enums import SearchMode, StudyType
from app.schemas.search import (
    PaperResult,
    RefineRequest,
    SearchFilters,
    SearchIntent,
    SearchQuality,
    SearchRequest,
    SearchResponse,
    SearchStrategy,
)


class TestSearchRequest:
    def test_valid_request(self):
        req = SearchRequest(query="effect of exercise on depression")
        assert req.query == "effect of exercise on depression"
        assert req.top_k == 20  # default
        assert req.mode == SearchMode.HYBRID

    def test_query_min_length(self):
        """Query must be at least 3 characters."""
        with pytest.raises(ValidationError):
            SearchRequest(query="ab")

    def test_query_exactly_3_chars(self):
        req = SearchRequest(query="abc")
        assert req.query == "abc"

    def test_query_max_length(self):
        req = SearchRequest(query="a" * 1000)
        assert len(req.query) == 1000

        with pytest.raises(ValidationError):
            SearchRequest(query="a" * 1001)

    def test_top_k_range(self):
        req = SearchRequest(query="test query", top_k=1)
        assert req.top_k == 1

        req = SearchRequest(query="test query", top_k=100)
        assert req.top_k == 100

        with pytest.raises(ValidationError):
            SearchRequest(query="test query", top_k=0)

        with pytest.raises(ValidationError):
            SearchRequest(query="test query", top_k=101)

    def test_search_mode_options(self):
        for mode in SearchMode:
            req = SearchRequest(query="test query", mode=mode)
            assert req.mode == mode

    def test_optional_session_id(self):
        req = SearchRequest(query="test query")
        assert req.session_id is None

        req = SearchRequest(query="test query", session_id="sess-123")
        assert req.session_id == "sess-123"

    def test_optional_filters(self):
        req = SearchRequest(query="test query")
        assert req.filters is None


class TestSearchFilters:
    def test_all_none_by_default(self):
        f = SearchFilters()
        assert f.year_from is None
        assert f.year_to is None
        assert f.study_type is None
        assert f.journal is None

    def test_year_boundaries(self):
        f = SearchFilters(year_from=1800, year_to=2030)
        assert f.year_from == 1800
        assert f.year_to == 2030

    def test_year_below_minimum(self):
        with pytest.raises(ValidationError):
            SearchFilters(year_from=1799)

    def test_year_above_maximum(self):
        with pytest.raises(ValidationError):
            SearchFilters(year_to=2031)

    def test_study_type_enum(self):
        f = SearchFilters(study_type=StudyType.SYSTEMATIC_REVIEW)
        assert f.study_type == StudyType.SYSTEMATIC_REVIEW

    def test_journal_filter(self):
        f = SearchFilters(journal="Nature Medicine")
        assert f.journal == "Nature Medicine"


class TestSearchIntent:
    def test_all_optional(self):
        intent = SearchIntent()
        assert intent.population is None
        assert intent.intervention is None

    def test_partial_fill(self):
        intent = SearchIntent(population="elderly", intervention="exercise")
        assert intent.population == "elderly"
        assert intent.intervention == "exercise"
        assert intent.condition is None


class TestSearchStrategy:
    def test_defaults(self):
        strategy = SearchStrategy()
        assert strategy.semantic_search is True
        assert strategy.mesh_terms == []
        assert strategy.concepts == []


class TestSearchQuality:
    def test_basic(self):
        q = SearchQuality(score=0.85, level="high")
        assert q.score == 0.85
        assert q.level == "high"
        assert q.refined is False
        assert q.refinement_count == 0

    def test_refined(self):
        q = SearchQuality(score=0.70, level="medium", refined=True, refinement_count=1)
        assert q.refined is True
        assert q.refinement_count == 1


class TestPaperResult:
    def test_minimal(self):
        paper = PaperResult(pmid="12345678")
        assert paper.pmid == "12345678"
        assert paper.title is None
        assert paper.authors == []
        assert paper.score == 0.0

    def test_full(self):
        paper = PaperResult(
            pmid="12345678",
            title="Test Paper",
            abstract="Abstract text",
            authors=["Smith J"],
            journal="Nature",
            year=2024,
            score=0.95,
            pub_types=["Review"],
            mesh_terms=["Depression"],
            match_reasons=["keyword", "semantic"],
            pubmed_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        )
        assert paper.year == 2024
        assert len(paper.authors) == 1
        assert len(paper.match_reasons) == 2


class TestSearchResponse:
    def test_minimal(self):
        resp = SearchResponse(session_id="sess-1", query="test")
        assert resp.results == []
        assert resp.total_results == 0
        assert resp.cached is False
        assert resp.ai_summary is None

    def test_with_results(self):
        paper = PaperResult(pmid="1")
        resp = SearchResponse(
            session_id="sess-1", query="test",
            results=[paper], total_results=1,
            ai_summary="Evidence suggests...",
            citations=["1"],
        )
        assert len(resp.results) == 1
        assert resp.citations == ["1"]


class TestRefineRequest:
    def test_valid(self):
        req = RefineRequest(session_id="sess-1")
        assert req.session_id == "sess-1"
        assert req.feedback is None

    def test_with_feedback(self):
        req = RefineRequest(session_id="sess-1", feedback="more recent papers")
        assert req.feedback == "more recent papers"
