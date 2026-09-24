"""Crawl results: one row per crawl, per fetched URL, and per internal link.

Only extracted facts are stored (titles, directives, counts, fingerprints) - never full
page HTML - which keeps storage bounded and avoids hoarding customer content.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum_values,
)


class CrawlStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


crawl_status_enum = Enum(CrawlStatus, name="crawl_status", values_callable=pg_enum_values)


class Crawl(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "crawls"
    __table_args__ = (Index("ix_crawls_project_created", "project_id", "created_at"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    status: Mapped[CrawlStatus] = mapped_column(
        crawl_status_enum, nullable=False, default=CrawlStatus.RUNNING
    )
    start_url: Mapped[str] = mapped_column(Text, nullable=False)
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    # False = shallow crawl of an unverified domain.
    domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Engines whose deltas are audited (the project's tracked engines at crawl time).
    engines: Mapped[list[str]] = mapped_column(ARRAY(String(20)), nullable=False, default=list)
    pages_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    budget_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    render_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Site-level facts gathered during the crawl (robots, sitemaps, probes, samples).
    site: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    score: Mapped[float | None] = mapped_column(Float)
    issue_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CrawlPage(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "crawl_pages"
    __table_args__ = (UniqueConstraint("crawl_id", "url"),)

    crawl_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int | None] = mapped_column(Integer)
    found_via: Mapped[str] = mapped_column(String(20), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(40))
    content_type: Mapped[str | None] = mapped_column(String(100))
    response_ms: Mapped[int | None] = mapped_column(Integer)
    bytes: Mapped[int | None] = mapped_column(Integer)
    redirect_to: Mapped[str | None] = mapped_column(Text)
    in_sitemap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_google: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_bing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    indexable_google: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    indexable_bing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    title: Mapped[str | None] = mapped_column(String(500))
    canonical: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    simhash: Mapped[int | None] = mapped_column(BigInteger)
    inlinks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    x_robots: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Differences found by JS rendering / mobile re-fetch for sampled pages.
    rendered: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    mobile: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class CrawlLink(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "crawl_links"
    __table_args__ = (Index("ix_crawl_links_target", "crawl_id", "target_url"),)

    crawl_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawls.id", ondelete="CASCADE"), nullable=False
    )
    source_page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawl_pages.id", ondelete="CASCADE"), nullable=False
    )
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    internal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    nofollow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anchor: Mapped[str] = mapped_column(String(200), nullable=False, default="")
