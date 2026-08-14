"""
PubMedIQ — Integration Test Configuration

Integration tests verify interactions between 2+ modules against real database tables.
Uses real PostgreSQL connection via asyncpg with automatic per-test transaction rollback.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.infrastructure.database.connection import Base
from app.infrastructure.database.models import (  # noqa: F401
    FeedbackModel,
    SavedPaperModel,
    SearchHistoryModel,
    UserModel,
)


@pytest.fixture
def test_engine() -> AsyncEngine:
    """Async engine targeting PostgreSQL test database."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    return engine


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session fixture for integration tests.
    Each test runs inside a transaction and rolls back automatically.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    connection = await test_engine.connect()
    transaction = await connection.begin()
    
    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    async with session_factory() as session:
        yield session

    await transaction.rollback()
    await connection.close()
    await test_engine.dispose()

