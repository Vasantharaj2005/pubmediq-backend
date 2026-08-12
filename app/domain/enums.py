"""
PubMedIQ — Domain Enumerations

All application-level enum types. Use these in domain models, schemas,
and services — never raw strings for categorized values.
"""
from __future__ import annotations

from enum import Enum


class StudyType(str, Enum):
    """PubMed publication/study types."""
    RANDOMIZED_CONTROLLED_TRIAL = "randomized_controlled_trial"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    CLINICAL_TRIAL = "clinical_trial"
    OBSERVATIONAL = "observational"
    COHORT_STUDY = "cohort_study"
    CASE_CONTROL = "case_control"
    REVIEW = "review"
    CASE_REPORT = "case_report"
    ANY = "any"


class SearchMode(str, Enum):
    """How the search engine retrieved results."""
    HYBRID = "hybrid"       # keyword + MeSH + semantic (default)
    KEYWORD = "keyword"     # PubMed keyword only
    SEMANTIC = "semantic"   # Pinecone vector search only
    MESH = "mesh"           # MeSH-only search


class QualityLevel(str, Enum):
    """Evidence quality gate output."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TokenType(str, Enum):
    """JWT token classification."""
    ACCESS = "access"
    REFRESH = "refresh"


class FeedbackRating(int, Enum):
    """User feedback rating scale."""
    VERY_POOR = 1
    POOR = 2
    NEUTRAL = 3
    GOOD = 4
    EXCELLENT = 5


class AppEnvironment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProviderEnum(str, Enum):
    """Supported LLM providers."""
    GROQ = "groq"
    GEMINI = "gemini"
    OPENAI = "openai"
    AUTO = "auto"
