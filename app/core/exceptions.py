"""
PubMedIQ — Custom Exception Hierarchy

All application exceptions are defined here so that:
- Exception handlers in main.py can catch them uniformly
- Handlers in endpoints can be thin
- HTTP status codes are centralised
"""
from __future__ import annotations

from http import HTTPStatus


class PubMedIQError(Exception):
    """Base exception for all PubMedIQ application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, error_code: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        self.error_code = error_code or self.__class__.error_code
        super().__init__(self.detail)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.error_code,
                "message": self.detail,
            }
        }


# ------------------------------------------------------------------
# Authentication & Authorization
# ------------------------------------------------------------------
class AuthError(PubMedIQError):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    detail = "Authentication failed."


class InvalidCredentialsError(AuthError):
    error_code = "INVALID_CREDENTIALS"
    detail = "Invalid email or password."


class TokenExpiredError(AuthError):
    error_code = "TOKEN_EXPIRED"
    detail = "Authentication token has expired."


class TokenInvalidError(AuthError):
    error_code = "TOKEN_INVALID"
    detail = "Authentication token is invalid."


class TokenBlacklistedError(AuthError):
    error_code = "TOKEN_REVOKED"
    detail = "Authentication token has been revoked."


class PermissionDeniedError(PubMedIQError):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    detail = "You do not have permission to perform this action."


# ------------------------------------------------------------------
# Resource Errors
# ------------------------------------------------------------------
class NotFoundError(PubMedIQError):
    status_code = 404
    error_code = "NOT_FOUND"
    detail = "The requested resource was not found."


class UserNotFoundError(NotFoundError):
    error_code = "USER_NOT_FOUND"
    detail = "User not found."


class PaperNotFoundError(NotFoundError):
    error_code = "PAPER_NOT_FOUND"
    detail = "PubMed article not found."


class HistoryNotFoundError(NotFoundError):
    error_code = "HISTORY_NOT_FOUND"
    detail = "Search history record not found."


# ------------------------------------------------------------------
# Conflict Errors
# ------------------------------------------------------------------
class ConflictError(PubMedIQError):
    status_code = 409
    error_code = "CONFLICT"
    detail = "Resource already exists."


class UserAlreadyExistsError(ConflictError):
    error_code = "USER_ALREADY_EXISTS"
    detail = "A user with this email address already exists."


class PaperAlreadySavedError(ConflictError):
    error_code = "PAPER_ALREADY_SAVED"
    detail = "This paper is already saved."


# ------------------------------------------------------------------
# Validation Errors
# ------------------------------------------------------------------
class ValidationError(PubMedIQError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    detail = "Request validation failed."


class InvalidQueryError(ValidationError):
    error_code = "INVALID_QUERY"
    detail = "Search query is invalid or too short."


# ------------------------------------------------------------------
# Rate Limiting
# ------------------------------------------------------------------
class RateLimitError(PubMedIQError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    detail = "Too many requests. Please slow down."


# ------------------------------------------------------------------
# External Service Errors
# ------------------------------------------------------------------
class ExternalServiceError(PubMedIQError):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    detail = "An external service is unavailable."


class PubMedError(ExternalServiceError):
    error_code = "PUBMED_UNAVAILABLE"
    detail = "PubMed API is temporarily unavailable. Using cached results where possible."


class PubMedRateLimitError(PubMedError):
    error_code = "PUBMED_RATE_LIMIT"
    detail = "PubMed API rate limit exceeded. Please retry shortly."


class PineconeError(ExternalServiceError):
    error_code = "PINECONE_UNAVAILABLE"
    detail = "Vector database is temporarily unavailable."


class LLMError(ExternalServiceError):
    error_code = "LLM_UNAVAILABLE"
    detail = "Language model service is temporarily unavailable."


class LLMRateLimitError(LLMError):
    error_code = "LLM_RATE_LIMIT"
    detail = "Language model rate limit exceeded. Switching to fallback provider."


# ------------------------------------------------------------------
# Search & Agent Errors
# ------------------------------------------------------------------
class SearchError(PubMedIQError):
    status_code = 500
    error_code = "SEARCH_ERROR"
    detail = "Search pipeline encountered an error."


class NoResultsError(PubMedIQError):
    status_code = 200  # Not an error per se — caller handles gracefully
    error_code = "NO_RESULTS"
    detail = "No relevant results found for this query."


class MaxRefinementsReachedError(SearchError):
    error_code = "MAX_REFINEMENTS_REACHED"
    detail = "Could not find high-quality results after maximum refinement attempts."


# ------------------------------------------------------------------
# Database Errors
# ------------------------------------------------------------------
class DatabaseError(PubMedIQError):
    status_code = 500
    error_code = "DATABASE_ERROR"
    detail = "A database error occurred."
