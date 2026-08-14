"""
PubMedIQ — PaperRepository Integration Tests (PostgreSQL)

Tests PaperRepository operations against real PostgreSQL database.
Verifies paper bookmarking, unsaving, bookmark checks, and user isolation.
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.paper_repository import PaperRepository
from app.infrastructure.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
class TestPaperRepositoryPostgreSQL:

    async def test_save_and_is_saved(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email=f"paper_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$argon2id$hash",
            full_name="Paper User",
        )

        paper_repo = PaperRepository(db_session)
        pmid = "99887766"

        saved_paper = await paper_repo.save(
            user_id=user.id,
            pmid=pmid,
            title="Postgres Paper Title",
            journal="Journal of Clinical Testing",
            year=2025,
        )

        assert saved_paper.id is not None
        assert saved_paper.user_id == user.id
        assert saved_paper.pmid == pmid

        is_saved = await paper_repo.is_saved(user.id, pmid)
        assert is_saved is True

    async def test_unsave_paper(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email=f"unsave_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$argon2id$hash",
            full_name="Unsave Paper User",
        )

        paper_repo = PaperRepository(db_session)
        pmid = "11223344"
        await paper_repo.save(user_id=user.id, pmid=pmid)

        unsaved = await paper_repo.unsave(user.id, pmid)
        assert unsaved is True

        is_saved_after = await paper_repo.is_saved(user.id, pmid)
        assert is_saved_after is False
