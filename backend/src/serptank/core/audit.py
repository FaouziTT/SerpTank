"""Append-only security audit log (OWASP A09:2025).

Rows are written by :func:`record_audit_event` and are **never updated or deleted** by
the application: the ``serptank_app`` role has only ``SELECT``/``INSERT`` on this table
(enforced in the migration). Org-scoped events are visible to that organization's
admins; user-level events (``organization_id IS NULL``, e.g. logins) only to that user.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.logging import redact
from serptank.core.models import Base, uuid7
from serptank.core.request_context import get_client_ip, get_request_id

_MAX_USER_AGENT = 300


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


def record_audit_event(
    session: AsyncSession,
    action: str,
    *,
    actor_user_id: uuid.UUID | None,
    organization_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Add an audit event to the session (committed with the surrounding transaction)."""
    event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        ip_address=get_client_ip() if get_client_ip() not in {None, "unknown"} else None,
        user_agent=(user_agent or "")[:_MAX_USER_AGENT] or None,
        request_id=get_request_id(),
        # Details go through the same redaction as logs: no secrets in the audit trail.
        details=redact(details or {}),
    )
    session.add(event)
    return event
