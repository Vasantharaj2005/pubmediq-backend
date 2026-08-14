"""
Tests for agents/conftest.py — Fixtures for agent-level tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_llm_response():
    """Factory for canned LLM responses."""
    def _make(content: str = '{"result": "ok"}'):
        return content
    return _make
