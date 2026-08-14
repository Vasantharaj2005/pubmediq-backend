"""
PubMedIQ — API Test Configuration

Provides a FastAPI TestClient with dependency overrides so that
API tests never hit real databases, Redis, or external services.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.security.jwt import JWTService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db_session():
    """Mock async DB session for dependency override."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def jwt_svc() -> JWTService:
    return JWTService()


@pytest.fixture
def test_user() -> UserModel:
    """A realistic UserModel mock for auth dependency injection."""
    user = MagicMock(spec=UserModel)
    user.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    user.email = "test@pubmediq.com"
    user.full_name = "Test User"
    user.is_active = True
    user.is_verified = False
    user.password_hash = "$argon2id$test"
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.last_login_at = None
    return user


@pytest.fixture
def auth_token(jwt_svc, test_user) -> str:
    """A valid JWT access token for test_user."""
    return jwt_svc.create_access_token(
        user_id=str(test_user.id),
        email=test_user.email,
    )


@pytest.fixture
def auth_headers(auth_token) -> dict[str, str]:
    """Authorization headers with a valid Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def app(mock_db_session, test_user):
    """
    Create a FastAPI app with dependency overrides.
    All external dependencies are mocked.
    """
    # Patch external services BEFORE importing the app
    with (
        patch("app.infrastructure.cache.redis_client.redis_client") as mock_redis,
        patch("app.infrastructure.vectorstore.pinecone_client.pinecone_client") as mock_pinecone,
        patch("app.infrastructure.security.token_blacklist.token_blacklist") as mock_blacklist,
    ):
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.is_available = True
        mock_pinecone.ping = AsyncMock(return_value=True)
        mock_blacklist.is_blacklisted = AsyncMock(return_value=False)
        mock_blacklist.add = AsyncMock()

        from app.main import create_app

        application = create_app()

        # Override DB dependency
        async def override_get_db():
            yield mock_db_session

        application.dependency_overrides[get_db] = override_get_db

        yield application

        application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """Async HTTP client for making requests to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
