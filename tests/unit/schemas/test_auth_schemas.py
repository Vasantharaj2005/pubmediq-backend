"""
Tests for app.schemas.auth

Verifies Pydantic validation for authentication request/response schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


class TestRegisterRequest:
    def test_valid_request(self):
        req = RegisterRequest(
            email="test@example.com",
            password="SecureP@ss1",
            full_name="John Doe",
        )
        assert req.email == "test@example.com"
        assert req.password == "SecureP@ss1"
        assert req.full_name == "John Doe"

    def test_invalid_email(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="not-an-email", password="12345678", full_name="Name")
        assert "email" in str(exc_info.value).lower()

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="short", full_name="Name")

    def test_password_min_length_boundary(self):
        """Exactly 8 characters should be accepted."""
        req = RegisterRequest(email="a@b.com", password="12345678", full_name="Name")
        assert len(req.password) == 8

    def test_password_max_length(self):
        """128 characters should be accepted, 129 should fail."""
        req = RegisterRequest(email="a@b.com", password="a" * 128, full_name="Name")
        assert len(req.password) == 128

        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="a" * 129, full_name="Name")

    def test_full_name_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="12345678", full_name="X")

    def test_full_name_max_length(self):
        req = RegisterRequest(email="a@b.com", password="12345678", full_name="A" * 100)
        assert len(req.full_name) == 100

        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="12345678", full_name="A" * 101)

    def test_missing_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(password="12345678", full_name="Name")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", full_name="Name")


class TestLoginRequest:
    def test_valid_login(self):
        req = LoginRequest(email="user@test.com", password="mypassword")
        assert req.email == "user@test.com"
        assert req.password == "mypassword"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="mypassword")


class TestRefreshRequest:
    def test_valid_refresh(self):
        req = RefreshRequest(refresh_token="some-jwt-token")
        assert req.refresh_token == "some-jwt-token"

    def test_missing_token(self):
        with pytest.raises(ValidationError):
            RefreshRequest()


class TestTokenResponse:
    def test_defaults(self):
        resp = TokenResponse(access_token="at", refresh_token="rt")
        assert resp.token_type == "bearer"
        assert resp.expires_in == 1800

    def test_custom_values(self):
        resp = TokenResponse(
            access_token="at", refresh_token="rt",
            token_type="bearer", expires_in=900,
        )
        assert resp.expires_in == 900


class TestUserResponse:
    def test_from_attributes(self):
        """UserResponse should support orm_mode / from_attributes."""
        assert UserResponse.model_config.get("from_attributes") is True

    def test_valid_user_response(self):
        resp = UserResponse(
            id=uuid.uuid4(),
            email="user@test.com",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(),
        )
        assert resp.is_active is True


class TestLogoutResponse:
    def test_default_message(self):
        resp = LogoutResponse()
        assert "logged out" in resp.message.lower()
