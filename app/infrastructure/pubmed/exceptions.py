"""
PubMedIQ — PubMed Infrastructure Exceptions
"""
from __future__ import annotations

from app.core.exceptions import ExternalServiceError


class PubMedAPIError(ExternalServiceError):
    error_code = "PUBMED_API_ERROR"
    detail = "PubMed API returned an unexpected response."


class PubMedRateLimitError(PubMedAPIError):
    error_code = "PUBMED_RATE_LIMIT"
    detail = "PubMed API rate limit exceeded. Please retry shortly."


class PubMedNotFoundError(PubMedAPIError):
    error_code = "PUBMED_NOT_FOUND"
    detail = "The requested PubMed record was not found."


class PubMedParseError(PubMedAPIError):
    error_code = "PUBMED_PARSE_ERROR"
    detail = "Failed to parse PubMed API response."
