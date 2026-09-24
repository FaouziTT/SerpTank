"""Async database access (SQLAlchemy 2.0 + asyncpg).

Tenant isolation is enforced twice (docs/execution-plan.md §5.2):

1. In the application: repositories always filter by ``organization_id``.
2. In PostgreSQL: Row-Level Security policies compare ``organization_id`` with the
   transaction-local setting ``app.org_id``. :func:`set_tenant` sets it with
   ``set_config(..., is_local => true)`` so it can never leak to another request that
   reuses the pooled connection.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from serptank.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            # Fail fast instead of hanging requests; statement timeout guards runaway queries.
            "timeout": 5,
            "server_settings": {
                "application_name": "serptank-api",
                "statement_timeout": "30000",
                "idle_in_transaction_session_timeout": "60000",
            },
        },
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def set_tenant(session: AsyncSession, organization_id: uuid.UUID | None) -> None:
    """Bind the current transaction to a tenant for RLS (transaction-local)."""
    await session.execute(
        text("SELECT set_config('app.org_id', :org_id, true)"),
        {"org_id": str(organization_id) if organization_id else ""},
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, committed by the caller's service.

    The transaction is rolled back automatically if the request raises.
    """
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
