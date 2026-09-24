"""Stored on-page analyses and content briefs (tenant-owned).

Only derived facts are kept: scores, checks, competitor headings and counts - never
competitor page bodies.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum_values,
)
from serptank.modules.crawler.models import CrawlStatus

# Reuse the crawl lifecycle (running / completed / failed / cancelled).
analysis_status_enum = Enum(CrawlStatus, name="analysis_status", values_callable=pg_enum_values)


class _Analysis(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_markets.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[CrawlStatus] = mapped_column(
        analysis_status_enum, nullable=False, default=CrawlStatus.RUNNING
    )
    error: Mapped[str | None] = mapped_column(String(200))


class PageOptimization(_Analysis, Base):
    __tablename__ = "page_optimizations"
    __table_args__ = (Index("ix_page_optimizations_project", "project_id", "created_at"),)

    url: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    # Analysis.to_json() plus the page/competitor summaries it was computed from.
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Optional LLM rewrite suggestions (schema-validated), generated on request.
    rewrite: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ContentBrief(_Analysis, Base):
    __tablename__ = "content_briefs"
    __table_args__ = (Index("ix_content_briefs_project", "project_id", "created_at"),)

    brief: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
