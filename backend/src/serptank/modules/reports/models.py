"""Exports, alert rules and in-app notifications (all tenant-owned)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Export(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """A generated CSV, kept for 24 hours and downloaded through a signed link."""

    __tablename__ = "exports"
    __table_args__ = (Index("ix_exports_project_created", "project_id", "created_at"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    rows: Mapped[int | None] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    content: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(200))


class AlertRule(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """One alert kind per project (enabled, threshold, email on/off)."""

    __tablename__ = "alert_rules"
    __table_args__ = (UniqueConstraint("project_id", "kind"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    threshold: Mapped[float | None] = mapped_column(Float)
    email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """An in-app notification for one member. ``dedupe_key`` makes alerts idempotent."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    link: Mapped[str | None] = mapped_column(String(300))
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
