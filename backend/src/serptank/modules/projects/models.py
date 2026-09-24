"""Projects and target markets (engine-aware from day one, plan §4.5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import (
    AIEngine,
    Base,
    Device,
    SearchEngine,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum_values,
)

search_engine_enum = Enum(SearchEngine, name="search_engine", values_callable=pg_enum_values)
ai_engine_enum = Enum(AIEngine, name="ai_engine", values_callable=pg_enum_values)
device_enum = Enum(Device, name="device", values_callable=pg_enum_values)


class Project(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("crawl_schedule IN ('off', 'weekly', 'monthly')", name="crawl_schedule"),
        Index(
            "uq_projects_org_domain_active",
            "organization_id",
            "primary_domain",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Registrable host, e.g. "example.com" (validated with the Public Suffix List in M5).
    primary_domain: Mapped[str] = mapped_column(CITEXT, nullable=False)
    domain_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_method: Mapped[str | None] = mapped_column(String(20))
    # Published by the customer in DNS or a file, so it is not a secret.
    verification_token: Mapped[str | None] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Automatic technical audits: "off", "weekly" or "monthly" (verified domains only).
    crawl_schedule: Mapped[str] = mapped_column(
        String(10), nullable=False, default="off", server_default="off"
    )


class ProjectMarket(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """A market a project competes in: country + language (+ city) + device + engines."""

    __tablename__ = "project_markets"
    __table_args__ = (
        Index(
            "uq_project_markets_target",
            "project_id",
            "country",
            "language",
            text("coalesce(location, '')"),
            "device",
            unique=True,
        ),
        CheckConstraint("country ~ '^[A-Z]{2}$'", name="country_iso2"),
        CheckConstraint("cardinality(search_engines) >= 1", name="has_engine"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    language: Mapped[str] = mapped_column(String(35), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    device: Mapped[Device] = mapped_column(device_enum, nullable=False, default=Device.DESKTOP)
    search_engines: Mapped[list[SearchEngine]] = mapped_column(
        ARRAY(search_engine_enum), nullable=False, default=lambda: [SearchEngine.GOOGLE]
    )
    ai_engines: Mapped[list[AIEngine]] = mapped_column(
        ARRAY(ai_engine_enum), nullable=False, default=list
    )
