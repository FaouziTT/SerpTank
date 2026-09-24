"""Integrations: per-organization connections, per-project data sources, synced data.

* :class:`Connection` - one per (organization, provider). Credentials (OAuth refresh
  tokens, API keys) are AES-GCM encrypted with the keyring; the associated data binds a
  ciphertext to its organization and provider, so it can't be replayed elsewhere.
* :class:`ProjectSource` - which property of a connection feeds which project (a GSC
  site, a GA4 property, a Bing site) and the project's IndexNow key.
* Daily metrics tables are TimescaleDB hypertables (time-partitioned). Syncs are
  idempotent: a date range is replaced, never appended twice.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Date,
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
    uuid7,
)


class Provider(StrEnum):
    GOOGLE = "google"  # Search Console, GA4, Google Ads (one OAuth grant, incremental scopes)
    BING = "bing"  # Bing Webmaster Tools (API key)


class ConnectionStatus(StrEnum):
    ACTIVE = "active"
    ERROR = "error"  # last call failed; retried later
    REAUTH_REQUIRED = "reauth_required"  # token revoked/expired: the user must reconnect


class SourceKind(StrEnum):
    GSC = "gsc"
    GA4 = "ga4"
    BING = "bing"
    INDEXNOW = "indexnow"


provider_enum = Enum(Provider, name="integration_provider", values_callable=pg_enum_values)
status_enum = Enum(ConnectionStatus, name="connection_status", values_callable=pg_enum_values)
source_enum = Enum(SourceKind, name="source_kind", values_callable=pg_enum_values)


class Connection(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("organization_id", "provider"),)

    provider: Mapped[Provider] = mapped_column(provider_enum, nullable=False)
    status: Mapped[ConnectionStatus] = mapped_column(
        status_enum, nullable=False, default=ConnectionStatus.ACTIVE
    )
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(200)), nullable=False, default=list)
    account_label: Mapped[str | None] = mapped_column(String(320))  # e.g. Google account email
    credentials: Mapped[str] = mapped_column(Text, nullable=False)  # keyring ciphertext
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectSource(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "project_sources"
    __table_args__ = (UniqueConstraint("project_id", "kind"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[SourceKind] = mapped_column(source_enum, nullable=False)
    # GSC site ("sc-domain:example.com"), GA4 "properties/123", Bing site URL, or the
    # IndexNow key. Not secret: IndexNow keys are published on the site by design.
    property_id: Mapped[str] = mapped_column(String(500), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str | None] = mapped_column(String(40))
    synced_through: Mapped[date | None] = mapped_column(Date)


def _metric_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


class GscDaily(TenantMixin, Base):
    """Search Console performance rows (query x page x country x device x day)."""

    __tablename__ = "gsc_daily"
    __table_args__ = (Index("ix_gsc_daily_project_date", "project_id", "date"),)

    id: Mapped[uuid.UUID] = _metric_pk()
    date: Mapped[date] = mapped_column(Date, primary_key=True)  # hypertable time column
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(3), nullable=False)
    device: Mapped[str] = mapped_column(String(10), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[float] = mapped_column(Float, nullable=False)


class Ga4Daily(TenantMixin, Base):
    """GA4 organic-search landing-page engagement and conversions."""

    __tablename__ = "ga4_daily"
    __table_args__ = (Index("ix_ga4_daily_project_date", "project_id", "date"),)

    id: Mapped[uuid.UUID] = _metric_pk()
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    landing_page: Mapped[str] = mapped_column(Text, nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    engaged_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    conversions: Mapped[float] = mapped_column(Float, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, nullable=False)


class BingDaily(TenantMixin, Base):
    """Bing Webmaster Tools query statistics (Bing, Yahoo and DuckDuckGo traffic)."""

    __tablename__ = "bing_daily"
    __table_args__ = (Index("ix_bing_daily_project_date", "project_id", "date"),)

    id: Mapped[uuid.UUID] = _metric_pk()
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[float | None] = mapped_column(Float)


class AiPerformanceDaily(TenantMixin, Base):
    """First-party AI-search data imported from CSV exports.

    ``source`` is ``gsc_genai`` (Search Console's Generative AI report: AI Overviews and
    AI Mode) or ``bing_ai`` (Bing Webmaster Tools AI Performance: Copilot citations).
    Neither has an API yet (plan §3); the adapters switch to APIs when they ship.
    """

    __tablename__ = "ai_performance_daily"
    __table_args__ = (Index("ix_ai_perf_project_date", "project_id", "source", "date"),)

    id: Mapped[uuid.UUID] = _metric_pk()
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    surface: Mapped[str] = mapped_column(
        String(40), nullable=False
    )  # ai_overview, ai_mode, copilot
    page: Mapped[str] = mapped_column(Text, nullable=False, default="")
    query: Mapped[str] = mapped_column(Text, nullable=False, default="")
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # as exported
    device: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    citations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class VitalsDaily(TenantMixin, Base):
    """Core Web Vitals field data (CrUX p75) per origin or URL and form factor."""

    __tablename__ = "vitals_daily"
    __table_args__ = (Index("ix_vitals_project_date", "project_id", "date"),)

    id: Mapped[uuid.UUID] = _metric_pk()
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)  # origin or URL
    scope: Mapped[str] = mapped_column(String(10), nullable=False)  # "origin" | "url"
    form_factor: Mapped[str] = mapped_column(String(10), nullable=False)  # PHONE | DESKTOP
    lcp_ms: Mapped[float | None] = mapped_column(Float)
    inp_ms: Mapped[float | None] = mapped_column(Float)
    cls: Mapped[float | None] = mapped_column(Float)
    fcp_ms: Mapped[float | None] = mapped_column(Float)
    ttfb_ms: Mapped[float | None] = mapped_column(Float)


class UrlInspection(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """Result of a Search Console URL Inspection (Google's own index status)."""

    __tablename__ = "url_inspections"
    __table_args__ = (Index("ix_url_inspections_project_url", "project_id", "url"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(40))
    coverage_state: Mapped[str | None] = mapped_column(String(200))
    indexing_state: Mapped[str | None] = mapped_column(String(80))
    robots_state: Mapped[str | None] = mapped_column(String(80))
    page_fetch_state: Mapped[str | None] = mapped_column(String(80))
    last_crawl_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    google_canonical: Mapped[str | None] = mapped_column(Text)
    user_canonical: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class IndexNowSubmission(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """Log of URL submissions (IndexNow and Bing URL submission) for audit and quotas."""

    __tablename__ = "indexing_submissions"
    __table_args__ = (Index("ix_indexing_submissions_project", "project_id", "submitted_at"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # indexnow | bing
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)  # manual | crawl
    urls: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
