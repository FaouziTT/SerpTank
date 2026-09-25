"""Billing state per organization, and the Stripe webhook event log (idempotency)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import Base, TimestampMixin


class OrganizationBilling(TimestampMixin, Base):
    """Mirror of the org's Stripe subscription. Stripe is the source of truth."""

    __tablename__ = "organization_billing"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(80))
    # active | trialing | past_due | canceled | unpaid | incomplete | none
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    plan_code: Mapped[str] = mapped_column(String(40), nullable=False, default="free")
    addons: Mapped[list[str]] = mapped_column(ARRAY(String(40)), nullable=False, default=list)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Payment failed: paid features stay on until this moment, then drop to free.
    grace_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StripeEvent(Base):
    """Every processed webhook event id (global; Stripe ids are unique). Replays no-op."""

    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    # Informational only (the table is a global replay guard, not tenant data).
    org_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
