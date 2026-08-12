"""
PubMedIQ — core/security.py

This module is intentionally a thin facade.
All JWT, password hashing, and token blacklist logic lives in:

  infrastructure/security/jwt.py
  infrastructure/security/password.py
  infrastructure/security/token_blacklist.py

This file provides convenient re-exports so callers can import from
either location without creating circular dependencies.
"""
from __future__ import annotations

# Re-export for backwards compatibility / convenience
from app.infrastructure.security.jwt import JWTService, TokenData
from app.infrastructure.security.password import PasswordHasher
from app.infrastructure.security.token_blacklist import TokenBlacklist

__all__ = [
    "JWTService",
    "TokenData",
    "PasswordHasher",
    "TokenBlacklist",
]
