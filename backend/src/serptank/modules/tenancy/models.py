"""Organizations (tenants) and memberships."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import (
    Base,
    MemberRole,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum_values,
)

member_role_enum = Enum(
    MemberRole, name="member_role", values_callable=pg_enum_values, validate_strings=True
)


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    plan_code: Mapped[str] = mapped_column(String(40), nullable=False, default="free")
    require_mfa: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # Soft delete with a 30-day grace period before hard deletion (GDPR, M13).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Membership(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MemberRole] = mapped_column(member_role_enum, nullable=False)


class Invitation(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    """An invitation to join an organization (single-use, expiring, hashed token)."""

    __tablename__ = "invitations"

    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    role: Mapped[MemberRole] = mapped_column(member_role_enum, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
