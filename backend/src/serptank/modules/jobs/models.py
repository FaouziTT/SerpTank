"""Background jobs: the tenant-visible record of long-running work (plan §4.4).

Celery (or the in-process runner in development) only transports *which* job to run;
all state - status, progress, counters, user-safe errors - lives in this table so
customers can see progress and history, and Redis is never a source of truth.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum_values,
)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATUSES = frozenset({JobStatus.QUEUED, JobStatus.RUNNING})
TERMINAL_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED})

job_status_enum = Enum(JobStatus, name="job_status", values_callable=pg_enum_values)


class Job(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # At most one active job of a kind per project (e.g. one crawl at a time).
        Index(
            "uq_jobs_active_per_project",
            "project_id",
            "kind",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running') AND project_id IS NOT NULL"),
        ),
        Index("ix_jobs_org_created", "organization_id", "created_at"),
    )

    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        job_status_enum, nullable=False, default=JobStatus.QUEUED
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stage: Mapped[str | None] = mapped_column(String(50))
    counters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Stable machine code + message written for end users (never exception text).
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
