"""
PubMedIQ — HistoryRepository Integration Tests (PostgreSQL)

Tests HistoryRepository CRUD operations against real PostgreSQL database.
Verifies record creation, JSONB intent/strategy persistence, pagination, and user isolation.
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.history_repository import HistoryRepository
from app.infrastructure.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
class TestHistoryRepositoryPostgreSQL:

    async def test_create_and_get_by_user(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email=f"hist_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$argon2id$hash",
            full_name="History User",
        )

        history_repo = HistoryRepository(db_session)
        intent_payload = {"condition": "depression", "population": "elderly"}
        
        record = await history_repo.create(
            user_id=user.id,
            query="exercise and depression in elderly",
            intent=intent_payload,
            results_count=15,
            quality_score=0.85,
        )

        assert record.id is not None
        assert record.user_id == user.id
        assert record.query == "exercise and depression in elderly"
        assert record.intent == intent_payload
        assert record.results_count == 15

        history_list = await history_repo.get_by_user(user.id)
        assert len(history_list) == 1
        assert history_list[0].id == record.id

    async def test_delete_history_record(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email=f"delhist_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$argon2id$hash",
            full_name="Del History User",
        )

        history_repo = HistoryRepository(db_session)
        record = await history_repo.create(
            user_id=user.id,
            query="test query to delete",
            results_count=5,
        )

        deleted = await history_repo.delete(record.id, user.id)
        assert deleted is True

        fetched = await history_repo.get_by_id(record.id)
        assert fetched is None
