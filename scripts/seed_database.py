"""
PubMedIQ — Database Seed Script

Creates all PostgreSQL tables via Alembic and optionally seeds test data.

Usage:
    python scripts/seed_database.py
    python scripts/seed_database.py --seed  # also create test user
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import configure_logging, get_logger
from app.infrastructure.database.connection import Base, async_engine
from app.infrastructure.database.models import (  # noqa: F401 - triggers model registration
    FeedbackModel, SavedPaperModel, SearchHistoryModel, UserModel,
)
from app.infrastructure.security.password import password_hasher

logger = get_logger(__name__)


async def create_tables() -> None:
    """Create all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")
    print("✅ Database tables created successfully.")


async def seed_test_user() -> None:
    """Create a test user for development."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.infrastructure.database.repositories.user_repository import UserRepository

    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        repo = UserRepository(session)

        existing = await repo.get_by_email("test@pubmediq.com")
        if existing:
            print("ℹ️  Test user already exists: test@pubmediq.com")
            return

        pw_hash = password_hasher.hash("testpassword123")
        user = await repo.create(
            email="test@pubmediq.com",
            password_hash=pw_hash,
            full_name="Test User",
        )
        await session.commit()
        print(f"✅ Test user created: test@pubmediq.com (id: {user.id})")
        print("   Password: testpassword123")


async def main(seed: bool = False) -> None:
    configure_logging()
    print("🔧 Setting up PubMedIQ database...")
    await create_tables()
    if seed:
        await seed_test_user()
    print("\n🎉 Database setup complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PubMedIQ Database Setup")
    parser.add_argument("--seed", action="store_true", help="Seed test data")
    args = parser.parse_args()
    asyncio.run(main(seed=args.seed))
