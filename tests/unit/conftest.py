"""
PubMedIQ — Unit Test Configuration

Fixtures shared across all unit tests.
Unit tests must NEVER touch real databases, Redis, or external APIs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_user_id() -> str:
    """Return a deterministic UUID string for test users."""
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture
def sample_email() -> str:
    return "test@pubmediq.com"


@pytest.fixture
def sample_password() -> str:
    return "SecureP@ss123"


@pytest.fixture
def sample_full_name() -> str:
    return "Test User"


@pytest.fixture
def sample_paper() -> dict:
    """A realistic PubMed paper dict as produced by retrieval nodes."""
    return {
        "pmid": "12345678",
        "title": "Effect of exercise on depression in elderly patients: a systematic review",
        "abstract": (
            "BACKGROUND: Depression is common in elderly populations. "
            "Exercise has been proposed as an adjunctive treatment. "
            "METHODS: We conducted a systematic review of randomized controlled trials. "
            "RESULTS: 15 studies met inclusion criteria involving 1,234 participants. "
            "Exercise significantly reduced depression scores (SMD -0.45, 95% CI -0.62 to -0.28). "
            "CONCLUSION: Exercise is an effective intervention for depression in older adults."
        ),
        "authors": ["Smith J", "Doe A", "Johnson B"],
        "journal": "Journal of Geriatric Psychiatry",
        "year": 2024,
        "pub_types": ["Systematic Review", "Meta-Analysis"],
        "mesh_terms": ["Depression", "Exercise", "Aged"],
        "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
    }


@pytest.fixture
def sample_papers(sample_paper) -> list[dict]:
    """Multiple papers with different PMIDs for fusion/rerank testing."""
    papers = []
    for i in range(5):
        p = dict(sample_paper)
        p["pmid"] = str(10000000 + i)
        p["title"] = f"Paper #{i + 1}: {sample_paper['title']}"
        papers.append(p)
    return papers


@pytest.fixture
def sample_research_state() -> dict:
    """Pre-populated ResearchState for agent node testing."""
    return {
        "query": "What is the effect of exercise on depression in elderly patients?",
        "session_id": "test-session-001",
        "top_k": 20,
        "filters": {},
        "refinement_count": 0,
        "errors": [],
    }


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock async SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session
