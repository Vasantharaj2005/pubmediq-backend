"""
PubMedIQ — FastAPI Authentication Dependencies

These are injectable FastAPI dependencies used to protect endpoints.
They form the bridge between HTTP auth headers and application services.

Usage:
    @router.get("/protected")
    async def endpoint(current_user = Depends(get_current_user)):
        ...
"""
from __future__ import annotations

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TOKEN_TYPE_ACCESS
from app.core.exceptions import (
    PermissionDeniedError,
    TokenBlacklistedError,
    UserNotFoundError,
)
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.jwt import jwt_service
from app.infrastructure.security.token_blacklist import token_blacklist

bearer_scheme = HTTPBearer(auto_error=True)
optional_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """
    Dependency: Extract and validate the Bearer token, return authenticated user.

    Flow:
      Authorization: Bearer <token>
        → decode_token()
        → check blacklist
        → UserRepository.get_by_id()
        → return UserModel

    Raises:
      TokenExpiredError, TokenInvalidError, TokenBlacklistedError, UserNotFoundError
    """
    token = credentials.credentials
    token_data = jwt_service.validate_token(token, TOKEN_TYPE_ACCESS)

    # Check blacklist (for logged-out tokens)
    if await token_blacklist.is_blacklisted(token_data.jti):
        raise TokenBlacklistedError()

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(token_data.user_id)
    if not user:
        raise UserNotFoundError()

    return user


async def require_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Dependency: Require an authenticated AND active user.

    Raises:
      PermissionDeniedError if the account is deactivated.
    """
    if not current_user.is_active:
        raise PermissionDeniedError(detail="Your account has been deactivated.")
    return current_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(optional_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserModel | None:
    """
    Dependency: Return the current user if authenticated, None otherwise.
    Used for endpoints that work for both anonymous and authenticated users.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials=credentials, db=db)
    except Exception:
        return None
