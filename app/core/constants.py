"""
PubMedIQ — Application Constants

Single source of truth for all magic numbers and string constants.
Import from here — never hard-code values in business logic.
"""
from __future__ import annotations

# ------------------------------------------------------------------
# Search Pipeline
# ------------------------------------------------------------------
MAX_REFINEMENTS: int = 2
QUALITY_THRESHOLD: float = 0.65  # minimum average rerank score to accept results
DEFAULT_TOP_K: int = 20
MAX_TOP_K: int = 100
PUBMED_MAX_RESULTS: int = 100

# Fusion weights for result scoring
WEIGHT_SEMANTIC: float = 0.35
WEIGHT_KEYWORD: float = 0.30
WEIGHT_MESH: float = 0.25
WEIGHT_RECENCY: float = 0.05
WEIGHT_STUDY_TYPE: float = 0.05

# Reciprocal Rank Fusion constant (prevents division by zero)
RRF_K: int = 60

# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------
TOKEN_TYPE_ACCESS: str = "access"
TOKEN_TYPE_REFRESH: str = "refresh"
BEARER_PREFIX: str = "Bearer"
AUTH_HEADER: str = "Authorization"

# ------------------------------------------------------------------
# Cache Key Prefixes (Redis)
# ------------------------------------------------------------------
CACHE_PREFIX_SEARCH: str = "search:"
CACHE_PREFIX_ARTICLE: str = "article:"
CACHE_PREFIX_SESSION: str = "session:"
CACHE_PREFIX_BLACKLIST: str = "blacklist:"
CACHE_PREFIX_RATE_LIMIT: str = "rate:"

# ------------------------------------------------------------------
# PubMed E-Utils
# ------------------------------------------------------------------
PUBMED_DB: str = "pubmed"
MESH_DB: str = "mesh"
PUBMED_RETMODE: str = "json"
PUBMED_EFETCH_RETTYPE: str = "abstract"

# Study type mappings (PubMed publication type terms)
STUDY_TYPE_MAP: dict[str, list[str]] = {
    "randomized_controlled_trial": [
        "Randomized Controlled Trial",
        "Randomized Clinical Trial",
    ],
    "systematic_review": [
        "Systematic Review",
        "Meta-Analysis",
    ],
    "clinical_trial": [
        "Clinical Trial",
        "Clinical Trial, Phase I",
        "Clinical Trial, Phase II",
        "Clinical Trial, Phase III",
        "Clinical Trial, Phase IV",
    ],
    "observational": [
        "Observational Study",
        "Cohort Study",
        "Case-Control Study",
    ],
    "review": [
        "Review",
        "Literature Review",
    ],
    "case_report": [
        "Case Reports",
    ],
}

# ------------------------------------------------------------------
# LLM / Agent
# ------------------------------------------------------------------
LLM_TEMPERATURE_DEFAULT: float = 0.1
LLM_TEMPERATURE_CREATIVE: float = 0.7
LLM_MAX_TOKENS_ANSWER: int = 2048
LLM_MAX_TOKENS_INTENT: int = 512
LLM_MAX_TOKENS_CONCEPTS: int = 1024

# Max papers fed to synthesis node
SYNTHESIS_MAX_PAPERS: int = 10
SYNTHESIS_MAX_ABSTRACT_CHARS: int = 800

# ------------------------------------------------------------------
# Pagination
# ------------------------------------------------------------------
PAGE_SIZE_DEFAULT: int = 20
PAGE_SIZE_MAX: int = 100

# ------------------------------------------------------------------
# HTTP Status Aliases (for readability in endpoints)
# ------------------------------------------------------------------
HTTP_200_OK: int = 200
HTTP_201_CREATED: int = 201
HTTP_204_NO_CONTENT: int = 204
HTTP_400_BAD_REQUEST: int = 400
HTTP_401_UNAUTHORIZED: int = 401
HTTP_403_FORBIDDEN: int = 403
HTTP_404_NOT_FOUND: int = 404
HTTP_409_CONFLICT: int = 409
HTTP_422_UNPROCESSABLE: int = 422
HTTP_429_RATE_LIMIT: int = 429
HTTP_500_SERVER_ERROR: int = 500
HTTP_502_BAD_GATEWAY: int = 502
HTTP_503_UNAVAILABLE: int = 503

# ------------------------------------------------------------------
# Regex Patterns
# ------------------------------------------------------------------
PMID_PATTERN: str = r"^\d{1,8}$"
EMAIL_PATTERN: str = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
