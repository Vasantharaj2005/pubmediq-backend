"""
PubMedIQ — Auth Flow Integration Test (PostgreSQL)

End-to-end testing of AuthService + UserRepository + JWT + PasswordHasher
against a real PostgreSQL database.
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth_service import AuthService
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt import JWTService
from app.infrastructure.security.password import PasswordHasher
from app.infrastructure.security.token_blacklist import TokenBlacklist
from app.schemas.auth import RegisterRequest, LoginRequest


@pytest.mark.asyncio
class TestAuthFlowPostgreSQL:

    async def test_full_auth_lifecycle(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        password_hasher = PasswordHasher()
        jwt_service = JWTService()
        token_blacklist = TokenBlacklist(redis_client=AsyncMock())

        auth_service = AuthService(
            db=db_session,
            hasher=password_hasher,
            jwt=jwt_service,
        )

        email = f"authflow_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePassword123!"

        # 1. Register user
        reg_req = RegisterRequest(
            email=email,
            password=password,
            full_name="Auth Flow User",
        )
        token_resp = await auth_service.register(reg_req)
        assert token_resp.access_token is not None
        assert token_resp.refresh_token is not None

        # 2. Login user
        login_req = LoginRequest(email=email, password=password)
        login_resp = await auth_service.login(login_req)
        assert login_resp.access_token is not None

        # 3. Decode access token
        token_data = jwt_service.decode_token(login_resp.access_token)
        assert token_data.email == email
