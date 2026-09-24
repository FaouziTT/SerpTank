"""ORM foundation: declarative base, mixins and shared enums.

Conventions (docs/execution-plan.md §5.2):

* Primary keys are **UUIDv7** (time-ordered, index-friendly, not enumerable).
* Timestamps are timezone-aware and set by the database.
* Every tenant-owned table uses :class:`TenantMixin` - a non-null, indexed
  ``organization_id`` with ``ON DELETE CASCADE`` - and gets Row-Level Security in its
  migration via ``migrations.helpers.enable_tenant_rls``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

import uuid_utils
from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def uuid7() -> uuid.UUID:
    """New time-ordered UUID (RFC 9562 version 7)."""
    return uuid.UUID(str(uuid_utils.uuid7()))


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantMixin:
    """Marks a table as tenant-owned. Repositories and RLS both key on this column."""

    @declared_attr
    @classmethod
    def organization_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class MemberRole(StrEnum):
    """Organization roles, most to least privileged (see modules.tenancy.policies)."""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    BILLING = "billing"


class SearchEngine(StrEnum):
    """Classic search engines. Google is tier 1 (all plans); others are plan add-ons."""

    GOOGLE = "google"
    BING = "bing"
    YAHOO = "yahoo"
    DUCKDUCKGO = "duckduckgo"
    YANDEX = "yandex"
    BAIDU = "baidu"
    NAVER = "naver"
    SEZNAM = "seznam"


class AIEngine(StrEnum):
    """AI answer surfaces tracked by the AI-visibility track."""

    GOOGLE_AI_OVERVIEW = "google_ai_overview"
    GOOGLE_AI_MODE = "google_ai_mode"
    CHATGPT = "chatgpt"
    PERPLEXITY = "perplexity"
    GEMINI = "gemini"
    COPILOT = "copilot"
    CLAUDE = "claude"


class Device(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


def pg_enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Store enum *values* (not names) in PostgreSQL enums."""
    return [member.value for member in enum_cls]
