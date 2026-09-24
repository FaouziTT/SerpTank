"""Audit findings produced from a crawl."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import Base, TenantMixin, UUIDPrimaryKeyMixin, pg_enum_values


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


severity_enum = Enum(Severity, name="issue_severity", values_callable=pg_enum_values)


class AuditIssue(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """One occurrence of a rule on one URL (or on the site when ``url`` is null)."""

    __tablename__ = "audit_issues"
    __table_args__ = (Index("ix_audit_issues_crawl_rule", "crawl_id", "rule_id"),)

    crawl_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawls.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[Severity] = mapped_column(severity_enum, nullable=False)
    # "all" for Google-baseline rules (they apply everywhere), else one engine id.
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    url: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
