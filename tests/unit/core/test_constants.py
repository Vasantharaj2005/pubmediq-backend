"""
Tests for app.core.constants

Verifies that all application constants:
  - Have the expected values (no accidental changes)
  - STUDY_TYPE_MAP has valid structure
  - Cache prefixes are non-empty strings
  - Regex patterns compile without errors
"""
from __future__ import annotations

import re

from app.core.constants import (
    AUTH_HEADER,
    BEARER_PREFIX,
    CACHE_PREFIX_ARTICLE,
    CACHE_PREFIX_BLACKLIST,
    CACHE_PREFIX_RATE_LIMIT,
    CACHE_PREFIX_SEARCH,
    CACHE_PREFIX_SESSION,
    DEFAULT_TOP_K,
    EMAIL_PATTERN,
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE,
    HTTP_429_RATE_LIMIT,
    HTTP_500_SERVER_ERROR,
    HTTP_502_BAD_GATEWAY,
    LLM_MAX_TOKENS_ANSWER,
    LLM_MAX_TOKENS_CONCEPTS,
    LLM_MAX_TOKENS_INTENT,
    LLM_TEMPERATURE_CREATIVE,
    LLM_TEMPERATURE_DEFAULT,
    MAX_REFINEMENTS,
    MAX_TOP_K,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    PMID_PATTERN,
    PUBMED_DB,
    PUBMED_MAX_RESULTS,
    QUALITY_THRESHOLD,
    RRF_K,
    STUDY_TYPE_MAP,
    SYNTHESIS_MAX_ABSTRACT_CHARS,
    SYNTHESIS_MAX_PAPERS,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    WEIGHT_KEYWORD,
    WEIGHT_MESH,
    WEIGHT_RECENCY,
    WEIGHT_SEMANTIC,
    WEIGHT_STUDY_TYPE,
)


class TestSearchPipelineConstants:
    def test_max_refinements(self):
        assert MAX_REFINEMENTS == 2
        assert isinstance(MAX_REFINEMENTS, int)

    def test_quality_threshold(self):
        assert QUALITY_THRESHOLD == 0.65
        assert 0.0 < QUALITY_THRESHOLD < 1.0

    def test_default_top_k(self):
        assert DEFAULT_TOP_K == 20
        assert DEFAULT_TOP_K > 0

    def test_max_top_k(self):
        assert MAX_TOP_K == 100
        assert MAX_TOP_K >= DEFAULT_TOP_K

    def test_pubmed_max_results(self):
        assert PUBMED_MAX_RESULTS == 100
        assert PUBMED_MAX_RESULTS > 0

    def test_rrf_k_constant(self):
        """RRF smoothing constant k=60 (Cormack et al., 2009)."""
        assert RRF_K == 60
        assert RRF_K > 0


class TestFusionWeights:
    def test_weights_sum_to_one(self):
        """All fusion weights should sum to 1.0."""
        total = WEIGHT_SEMANTIC + WEIGHT_KEYWORD + WEIGHT_MESH + WEIGHT_RECENCY + WEIGHT_STUDY_TYPE
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_semantic_weight_is_highest(self):
        """Semantic should be the most important signal."""
        assert WEIGHT_SEMANTIC >= WEIGHT_KEYWORD
        assert WEIGHT_SEMANTIC >= WEIGHT_MESH

    def test_all_weights_positive(self):
        for w in (WEIGHT_SEMANTIC, WEIGHT_KEYWORD, WEIGHT_MESH, WEIGHT_RECENCY, WEIGHT_STUDY_TYPE):
            assert w > 0


class TestAuthConstants:
    def test_token_types(self):
        assert TOKEN_TYPE_ACCESS == "access"
        assert TOKEN_TYPE_REFRESH == "refresh"

    def test_bearer_prefix(self):
        assert BEARER_PREFIX == "Bearer"

    def test_auth_header(self):
        assert AUTH_HEADER == "Authorization"


