"""Search data storage.

Global (not tenant-owned, no ``organization_id``):

* ``serp_snapshots`` - public SERPs, one per (engine, query, locale, device, day). The
  cache never records *who* asked: which keywords a customer tracks lives only in
  tenant tables (plan §5.2 "provider cache isolation").
* ``keyword_metrics`` - public keyword volumes/CPC from official or vendor sources.
* ``vendor_usage`` - daily request counts per vendor/engine (budgets, cost model).
* ``serp_validations`` - cross-vendor agreement samples.

Tenant-owned (RLS): tracked keywords, competitors, rank observations, SERP usage.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, uuid7


class SerpSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "serp_snapshots"
    __table_args__ = (
        Index(
            "uq_serp_snapshots_key",
            "engine",
            "query",
            "country",
            "language",
            text("coalesce(location, '')"),
            "device",
            "fetched_on",
            unique=True,
        ),
    )

    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    language: Mapped[str] = mapped_column(String(35), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    device: Mapped[str] = mapped_column(String(10), nullable=False)
    fetched_on: Mapped[date] = mapped_column(Date, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    vendor: Mapped[str] = mapped_column(String(30), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class KeywordMetrics(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "keyword_metrics"
    __table_args__ = (UniqueConstraint("keyword", "country", "language", "source"),)

    keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    language: Mapped[str] = mapped_column(String(35), nullable=False)
    source: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # google_ads | bing | dataforseo
    avg_monthly_searches: Mapped[int | None] = mapped_column(Integer)
    # Google returns ranges for accounts without spend; stored as-is (never made precise).
    volume_is_range: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    competition: Mapped[str | None] = mapped_column(String(20))
    cpc_low_micros: Mapped[int | None] = mapped_column(BigInteger)
    cpc_high_micros: Mapped[int | None] = mapped_column(BigInteger)
    monthly: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    fetched_on: Mapped[date] = mapped_column(Date, nullable=False)


class VendorUsage(Base):
    __tablename__ = "vendor_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    vendor: Mapped[str] = mapped_column(String(30), primary_key=True)
    engine: Mapped[str] = mapped_column(String(20), primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class SerpValidation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "serp_validations"

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    primary_vendor: Mapped[str] = mapped_column(String(30), nullable=False)
    secondary_vendor: Mapped[str] = mapped_column(String(30), nullable=False)
    top10_overlap: Mapped[float] = mapped_column(Float, nullable=False)  # Jaccard of domains
    agreed: Mapped[bool] = mapped_column(Boolean, nullable=False)


class TrackedKeyword(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "tracked_keywords"
    __table_args__ = (UniqueConstraint("market_id", "keyword"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_markets.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(String(300), nullable=False)  # normalized
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False, default=list)
    target_url: Mapped[str | None] = mapped_column(Text)


class Competitor(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("project_id", "domain"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120))


class RankObservation(TenantMixin, Base):
    """One position reading: own site (source gsc/bing/serp) or a competitor (serp)."""

    __tablename__ = "rank_observations"
    __table_args__ = (Index("ix_rank_obs_keyword_date", "keyword_id", "date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    keyword_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # gsc | bing | serp
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    is_own: Mapped[bool] = mapped_column(Boolean, nullable=False)
    position: Mapped[float | None] = mapped_column(Float)  # None = not in the checked depth
    url: Mapped[str | None] = mapped_column(Text)
    features: Mapped[list[str]] = mapped_column(ARRAY(String(40)), nullable=False, default=list)
    ai_cited: Mapped[bool | None] = mapped_column(Boolean)
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class SerpUsage(Base):
    """Paid SERP fetches attributed to an org (cache hits are free and not counted)."""

    __tablename__ = "serp_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
