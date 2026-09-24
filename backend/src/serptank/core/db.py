"""Async database access (SQLAlchemy 2.0 + asyncpg) and tenant binding for RLS.

Tenant isolation is enforced twice (docs/execution-plan.md §5.2):

1. **Application:** tenant repositories always filter by ``organization_id``
   (:mod:`serptank.core.repository`).
2. **PostgreSQL Row-Level Security:** policies compare rows with the transaction-local
   settings ``app.org_id`` and ``app.user_id``. The API connects as the non-owner role
   ``serptank_app`` (no ``BYPASSRLS``), and every table has ``FORCE ROW LEVEL SECURITY``.

Binding
-------
:func:`bind_identity` stores the current user/org on the session. An ``after_begin``
listener re-applies them with ``set_config(..., is_local => true)`` at the start of
**every** transaction on that session, so values survive commits within a request but
can never leak to another request that reuses the pooled connection.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, SessionTransaction

from serptank.core.config import Settings

_ORG_KEY = "serptank.org_id"
_USER_KEY = "serptank.user_id"
_SET_GUCS = text(
    "SELECT set_config('app.org_id', :org_id, true), set_config('app.user_id', :user_id, true)"
)


def create_engine(settings: Settings, *, application_name: str = "serptank-api") -> AsyncEngine:
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
                "application_name": application_name,
                "statement_timeout": "30000",
                "idle_in_transaction_session_timeout": "60000",
            },
        },
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


def _guc_params(session: Session) -> dict[str, str]:
    org_id = session.info.get(_ORG_KEY)
    user_id = session.info.get(_USER_KEY)
    return {"org_id": str(org_id) if org_id else "", "user_id": str(user_id) if user_id else ""}


@event.listens_for(Session, "after_begin")
def _apply_identity_gucs(session: Session, _tx: SessionTransaction, connection: Connection) -> None:
    connection.execute(_SET_GUCS, _guc_params(session))


async def bind_identity(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
) -> None:
    """Bind the acting user and/or tenant to ``session`` (applies immediately)."""
    if user_id is not None:
        session.info[_USER_KEY] = user_id
    if organization_id is not None:
        session.info[_ORG_KEY] = organization_id
    if session.in_transaction():
        await session.execute(_SET_GUCS, _guc_params(session.sync_session))


def bound_organization_id(session: AsyncSession) -> uuid.UUID | None:
    value: Any = session.info.get(_ORG_KEY)
    return value if isinstance(value, uuid.UUID) else None


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request.

    Services commit explicitly (so a failed commit becomes an error response, never a
    silent failure after a 200). Anything uncommitted is rolled back on exit.
    """
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()