class TestCachePrefixes:
    def test_all_prefixes_non_empty(self):
        for prefix in (CACHE_PREFIX_SEARCH, CACHE_PREFIX_ARTICLE,
                       CACHE_PREFIX_SESSION, CACHE_PREFIX_BLACKLIST,
                       CACHE_PREFIX_RATE_LIMIT):
            assert isinstance(prefix, str)
            assert len(prefix) > 0

    def test_prefixes_end_with_colon(self):
        """Convention: all prefixes end with ':' for Redis key namespacing."""
        for prefix in (CACHE_PREFIX_SEARCH, CACHE_PREFIX_ARTICLE,
                       CACHE_PREFIX_SESSION, CACHE_PREFIX_BLACKLIST,
                       CACHE_PREFIX_RATE_LIMIT):
            assert prefix.endswith(":"), f"'{prefix}' should end with ':'"


class TestStudyTypeMap:
    def test_map_is_non_empty(self):
        assert len(STUDY_TYPE_MAP) > 0

    def test_all_values_are_lists(self):
        for key, value in STUDY_TYPE_MAP.items():
            assert isinstance(value, list), f"STUDY_TYPE_MAP['{key}'] should be a list"
            assert len(value) > 0, f"STUDY_TYPE_MAP['{key}'] should not be empty"

    def test_expected_keys_present(self):
        expected = {"randomized_controlled_trial", "systematic_review",
                    "clinical_trial", "observational", "review", "case_report"}
        for key in expected:
            assert key in STUDY_TYPE_MAP, f"Expected key '{key}' in STUDY_TYPE_MAP"

    def test_all_values_are_strings(self):
        for key, values in STUDY_TYPE_MAP.items():
            for v in values:
                assert isinstance(v, str), f"STUDY_TYPE_MAP['{key}'] contains non-string: {v}"


class TestLLMConstants:
    def test_temperature_default(self):
        assert 0.0 <= LLM_TEMPERATURE_DEFAULT <= 1.0

    def test_temperature_creative(self):
        assert LLM_TEMPERATURE_CREATIVE > LLM_TEMPERATURE_DEFAULT

    def test_max_tokens_positive(self):
        assert LLM_MAX_TOKENS_ANSWER > 0
        assert LLM_MAX_TOKENS_INTENT > 0
        assert LLM_MAX_TOKENS_CONCEPTS > 0

    def test_synthesis_limits(self):
        assert SYNTHESIS_MAX_PAPERS > 0
        assert SYNTHESIS_MAX_ABSTRACT_CHARS > 0


class TestPaginationConstants:
    def test_defaults(self):
        assert PAGE_SIZE_DEFAULT == 20
        assert PAGE_SIZE_MAX == 100
        assert PAGE_SIZE_MAX >= PAGE_SIZE_DEFAULT


class TestHTTPStatusConstants:
    def test_success_codes(self):
        assert HTTP_200_OK == 200
        assert HTTP_201_CREATED == 201

    def test_client_error_codes(self):
        assert HTTP_401_UNAUTHORIZED == 401
        assert HTTP_404_NOT_FOUND == 404
        assert HTTP_409_CONFLICT == 409
        assert HTTP_422_UNPROCESSABLE == 422
        assert HTTP_429_RATE_LIMIT == 429

    def test_server_error_codes(self):
        assert HTTP_500_SERVER_ERROR == 500
        assert HTTP_502_BAD_GATEWAY == 502


class TestRegexPatterns:
    def test_pmid_pattern_compiles(self):
        pattern = re.compile(PMID_PATTERN)
        assert pattern.match("12345678")
        assert pattern.match("1")
        assert not pattern.match("123456789")  # 9 digits > 8
        assert not pattern.match("")
        assert not pattern.match("abc")

    def test_email_pattern_compiles(self):
        pattern = re.compile(EMAIL_PATTERN)
        assert pattern.match("user@example.com")
        assert pattern.match("test+tag@sub.domain.org")
        assert not pattern.match("notanemail")
        assert not pattern.match("@missing.com")

    def test_pubmed_db(self):
        assert PUBMED_DB == "pubmed"
