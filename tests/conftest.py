"""
PubMedIQ — Root Test Configuration

Global fixtures shared across ALL test categories:
  - pytest-asyncio configuration
  - Environment variable overrides for testing
  - Shared helpers
"""
from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Override settings BEFORE any app module is imported
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars!!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-that-is-at-least-32-chars!!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("GOOGLE_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("PINECONE_API_KEY", "")


# ---------------------------------------------------------------------------
# pytest-asyncio configuration
# ---------------------------------------------------------------------------
@pytest.fixture
def anyio_backend():
    """Required by pytest-asyncio — use asyncio backend."""
    return "asyncio"
