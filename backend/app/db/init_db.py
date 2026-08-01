"""Database initialization — create tables and seed a default owner.

Called once at application startup (see ``app/main.py`` lifespan).
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import UserRole
from app.db.session import AsyncSessionLocal, Base, engine
from app.models import User  # noqa: F401 — ensure all models are loaded
from app.services.auth_service import get_user_by_email, hash_password

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables (if missing) and seed the default owner account.

    Safe to call repeatedly — the owner seed is idempotent.
    """

    # -- 1. Create tables ----------------------------------------------------
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not already present).")

    # -- 2. Seed default owner account ---------------------------------------
    async with AsyncSessionLocal() as session:
        await _seed_default_owner(session)
        await session.commit()

    logger.info("Database initialization complete.")


async def _seed_default_owner(session: AsyncSession) -> None:
    """Create the default owner account if it does not already exist."""

    email = settings.DEFAULT_OWNER_EMAIL.lower().strip()
    existing = await get_user_by_email(session, email)

    if existing is not None:
        logger.debug("Default owner already exists (id=%d).", existing.id)
        return

    from app.models.user import User

    user = User(
        email=email,
        hashed_password=hash_password(settings.DEFAULT_OWNER_PASSWORD),
        display_name="Default Owner",
        role=UserRole.OWNER,
        is_active=True,
    )
    session.add(user)
    logger.info(
        "Seeded default owner: email=%s role=%s (change password immediately!).",
        email,
        UserRole.OWNER,
    )
