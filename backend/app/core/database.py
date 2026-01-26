"""
Database Configuration

Async SQLAlchemy setup for chat session persistence.
Supports both SQLite (local) and PostgreSQL (production).
"""

from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""
    pass


def _get_database_url() -> str:
    """Get the database URL, converting to async driver if needed."""
    db_url = settings.effective_database_url

    # Convert standard PostgreSQL URL to async version
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        # Railway uses postgres:// which is deprecated but still used
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    return db_url


def _ensure_db_directory():
    """Ensure the database directory exists for SQLite."""
    db_url = settings.effective_database_url
    if "sqlite" in db_url:
        # Extract path from sqlite URL (sqlite+aiosqlite:////path/to/db.db or sqlite+aiosqlite:///C:/path)
        if "////" in db_url:
            # Unix absolute path: sqlite+aiosqlite:////tmp/db.db
            db_path = db_url.split("////")[1]
        elif "///" in db_url:
            # Relative or Windows path: sqlite+aiosqlite:///./data/db.db or sqlite+aiosqlite:///C:/path
            db_path = db_url.split("///")[1]
        else:
            return

        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)


# Ensure directory exists for SQLite
_ensure_db_directory()

# Get the properly formatted database URL
DATABASE_URL = _get_database_url()

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database and create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
