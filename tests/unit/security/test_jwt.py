"""
Tests for app.infrastructure.security.jwt

Verifies token creation, decoding, validation, and edge cases.
Uses real JWT operations but with test-only secret keys.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.exceptions import TokenExpiredError, TokenInvalidError
from app.infrastructure.security.jwt import JWTService, TokenData


@pytest.fixture
def jwt_svc() -> JWTService:
    """JWTService configured with test secrets (reads from test env vars)."""
    return JWTService()


@pytest.fixture
def sample_user_id() -> str:
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture
def sample_email() -> str:
    return "test@pubmediq.com"


class TestAccessTokenCreation:
    def test_creates_non_empty_string(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_access_token(sample_user_id, sample_email)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_parts(self, jwt_svc, sample_user_id, sample_email):
        """JWT format: header.payload.signature"""
        token = jwt_svc.create_access_token(sample_user_id, sample_email)
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_roundtrip(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_access_token(sample_user_id, sample_email)
        data = jwt_svc.decode_token(token)
        assert data.user_id == sample_user_id
        assert data.email == sample_email
        assert data.token_type == "access"
        assert data.jti is not None
        assert isinstance(data.exp, datetime)

    def test_unique_jti_per_token(self, jwt_svc, sample_user_id, sample_email):
        t1 = jwt_svc.create_access_token(sample_user_id, sample_email)
        t2 = jwt_svc.create_access_token(sample_user_id, sample_email)
        d1 = jwt_svc.decode_token(t1)
        d2 = jwt_svc.decode_token(t2)
        assert d1.jti != d2.jti

    def test_extra_claims(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_access_token(
            sample_user_id, sample_email, extra_claims={"role": "admin"}
        )
        # Token should still decode fine
        data = jwt_svc.decode_token(token)
        assert data.user_id == sample_user_id


class TestRefreshTokenCreation:
    def test_creates_refresh_token(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_refresh_token(sample_user_id, sample_email)
        data = jwt_svc.decode_token(token)
        assert data.token_type == "refresh"

    def test_refresh_token_longer_expiry(self, jwt_svc, sample_user_id, sample_email):
        """Refresh token should expire later than access token."""
        access = jwt_svc.create_access_token(sample_user_id, sample_email)
        refresh = jwt_svc.create_refresh_token(sample_user_id, sample_email)
        access_data = jwt_svc.decode_token(access)
        refresh_data = jwt_svc.decode_token(refresh)
        assert refresh_data.exp > access_data.exp


class TestTokenValidation:
    def test_validate_access_token(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_access_token(sample_user_id, sample_email)
        data = jwt_svc.validate_token(token, "access")
        assert data.token_type == "access"

    def test_validate_refresh_token(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_refresh_token(sample_user_id, sample_email)
        data = jwt_svc.validate_token(token, "refresh")
        assert data.token_type == "refresh"

    def test_wrong_token_type_raises(self, jwt_svc, sample_user_id, sample_email):
        """Using an access token where refresh is expected should fail."""
        access = jwt_svc.create_access_token(sample_user_id, sample_email)
        with pytest.raises(TokenInvalidError):
            jwt_svc.validate_token(access, "refresh")

    def test_tampered_token_raises(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_access_token(sample_user_id, sample_email)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(TokenInvalidError):
            jwt_svc.decode_token(tampered)

    def test_garbage_token_raises(self, jwt_svc):
        with pytest.raises(TokenInvalidError):
            jwt_svc.decode_token("not.a.valid.jwt")

    def test_empty_token_raises(self, jwt_svc):
        with pytest.raises((TokenInvalidError, Exception)):
            jwt_svc.decode_token("")


class TestTokenExpiry:
    def test_expired_token_raises(self, sample_user_id, sample_email):
        """Create a service with 0-minute expiry, token should immediately expire."""
        svc = JWTService()
        # Patch _access_expire to 0 to simulate expired token
        svc._access_expire = 0

        token = svc.create_access_token(sample_user_id, sample_email)
        # Token created with exp = now + 0 minutes = now, so it's already expired
        # We need a tiny sleep or it might not be expired yet
        time.sleep(1)
        with pytest.raises(TokenExpiredError):
            svc.decode_token(token)


class TestGetTokenJTI:
    def test_get_jti_from_valid_token(self, jwt_svc, sample_user_id, sample_email):
        token = jwt_svc.create_access_token(sample_user_id, sample_email)
        jti = jwt_svc.get_token_jti(token)
        assert isinstance(jti, str)
        assert len(jti) > 0

    def test_get_jti_from_expired_token(self, sample_user_id, sample_email):
        """get_token_jti should work even for expired tokens (for logout)."""
        svc = JWTService()
        svc._access_expire = 0
        token = svc.create_access_token(sample_user_id, sample_email)
        time.sleep(1)

        # Should NOT raise even though token is expired
        jti = svc.get_token_jti(token)
        assert isinstance(jti, str)
        assert len(jti) > 0

    def test_get_jti_from_garbage_raises(self, jwt_svc):
        with pytest.raises(TokenInvalidError):
            jwt_svc.get_token_jti("garbage-token")


class TestTokenDataModel:
    def test_token_data_attributes(self):
        now = datetime.now(tz=timezone.utc)
        td = TokenData(
            user_id="uid", email="e@e.com",
            token_type="access", jti="jti-1", exp=now,
        )
        assert td.user_id == "uid"
        assert td.email == "e@e.com"
        assert td.token_type == "access"
        assert td.jti == "jti-1"
        assert td.exp == now
