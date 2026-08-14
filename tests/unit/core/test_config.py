"""
Tests for app.core.config

Verifies Settings loading, defaults, validators, and computed properties.
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from app.core.config import Settings, get_settings


class TestSettingsDefaults:
    """Verify default values when no env vars are set."""

    def test_app_name(self):
        s = Settings()
        assert s.APP_NAME == "PubMedIQ"

    def test_app_version(self):
        s = Settings()
        assert isinstance(s.APP_VERSION, str)
        assert len(s.APP_VERSION) > 0

    def test_default_llm_provider(self):
        s = Settings()
        assert s.DEFAULT_LLM_PROVIDER == "groq"

    def test_embedding_dimension(self):
        s = Settings()
        assert s.EMBEDDING_DIMENSION == 768

    def test_quality_threshold(self):
        s = Settings()
        assert s.QUALITY_THRESHOLD == 0.65

    def test_jwt_defaults(self):
        s = Settings()
        assert s.JWT_ALGORITHM == "HS256"
        assert s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert s.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_reranker_defaults(self):
        s = Settings()
        assert s.RERANKER_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert s.RERANKER_DEVICE == "cpu"
        assert s.RERANKER_TOP_K == 10


class TestCORSValidator:
    """Test the parse_cors field validator."""

    def test_parse_cors_from_json_string(self):
        """CORS_ORIGINS can be a JSON array string."""
        s = Settings(CORS_ORIGINS='["http://a.com", "http://b.com"]')
        assert s.CORS_ORIGINS == ["http://a.com", "http://b.com"]

    def test_parse_cors_from_comma_separated(self):
        """CORS_ORIGINS can be a comma-separated string."""
        s = Settings(CORS_ORIGINS="http://a.com, http://b.com")
        assert s.CORS_ORIGINS == ["http://a.com", "http://b.com"]

    def test_parse_cors_from_list(self):
        """CORS_ORIGINS can be passed as a list directly."""
        s = Settings(CORS_ORIGINS=["http://a.com"])
        assert s.CORS_ORIGINS == ["http://a.com"]

    def test_parse_cors_single_value(self):
        s = Settings(CORS_ORIGINS="http://localhost:3000")
        assert s.CORS_ORIGINS == ["http://localhost:3000"]


class TestComputedProperties:
    def test_is_production(self):
        s = Settings(APP_ENV="production")
        assert s.is_production is True
        assert s.is_development is False

    def test_is_development(self):
        s = Settings(APP_ENV="development")
        assert s.is_development is True
        assert s.is_production is False

    def test_pubmed_rate_limit_without_key(self):
        s = Settings(NCBI_API_KEY="")
        assert s.pubmed_rate_limit_effective == 3

    def test_pubmed_rate_limit_with_key(self):
        s = Settings(NCBI_API_KEY="some-api-key")
        assert s.pubmed_rate_limit_effective == 10

    def test_langsmith_disabled_by_default(self):
        s = Settings()
        assert s.langsmith_enabled is False

    def test_langsmith_enabled_with_tracing_and_key(self):
        s = Settings(LANGCHAIN_TRACING_V2=True, LANGCHAIN_API_KEY="key-123")
        assert s.langsmith_enabled is True

    def test_langsmith_disabled_without_key(self):
        s = Settings(LANGCHAIN_TRACING_V2=True, LANGCHAIN_API_KEY="")
        assert s.langsmith_enabled is False


class TestGetSettingsSingleton:
    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_cached(self):
        """get_settings uses lru_cache — should return same object."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
