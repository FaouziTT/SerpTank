"""
Database session management.

This module provides functions and classes for managing database sessions
and connections using SQLAlchemy.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# These arguments tell the database driver (asyncpg) to expect
# and handle timezone information correctly at the connection level.
connect_args = {"server_settings": {"timezone": "utc"}}

# Create async engine
engine = create_async_engine(
    str(settings.get_database_uri()),
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args=connect_args, # ADD THIS LINE
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.

    Yields:
        AsyncSession: The database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise