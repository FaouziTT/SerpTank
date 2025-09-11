"""
Database initialization script.

This module provides functions to initialize the database with default data.
"""
import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.auth.core.security import get_password_hash
from app.db.session import async_session_factory
from app.models.user import User

logger = logging.getLogger(__name__)


async def create_first_superuser(db: AsyncSession) -> None:
    """
    Create the first superuser if it doesn't exist.
    
    Args:
        db: Database session
    """    # Check if superuser already exists
    result = await db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": settings.FIRST_SUPERUSER_EMAIL},    )
    user = result.scalar_one_or_none()
    
    if user:
        logger.info("Superuser already exists")
        return
    
    # Create superuser using SQL to avoid relationship configuration issues
    hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
    await db.execute(
        text("""
            INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser, created_at, updated_at)
            VALUES (:email, :hashed_password, :full_name, :is_active, :is_superuser, NOW(), NOW())
        """),
        {
            "email": settings.FIRST_SUPERUSER_EMAIL,
            "hashed_password": hashed_password,
            "full_name": "Admin User",
            "is_active": True,
            "is_superuser": True,
        },
    )
    await db.commit()
    
    logger.info(f"Superuser {settings.FIRST_SUPERUSER_EMAIL} created")


async def init_db() -> None:
    """
    Initialize the database with default data.
    """
    async with async_session_factory() as db:
        await create_first_superuser(db)


if __name__ == "__main__":
    asyncio.run(init_db())