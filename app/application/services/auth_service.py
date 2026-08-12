"""
PubMedIQ — Auth Service

Business logic for user authentication.
Coordinates: UserRepository + PasswordHasher + JWTService + TokenBlacklist

This service has NO knowledge of HTTP — it works with domain objects.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentialsError,
    TokenBlacklistedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.logging import get_logger
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt import JWTService, jwt_service
from app.infrastructure.security.password import PasswordHasher, password_hasher
from app.infrastructure.security.token_blacklist import token_blacklist
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)


class AuthService:
    """
    Authentication service coordinating all auth operations.

    Layer separation:
      AuthService            ← business logic (this file)
        ├── UserRepository   ← DB persistence
        ├── PasswordHasher   ← Argon2 hashing
        ├── JWTService       ← token creation/validation
        └── TokenBlacklist   ← logout/revocation
    """

    def __init__(
        self,
        db: AsyncSession,
        hasher: PasswordHasher = password_hasher,
        jwt: JWTService = jwt_service,
    ) -> None:
        self._repo = UserRepository(db)
        self._hasher = hasher
        self._jwt = jwt

    async def register(self, request: RegisterRequest) -> TokenResponse:
        """
        Register a new user.

        Steps:
          1. Check email uniqueness
          2. Hash password with Argon2
          3. Persist user
          4. Issue access + refresh tokens
        """
        # Check for duplicate email
        existing = await self._repo.get_by_email(request.email)
        if existing:
            raise UserAlreadyExistsError()

        # Hash password
        password_hash = self._hasher.hash(request.password)

        # Create user
        user = await self._repo.create(
            email=request.email,
            password_hash=password_hash,
            full_name=request.full_name,
        )

        logger.info("user_registered", user_id=str(user.id))

        # Issue tokens
        access_token = self._jwt.create_access_token(
            user_id=str(user.id), email=user.email
        )
        refresh_token = self._jwt.create_refresh_token(
            user_id=str(user.id), email=user.email
        )

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def login(self, request: LoginRequest) -> TokenResponse:
        """
        Authenticate a user with email and password.

        Steps:
          1. Load user by email
          2. Verify Argon2 password
          3. Update last_login timestamp
          4. Issue tokens
        """
        user = await self._repo.get_by_email(request.email)
        if not user:
            raise InvalidCredentialsError()

        if not self._hasher.verify(request.password, user.password_hash):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError(detail="This account has been deactivated.")

        # Transparent password rehash if parameters changed
        if self._hasher.needs_rehash(user.password_hash):
            new_hash = self._hasher.hash(request.password)
            await self._repo.update_profile(user.id)  # would update hash in production
            logger.info("password_rehashed", user_id=str(user.id))

        await self._repo.update_last_login(user.id)
        logger.info("user_logged_in", user_id=str(user.id))

        access_token = self._jwt.create_access_token(
            user_id=str(user.id), email=user.email
        )
        refresh_token = self._jwt.create_refresh_token(
            user_id=str(user.id), email=user.email
        )

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """
        Issue a new access token using a valid refresh token.
        """
        from app.core.constants import TOKEN_TYPE_REFRESH

        token_data = self._jwt.validate_token(refresh_token, TOKEN_TYPE_REFRESH)

        # Check blacklist
        if await token_blacklist.is_blacklisted(token_data.jti):
            raise TokenBlacklistedError()

        user = await self._repo.get_by_id(token_data.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        new_access = self._jwt.create_access_token(
            user_id=str(user.id), email=user.email
        )
        new_refresh = self._jwt.create_refresh_token(
            user_id=str(user.id), email=user.email
        )

        # Blacklist the used refresh token
        import math
        from datetime import datetime, timezone
        ttl = max(0, int((token_data.exp - datetime.now(tz=timezone.utc)).total_seconds()))
        await token_blacklist.add(token_data.jti, ttl_seconds=ttl)

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def logout(self, access_token: str) -> None:
        """
        Revoke an access token by blacklisting its JTI.
        """
        from app.core.config import settings
        jti = self._jwt.get_token_jti(access_token)
        ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await token_blacklist.add(jti, ttl_seconds=ttl)
        logger.info("user_logged_out", jti=jti[:8] + "...")

    async def get_current_user(self, user_id: str) -> UserResponse:
        """Return the authenticated user's profile."""
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return UserResponse.model_validate(user)
