"""
PubMedIQ — Password Hashing (Argon2)

Uses argon2-cffi (Argon2id variant) — the winner of the Password Hashing
Competition and the recommended algorithm for new systems.

Responsibilities:
  - hash(plain)         → hashed string stored in DB
  - verify(plain, hash) → boolean result for login

This module has NO database awareness.
"""
from __future__ import annotations

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

# Argon2id parameters (OWASP recommended minimums for 2024)
_hasher = _Argon2Hasher(
    time_cost=3,       # number of iterations
    memory_cost=65536, # 64 MB
    parallelism=1,     # threads
    hash_len=32,       # output length in bytes
    salt_len=16,       # salt length in bytes
)


class PasswordHasher:
    """
    Argon2id password hashing service.

    Usage:
        hasher = PasswordHasher()
        hashed = hasher.hash("my-secret-password")
        ok = hasher.verify("my-secret-password", hashed)  # True
    """

    def hash(self, plain_password: str) -> str:
        """
        Hash a plain-text password using Argon2id.

        Args:
            plain_password: The raw password string.

        Returns:
            The Argon2 hash string (includes salt + parameters).

        Raises:
            RuntimeError: If hashing fails unexpectedly.
        """
        try:
            return _hasher.hash(plain_password)
        except HashingError as e:
            logger.error("password_hash_failed", error=str(e))
            raise RuntimeError("Password hashing failed.") from e

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain-text password against a stored Argon2 hash.

        Args:
            plain_password: The raw password to check.
            hashed_password: The stored hash from the database.

        Returns:
            True if the password matches, False otherwise.
        """
        try:
            return _hasher.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            # Password does not match — not an error
            return False
        except (VerificationError, InvalidHashError) as e:
            logger.warning("password_verify_error", error=str(e))
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if the stored hash was created with outdated Argon2 parameters.
        Use this to transparently upgrade hashes on login.

        Args:
            hashed_password: The stored hash to check.

        Returns:
            True if the hash should be rehashed with current parameters.
        """
        return _hasher.check_needs_rehash(hashed_password)


# ---------------------------------------------------------------------------
# Module-level singleton — import this wherever password operations are needed
# ---------------------------------------------------------------------------
password_hasher = PasswordHasher()
