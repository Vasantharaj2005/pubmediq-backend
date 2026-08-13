"""
Tests for app.core.exceptions

Verifies that every custom exception in the hierarchy has:
  - The correct HTTP status code
  - The correct error code string
  - A meaningful default detail message
  - A well-formed to_dict() output
"""
from __future__ import annotations

import pytest

from app.core.exceptions import (
    AuthError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    HistoryNotFoundError,
    InvalidCredentialsError,
    InvalidQueryError,
    LLMError,
    LLMRateLimitError,
    MaxRefinementsReachedError,
    NoResultsError,
    NotFoundError,
    PaperAlreadySavedError,
    PaperNotFoundError,
    PermissionDeniedError,
    PineconeError,
    PubMedError,
    PubMedIQError,
    PubMedRateLimitError,
    RateLimitError,
    SearchError,
    TokenBlacklistedError,
    TokenExpiredError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)


# =====================================================================
# Base exception
# =====================================================================
class TestPubMedIQError:
    def test_default_status_code(self):
        exc = PubMedIQError()
        assert exc.status_code == 500

    def test_default_error_code(self):
        exc = PubMedIQError()
        assert exc.error_code == "INTERNAL_ERROR"

    def test_default_detail(self):
        exc = PubMedIQError()
        assert exc.detail == "An unexpected error occurred."

    def test_custom_detail(self):
        exc = PubMedIQError(detail="Something broke")
        assert exc.detail == "Something broke"

    def test_custom_error_code(self):
        exc = PubMedIQError(error_code="CUSTOM_CODE")
        assert exc.error_code == "CUSTOM_CODE"

    def test_to_dict_structure(self):
        exc = PubMedIQError()
        d = exc.to_dict()
        assert "error" in d
        assert "code" in d["error"]
        assert "message" in d["error"]
        assert d["error"]["code"] == "INTERNAL_ERROR"

    def test_is_exception(self):
        exc = PubMedIQError()
        assert isinstance(exc, Exception)

    def test_str_representation(self):
        exc = PubMedIQError(detail="test message")
        assert str(exc) == "test message"


# =====================================================================
# Auth exceptions
# =====================================================================
class TestAuthExceptions:
    def test_auth_error_status(self):
        assert AuthError().status_code == 401

    def test_invalid_credentials(self):
        exc = InvalidCredentialsError()
        assert exc.status_code == 401
        assert exc.error_code == "INVALID_CREDENTIALS"
        assert "email" in exc.detail.lower() or "password" in exc.detail.lower()

    def test_token_expired(self):
        exc = TokenExpiredError()
        assert exc.status_code == 401
        assert exc.error_code == "TOKEN_EXPIRED"

    def test_token_invalid(self):
        exc = TokenInvalidError()
        assert exc.status_code == 401
        assert exc.error_code == "TOKEN_INVALID"

    def test_token_blacklisted(self):
        exc = TokenBlacklistedError()
        assert exc.status_code == 401
        assert exc.error_code == "TOKEN_REVOKED"

    def test_permission_denied(self):
        exc = PermissionDeniedError()
        assert exc.status_code == 403
        assert exc.error_code == "PERMISSION_DENIED"

    def test_auth_exceptions_inherit_from_base(self):
        """All auth exceptions must be caught by PubMedIQError handler."""
        for cls in (AuthError, InvalidCredentialsError, TokenExpiredError,
                    TokenInvalidError, TokenBlacklistedError):
            assert issubclass(cls, PubMedIQError)


# =====================================================================
# Resource exceptions
# =====================================================================
class TestResourceExceptions:
    def test_not_found_base(self):
        assert NotFoundError().status_code == 404

    def test_user_not_found(self):
        exc = UserNotFoundError()
        assert exc.status_code == 404
        assert exc.error_code == "USER_NOT_FOUND"

    def test_paper_not_found(self):
        exc = PaperNotFoundError()
        assert exc.status_code == 404
        assert exc.error_code == "PAPER_NOT_FOUND"

    def test_history_not_found(self):
        exc = HistoryNotFoundError()
        assert exc.status_code == 404
        assert exc.error_code == "HISTORY_NOT_FOUND"


