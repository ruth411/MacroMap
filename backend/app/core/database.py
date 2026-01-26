"""
Database Configuration

Async SQLAlchemy setup for chat session persistence.
"""

from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""
    pass


def _ensure_db_directory():
    """Ensure the database directory exists for SQLite."""
    db_url = settings.database_url
    if "sqlite" in db_url:
        # Extract path from sqlite URL (sqlite+aiosqlite:////path/to/db.db)
        # The path starts after the third or fourth slash
        if "////" in db_url:
            # Absolute path: sqlite+aiosqlite:////tmp/db.db
            db_path = db_url.split("////")[1]
        elif "///" in db_url:
            # Relative path: sqlite+aiosqlite:///./data/db.db
            db_path = db_url.split("///")[1]
        else:
            return

        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)


# Ensure directory exists before creating engine
_ensure_db_directory()

# Create async engine
engine = create_async_engine(
    settings.database_url,
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
