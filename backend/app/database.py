"""Database configuration and session management."""

from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.SQL_ECHO,
    future=True,
)

# Create async session factory
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_maker() as session:
        yield session


#: Arbitrary constant naming the schema-creation advisory lock.
SCHEMA_LOCK_KEY = 7731


async def init_db(target: Optional[AsyncEngine] = None) -> None:
    """Create any missing tables.

    Every web worker runs this at startup. On PostgreSQL concurrent ``CREATE TABLE`` calls race
    (one wins, the others fail with a duplicate-type error), so they take an advisory lock first.
    """
    async with (target or engine).begin() as conn:
        if conn.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SCHEMA_LOCK_KEY})
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