# =====================================================================
# Conflict exceptions
# =====================================================================
class TestConflictExceptions:
    def test_conflict_base(self):
        assert ConflictError().status_code == 409

    def test_user_already_exists(self):
        exc = UserAlreadyExistsError()
        assert exc.status_code == 409
        assert exc.error_code == "USER_ALREADY_EXISTS"

    def test_paper_already_saved(self):
        exc = PaperAlreadySavedError()
        assert exc.status_code == 409
        assert exc.error_code == "PAPER_ALREADY_SAVED"


# =====================================================================
# Validation exceptions
# =====================================================================
class TestValidationExceptions:
    def test_validation_base(self):
        assert ValidationError().status_code == 422

    def test_invalid_query(self):
        exc = InvalidQueryError()
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_QUERY"


# =====================================================================
# Rate limiting
# =====================================================================
class TestRateLimitException:
    def test_rate_limit(self):
        exc = RateLimitError()
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"


# =====================================================================
# External service exceptions
# =====================================================================
class TestExternalServiceExceptions:
    def test_external_base(self):
        assert ExternalServiceError().status_code == 502

    def test_pubmed_error(self):
        exc = PubMedError()
        assert exc.status_code == 502
        assert exc.error_code == "PUBMED_UNAVAILABLE"

    def test_pubmed_rate_limit(self):
        exc = PubMedRateLimitError()
        assert exc.status_code == 502
        assert "rate limit" in exc.detail.lower()

    def test_pinecone_error(self):
        exc = PineconeError()
        assert exc.status_code == 502
        assert exc.error_code == "PINECONE_UNAVAILABLE"

    def test_llm_error(self):
        exc = LLMError()
        assert exc.status_code == 502
        assert exc.error_code == "LLM_UNAVAILABLE"

    def test_llm_rate_limit(self):
        exc = LLMRateLimitError()
        assert exc.status_code == 502
        assert exc.error_code == "LLM_RATE_LIMIT"

    def test_external_exceptions_inherit_chain(self):
        """PubMedError → ExternalServiceError → PubMedIQError."""
        assert issubclass(PubMedError, ExternalServiceError)
        assert issubclass(ExternalServiceError, PubMedIQError)
        assert issubclass(LLMRateLimitError, LLMError)


# =====================================================================
# Search exceptions
# =====================================================================
class TestSearchExceptions:
    def test_search_error(self):
        assert SearchError().status_code == 500

    def test_no_results(self):
        exc = NoResultsError()
        assert exc.status_code == 200  # Not an error — handled gracefully
        assert exc.error_code == "NO_RESULTS"

    def test_max_refinements_reached(self):
        exc = MaxRefinementsReachedError()
        assert exc.status_code == 500
        assert exc.error_code == "MAX_REFINEMENTS_REACHED"


# =====================================================================
# Database exceptions
# =====================================================================
class TestDatabaseException:
    def test_database_error(self):
        exc = DatabaseError()
        assert exc.status_code == 500
        assert exc.error_code == "DATABASE_ERROR"


# =====================================================================
# to_dict consistency
# =====================================================================
class TestToDictConsistency:
    """Verify all exceptions produce consistent JSON-serializable dicts."""

    EXCEPTION_CLASSES = [
        PubMedIQError, AuthError, InvalidCredentialsError,
        TokenExpiredError, TokenInvalidError, TokenBlacklistedError,
        PermissionDeniedError, NotFoundError, UserNotFoundError,
        PaperNotFoundError, ConflictError, UserAlreadyExistsError,
        ValidationError, RateLimitError, ExternalServiceError,
        PubMedError, PineconeError, LLMError, SearchError,
        NoResultsError, DatabaseError,
    ]

    @pytest.mark.parametrize("exc_class", EXCEPTION_CLASSES)
    def test_to_dict_has_error_key(self, exc_class):
        d = exc_class().to_dict()
        assert "error" in d
        assert isinstance(d["error"], dict)
        assert "code" in d["error"]
        assert "message" in d["error"]
        assert isinstance(d["error"]["code"], str)
        assert isinstance(d["error"]["message"], str)
        assert len(d["error"]["code"]) > 0
        assert len(d["error"]["message"]) > 0
