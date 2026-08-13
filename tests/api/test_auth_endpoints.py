"""
Tests for authentication endpoints

POST /api/v1/auth/register  → 201 / 409 / 422
POST /api/v1/auth/login     → 200 / 401 / 422
POST /api/v1/auth/refresh   → 200 / 401
POST /api/v1/auth/logout    → 200 / 401
GET  /api/v1/auth/me        → 200 / 401
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.schemas.auth import TokenResponse, UserResponse


@pytest.mark.asyncio
class TestRegisterEndpoint:
    async def test_register_success(self, client):
        token_resp = TokenResponse(
            access_token="at-new", refresh_token="rt-new",
        )
        with patch("app.api.v1.endpoints.auth.AuthService") as MockService:
            instance = MockService.return_value
            instance.register = AsyncMock(return_value=token_resp)

            resp = await client.post("/api/v1/auth/register", json={
                "email": "new@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
            })

        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client):
        with patch("app.api.v1.endpoints.auth.AuthService") as MockService:
            instance = MockService.return_value
            instance.register = AsyncMock(side_effect=UserAlreadyExistsError())

            resp = await client.post("/api/v1/auth/register", json={
                "email": "existing@example.com",
                "password": "SecurePass123",
                "full_name": "Name",
            })

        assert resp.status_code == 409
        data = resp.json()
        assert data["error"]["code"] == "USER_ALREADY_EXISTS"

    async def test_register_validation_error_short_password(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "short",
            "full_name": "Name",
        })
        assert resp.status_code == 422

    async def test_register_validation_error_bad_email(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass123",
            "full_name": "Name",
        })
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client):
        resp = await client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLoginEndpoint:
    async def test_login_success(self, client):
        token_resp = TokenResponse(
            access_token="at", refresh_token="rt",
        )
        with patch("app.api.v1.endpoints.auth.AuthService") as MockService:
            instance = MockService.return_value
            instance.login = AsyncMock(return_value=token_resp)

            resp = await client.post("/api/v1/auth/login", json={
                "email": "user@example.com",
                "password": "CorrectPassword",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_login_invalid_credentials(self, client):
        with patch("app.api.v1.endpoints.auth.AuthService") as MockService:
            instance = MockService.return_value
            instance.login = AsyncMock(side_effect=InvalidCredentialsError())

            resp = await client.post("/api/v1/auth/login", json={
                "email": "user@example.com",
                "password": "WrongPassword",
            })

        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_login_missing_password(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestRefreshEndpoint:
    async def test_refresh_success(self, client):
        token_resp = TokenResponse(
            access_token="new-at", refresh_token="new-rt",
        )
        with patch("app.api.v1.endpoints.auth.AuthService") as MockService:
            instance = MockService.return_value
            instance.refresh = AsyncMock(return_value=token_resp)

            resp = await client.post("/api/v1/auth/refresh", json={
                "refresh_token": "valid-refresh-token",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "new-at"

    async def test_refresh_missing_token(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={})
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestMeEndpoint:
    async def test_me_authenticated(self, client, auth_headers, test_user):
        with patch("app.api.v1.dependencies.UserRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_by_id = AsyncMock(return_value=test_user)

            resp = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name

    async def test_me_unauthenticated(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)
