"""
PubMedIQ — User Repository

All database operations for the users table.
Services MUST use this repository — they must NOT write raw SQL.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.user import UserModel

logger = get_logger(__name__)


class UserRepository:
    """Repository for user CRUD operations."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: str | uuid.UUID) -> UserModel | None:
        """Fetch a user by UUID primary key."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        result = await self._db.execute(
            select(UserModel).where(UserModel.id == uid)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserModel | None:
        """Fetch a user by email address (case-insensitive)."""
        result = await self._db.execute(
            select(UserModel).where(
                UserModel.email == email.lower().strip()
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        full_name: str,
    ) -> UserModel:
        """
        Create and persist a new user.

        Args:
            email: Validated email address.
            password_hash: Argon2 hash (never plain-text).
            full_name: Display name.

        Returns:
            Persisted UserModel with generated UUID.
        """
        user = UserModel(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name,
        )
        self._db.add(user)
        await self._db.flush()  # get the ID without committing
        await self._db.refresh(user)
        logger.info("user_created", user_id=str(user.id), email=email)
        return user

    async def update_last_login(self, user_id: str | uuid.UUID) -> None:
        """Record the timestamp of a successful login."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        await self._db.execute(
            update(UserModel)
            .where(UserModel.id == uid)
            .values(last_login_at=datetime.now(tz=timezone.utc))
        )

    async def update_profile(
        self,
        user_id: str | uuid.UUID,
        full_name: str | None = None,
    ) -> UserModel | None:
        """Update mutable user profile fields."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        values: dict = {}
        if full_name is not None:
            values["full_name"] = full_name
        if not values:
            return await self.get_by_id(uid)

        await self._db.execute(
            update(UserModel).where(UserModel.id == uid).values(**values)
        )
        return await self.get_by_id(uid)

    async def deactivate(self, user_id: str | uuid.UUID) -> None:
        """Soft-delete a user by setting is_active = False."""
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        await self._db.execute(
            update(UserModel).where(UserModel.id == uid).values(is_active=False)
        )
