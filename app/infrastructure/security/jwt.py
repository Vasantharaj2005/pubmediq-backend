"""
PubMedIQ — JWT Service

Responsible ONLY for token operations:
  - create_access_token()
  - create_refresh_token()
  - decode_token()
  - validate_token()

This module has NO database queries.
All DB interaction is in UserRepository and AuthService.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.core.config import settings
from app.core.constants import TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH
from app.core.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenData:
    """Decoded and validated JWT payload."""

    def __init__(
        self,
        user_id: str,
        email: str,
        token_type: str,
        jti: str,
        exp: datetime,
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.token_type = token_type
        self.jti = jti        # JWT ID — used for blacklisting
        self.exp = exp


class JWTService:
    """
    JSON Web Token service for PubMedIQ.

    Architecture note:
      - Access tokens  → short-lived (30 min default), used for API calls
      - Refresh tokens → longer-lived (7 days default), used to get new access tokens

    The frontend sends:  Authorization: Bearer <access_token>
    """

    def __init__(self) -> None:
        self._secret = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._access_expire = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_expire = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        user_id: str,
        email: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a short-lived access token.

        Args:
            user_id: UUID string of the authenticated user.
            email: User's email (included for convenience, avoid sensitive data).
            extra_claims: Optional additional claims to embed.

        Returns:
            Signed JWT string.
        """
        now = datetime.now(tz=timezone.utc)
        expire = now + timedelta(minutes=self._access_expire)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "type": TOKEN_TYPE_ACCESS,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": expire,
        }
        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        logger.debug("access_token_created", user_id=user_id)
        return token

    def create_refresh_token(self, user_id: str, email: str) -> str:
        """
        Create a longer-lived refresh token.

        Args:
            user_id: UUID string of the authenticated user.
            email: User's email.

        Returns:
            Signed JWT string.
        """
        now = datetime.now(tz=timezone.utc)
        expire = now + timedelta(days=self._refresh_expire)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "type": TOKEN_TYPE_REFRESH,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": expire,
        }

        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        logger.debug("refresh_token_created", user_id=user_id)
        return token

    def decode_token(self, token: str) -> TokenData:
        """
        Decode and validate a JWT token.

        Args:
            token: The raw JWT string.

        Returns:
            TokenData with validated claims.

        Raises:
            TokenExpiredError: If the token has expired.
            TokenInvalidError: If the token signature or structure is invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTError as e:
            logger.warning("token_decode_failed", error=str(e))
            raise TokenInvalidError()

        user_id = payload.get("sub")
        email = payload.get("email")
        token_type = payload.get("type")
        jti = payload.get("jti")
        exp_ts = payload.get("exp")

        if not all([user_id, email, token_type, jti, exp_ts]):
            raise TokenInvalidError(detail="Token is missing required claims.")

        exp = datetime.fromtimestamp(exp_ts, tz=timezone.utc)

        return TokenData(
            user_id=user_id,
            email=email,
            token_type=token_type,
            jti=jti,
            exp=exp,
        )

    def validate_token(self, token: str, expected_type: str) -> TokenData:
        """
        Decode a token and assert it is of the expected type.

        Args:
            token: The raw JWT string.
            expected_type: 'access' or 'refresh'.

        Returns:
            Validated TokenData.

        Raises:
            TokenInvalidError: If the type does not match.
        """
        data = self.decode_token(token)

        if data.token_type != expected_type:
            raise TokenInvalidError(
                detail=f"Expected '{expected_type}' token, got '{data.token_type}'."
            )

        return data

    def get_token_jti(self, token: str) -> str:
        """
        Extract the JWT ID (jti) without full validation.
        Used to blacklist a token during logout.

        Args:
            token: The raw JWT string (may be expired).

        Returns:
            The jti claim string.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"verify_exp": False},  # allow expired tokens for logout
            )
            jti = payload.get("jti", "")
            if not jti:
                raise TokenInvalidError(detail="Token has no JTI claim.")
            return jti
        except JWTError:
            raise TokenInvalidError()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
jwt_service = JWTService()
