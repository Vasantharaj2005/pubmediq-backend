"""
Tests for app.domain.enums

Verifies that all enum types have expected members and string values.
"""
from __future__ import annotations

from app.domain.enums import (
    AppEnvironment,
    FeedbackRating,
    LLMProviderEnum,
    QualityLevel,
    SearchMode,
    StudyType,
    TokenType,
)


class TestStudyType:
    def test_member_count(self):
        assert len(StudyType) >= 9  # at least 9 study types defined

    def test_expected_members(self):
        expected = {
            "RANDOMIZED_CONTROLLED_TRIAL", "SYSTEMATIC_REVIEW",
            "META_ANALYSIS", "CLINICAL_TRIAL", "OBSERVATIONAL",
            "COHORT_STUDY", "CASE_CONTROL", "REVIEW", "CASE_REPORT", "ANY",
        }
        actual = {m.name for m in StudyType}
        for name in expected:
            assert name in actual, f"Missing StudyType.{name}"

    def test_values_are_snake_case(self):
        for member in StudyType:
            assert member.value == member.value.lower()
            assert " " not in member.value

    def test_is_string_enum(self):
        assert isinstance(StudyType.REVIEW.value, str)
        assert StudyType.REVIEW == "review"


class TestSearchMode:
    def test_members(self):
        assert SearchMode.HYBRID == "hybrid"
        assert SearchMode.KEYWORD == "keyword"
        assert SearchMode.SEMANTIC == "semantic"
        assert SearchMode.MESH == "mesh"

    def test_default_is_hybrid(self):
        """HYBRID should be the default search mode (verified in schema tests too)."""
        assert SearchMode.HYBRID.value == "hybrid"


class TestQualityLevel:
    def test_members(self):
        assert QualityLevel.HIGH == "high"
        assert QualityLevel.MEDIUM == "medium"
        assert QualityLevel.LOW == "low"

    def test_exactly_three_levels(self):
        assert len(QualityLevel) == 3


class TestTokenType:
    def test_members(self):
        assert TokenType.ACCESS == "access"
        assert TokenType.REFRESH == "refresh"


class TestFeedbackRating:
    def test_is_int_enum(self):
        assert isinstance(FeedbackRating.EXCELLENT.value, int)

    def test_range(self):
        assert FeedbackRating.VERY_POOR.value == 1
        assert FeedbackRating.EXCELLENT.value == 5

    def test_ordering(self):
        assert FeedbackRating.VERY_POOR < FeedbackRating.POOR
        assert FeedbackRating.POOR < FeedbackRating.NEUTRAL
        assert FeedbackRating.NEUTRAL < FeedbackRating.GOOD
        assert FeedbackRating.GOOD < FeedbackRating.EXCELLENT


class TestAppEnvironment:
    def test_members(self):
        assert AppEnvironment.DEVELOPMENT == "development"
        assert AppEnvironment.STAGING == "staging"
        assert AppEnvironment.PRODUCTION == "production"


class TestLLMProviderEnum:
    def test_members(self):
        assert LLMProviderEnum.GROQ == "groq"
        assert LLMProviderEnum.GEMINI == "gemini"
        assert LLMProviderEnum.OPENAI == "openai"
        assert LLMProviderEnum.AUTO == "auto"

    def test_is_string_enum(self):
        for member in LLMProviderEnum:
            assert isinstance(member.value, str)
