"""SQLAlchemy async engine, session factory, and declarative Base.

All models inherit from ``Base``.  Every database interaction goes through
the async session returned by ``get_session``.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ---------------------------------------------------------------------------
# Async Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    # SQLite-specific: allow multi-threaded access (required for aiosqlite)
    connect_args={"check_same_thread": False},
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency – yields a session and closes it after the request
# ---------------------------------------------------------------------------
async def get_session() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that provides an async database session.

    Usage in a router::

        from fastapi import Depends
        from app.db.session import get_session

        @router.get("/agents")
        async def list_agents(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
