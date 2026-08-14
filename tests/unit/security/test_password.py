"""
Tests for app.infrastructure.security.password

Verifies Argon2id hashing, verification, and needs_rehash logic.
No external dependencies needed — pure cryptographic operations.
"""
from __future__ import annotations

import pytest

from app.infrastructure.security.password import PasswordHasher


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher()


class TestPasswordHashing:
    def test_hash_returns_string(self, hasher):
        hashed = hasher.hash("mypassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_not_plaintext(self, hasher):
        password = "mypassword"
        hashed = hasher.hash(password)
        assert hashed != password

    def test_hash_contains_argon2_marker(self, hasher):
        """Argon2 hashes start with $argon2."""
        hashed = hasher.hash("testpassword")
        assert hashed.startswith("$argon2")

    def test_different_salts(self, hasher):
        """Same password should produce different hashes (random salt)."""
        h1 = hasher.hash("samepassword")
        h2 = hasher.hash("samepassword")
        assert h1 != h2


class TestPasswordVerification:
    def test_verify_correct_password(self, hasher):
        password = "CorrectHorse42!"
        hashed = hasher.hash(password)
        assert hasher.verify(password, hashed) is True

    def test_verify_wrong_password(self, hasher):
        hashed = hasher.hash("CorrectPassword")
        assert hasher.verify("WrongPassword", hashed) is False

    def test_verify_empty_password(self, hasher):
        hashed = hasher.hash("notempty")
        assert hasher.verify("", hashed) is False

    def test_verify_corrupted_hash(self, hasher):
        """Corrupted hash should return False, not raise."""
        assert hasher.verify("password", "not-a-valid-hash") is False

    def test_verify_empty_hash(self, hasher):
        """Empty hash should return False, not raise."""
        assert hasher.verify("password", "") is False


class TestNeedsRehash:
    def test_fresh_hash_does_not_need_rehash(self, hasher):
        """A hash created with current params should not need rehash."""
        hashed = hasher.hash("testpassword")
        assert hasher.needs_rehash(hashed) is False
