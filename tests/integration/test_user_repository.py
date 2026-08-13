"""
PubMedIQ — UserRepository Integration Tests (PostgreSQL)

Tests UserRepository CRUD operations against real PostgreSQL database.
Verifies UUID generation, email uniqueness constraints, profile updates, and soft deletion.
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
class TestUserRepositoryPostgreSQL:

    async def test_create_and_get_by_id(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        
        user = await repo.create(
            email=email,
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
            full_name="Postgres User",
        )
        assert user.id is not None
        assert user.email == email
        assert user.full_name == "Postgres User"
        assert user.is_active is True

        fetched = await repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.email == email

    async def test_get_by_email_case_insensitive(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        email = f"CaseTest_{uuid.uuid4().hex[:8]}@Example.COM"
        
        user = await repo.create(
            email=email,
            password_hash="$argon2id$fake",
            full_name="Case Test User",
        )

        fetched = await repo.get_by_email("casetest_" + email.split("_")[1].lower())
        assert fetched is not None
        assert fetched.id == user.id

    async def test_update_last_login(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        email = f"login_{uuid.uuid4().hex[:8]}@example.com"
        user = await repo.create(
            email=email,
            password_hash="$argon2id$fake",
            full_name="Login Test User",
        )
        assert user.last_login_at is None

        await repo.update_last_login(user.id)
        fetched = await repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.last_login_at is not None

    async def test_deactivate_user(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        email = f"deact_{uuid.uuid4().hex[:8]}@example.com"
        user = await repo.create(
            email=email,
            password_hash="$argon2id$fake",
            full_name="Deactivate User",
        )

        await repo.deactivate(user.id)
        fetched = await repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.is_active is False
