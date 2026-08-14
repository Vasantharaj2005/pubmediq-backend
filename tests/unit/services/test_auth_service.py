"""
Tests for app.application.services.auth_service

Verifies the AuthService orchestration with ALL dependencies mocked:
  - UserRepository
  - PasswordHasher
  - JWTService
  - TokenBlacklist
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    InvalidCredentialsError,
    TokenBlacklistedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.application.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, RegisterRequest


def _make_user_model(
    user_id=None, email="test@example.com", password_hash="$argon2...",
    full_name="Test User", is_active=True,
):
    """Create a mock UserModel."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.password_hash = password_hash
    user.full_name = full_name
    user.is_active = is_active
    return user


@pytest.fixture
def mock_hasher():
    hasher = MagicMock()
    hasher.hash.return_value = "$argon2id$hashed"
    hasher.verify.return_value = True
    hasher.needs_rehash.return_value = False
    return hasher


@pytest.fixture
def mock_jwt():
    jwt = MagicMock()
    jwt.create_access_token.return_value = "access-token-123"
    jwt.create_refresh_token.return_value = "refresh-token-456"
    jwt.validate_token.return_value = MagicMock(
        user_id="uid", email="test@example.com",
        token_type="refresh", jti="jti-1",
        exp=datetime.now(tz=timezone.utc) + timedelta(days=7),
    )
    jwt.get_token_jti.return_value = "jti-abc"
    return jwt


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def auth_service(mock_db, mock_hasher, mock_jwt):
    return AuthService(db=mock_db, hasher=mock_hasher, jwt=mock_jwt)


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, auth_service, mock_db):
        new_user = _make_user_model()

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=new_user)

            request = RegisterRequest(
                email="new@example.com", password="password123", full_name="New User"
            )
            result = await auth_service.register(request)

        assert result.access_token == "access-token-123"
        assert result.refresh_token == "refresh-token-456"
        assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service):
        existing_user = _make_user_model()

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=existing_user)

            request = RegisterRequest(
                email="existing@example.com", password="password123", full_name="Name"
            )
            with pytest.raises(UserAlreadyExistsError):
                await auth_service.register(request)


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_hasher):
        user = _make_user_model(is_active=True)

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)
            mock_repo.update_last_login = AsyncMock()

            request = LoginRequest(email="test@example.com", password="correct")
            result = await auth_service.login(request)

        assert result.access_token == "access-token-123"
        mock_hasher.verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service):
        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=None)

            request = LoginRequest(email="nope@example.com", password="pass")
            with pytest.raises(InvalidCredentialsError):
                await auth_service.login(request)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_service, mock_hasher):
        user = _make_user_model()
        mock_hasher.verify.return_value = False

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)

            request = LoginRequest(email="test@example.com", password="wrong")
            with pytest.raises(InvalidCredentialsError):
                await auth_service.login(request)

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, auth_service, mock_hasher):
        user = _make_user_model(is_active=False)

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)

            request = LoginRequest(email="test@example.com", password="correct")
            with pytest.raises(InvalidCredentialsError):
                await auth_service.login(request)

    @pytest.mark.asyncio
    async def test_login_triggers_rehash(self, auth_service, mock_hasher):
        """When needs_rehash=True, login should rehash the password."""
        user = _make_user_model(is_active=True)
        mock_hasher.needs_rehash.return_value = True

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)
            mock_repo.update_last_login = AsyncMock()
            mock_repo.update_profile = AsyncMock()

            request = LoginRequest(email="test@example.com", password="pass")
            await auth_service.login(request)

        mock_hasher.hash.assert_called_once()


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, auth_service, mock_jwt):
        user = _make_user_model(is_active=True)

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=user)
            with patch("app.application.services.auth_service.token_blacklist") as mock_bl:
                mock_bl.is_blacklisted = AsyncMock(return_value=False)
                mock_bl.add = AsyncMock()

                result = await auth_service.refresh("refresh-token")

        assert result.access_token == "access-token-123"

    @pytest.mark.asyncio
    async def test_refresh_blacklisted_token(self, auth_service):
        with patch("app.application.services.auth_service.token_blacklist") as mock_bl:
            mock_bl.is_blacklisted = AsyncMock(return_value=True)

            with pytest.raises(TokenBlacklistedError):
                await auth_service.refresh("blacklisted-token")

    @pytest.mark.asyncio
    async def test_refresh_user_not_found(self, auth_service):
        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)
            with patch("app.application.services.auth_service.token_blacklist") as mock_bl:
                mock_bl.is_blacklisted = AsyncMock(return_value=False)

                with pytest.raises(UserNotFoundError):
                    await auth_service.refresh("refresh-token")


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, auth_service, mock_jwt):
        with patch("app.application.services.auth_service.token_blacklist") as mock_bl:
            mock_bl.add = AsyncMock()
            await auth_service.logout("access-token")
            mock_bl.add.assert_called_once()


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, auth_service):
        user = _make_user_model()
        user.created_at = datetime.now(tz=timezone.utc)

        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=user)
            result = await auth_service.get_current_user(str(user.id))

        assert result.email == user.email

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, auth_service):
        with patch.object(auth_service, "_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(UserNotFoundError):
                await auth_service.get_current_user("nonexistent-id")
