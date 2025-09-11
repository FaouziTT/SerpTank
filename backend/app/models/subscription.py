"""
Subscription and billing models.

This module defines SQLAlchemy models for managing user subscriptions,
billing, usage tracking, and plan-based features.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"


class PlanType(str, Enum):
    """Subscription plan types."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BillingCycle(str, Enum):
    """Billing cycle types."""
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionPlan(Base):
    """Model for subscription plans."""
    
    __tablename__ = "subscription_plans"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Plan details
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    plan_type: Mapped[PlanType] = mapped_column(SQLEnum(PlanType))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pricing
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    annual_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    
    # Feature limits
    api_requests_limit: Mapped[int] = mapped_column(Integer, default=1000)
    websites_limit: Mapped[int] = mapped_column(Integer, default=1)
    team_members_limit: Mapped[int] = mapped_column(Integer, default=1)
    data_storage_gb_limit: Mapped[int] = mapped_column(Integer, default=1)
    crawl_frequency_hours: Mapped[int] = mapped_column(Integer, default=24)  # minimum hours between crawls
    
    # Features availability
    features: Mapped[Dict] = mapped_column(JSONB, default=lambda: {})  # JSON object of feature flags
    
    # Plan metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))    # Note: Relationships temporarily commented out to avoid circular import issues
    # Will be re-added after proper relationship management is implemented
    
    def __repr__(self) -> str:
        return f"<SubscriptionPlan(id={self.id}, name={self.name}, type={self.plan_type})>"


class Subscription(Base):
    """Model for user subscriptions."""
    
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    
    # Subscription details
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    billing_cycle: Mapped[BillingCycle] = mapped_column(SQLEnum(BillingCycle), default=BillingCycle.MONTHLY)
    
    # Billing information
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Subscription dates
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_billing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # External billing system IDs
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)    # Metadata
    extra_data: Mapped[Dict] = mapped_column(JSONB, default=lambda: {})  # Additional subscription data
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan")
    
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        if self.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
            return False
        
        if self.end_date and self.end_date < datetime.now(timezone.utc):
            return False
            
        return True
    
    def is_trial(self) -> bool:
        """Check if subscription is in trial period."""
        return (
            self.status == SubscriptionStatus.TRIALING and 
            self.trial_end_date and 
            self.trial_end_date > datetime.now(timezone.utc)
        )
    
    def days_remaining(self) -> Optional[int]:
        """Get days remaining in current billing cycle."""
        if not self.next_billing_date:
            return None
        
        delta = self.next_billing_date - datetime.now(timezone.utc)
        return max(0, delta.days)
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"


class UsageRecord(Base):
    """Model for tracking usage metrics."""
    
    __tablename__ = "usage_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscriptions.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
      # Usage tracking
    metric_name: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "api_requests", "websites"
    value: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    
    # Metadata
    extra_data: Mapped[Dict] = mapped_column(JSONB, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_records")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription")
    
    def __repr__(self) -> str:
        return f"<UsageRecord(id={self.id}, metric={self.metric_name}, value={self.value})>"


class BillingEvent(Base):
    """Model for billing events and transactions."""
    
    __tablename__ = "billing_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscriptions.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "invoice.paid", "subscription.created"
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    
    # External system IDs
    stripe_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
      # Event data
    event_data: Mapped[Dict] = mapped_column(JSONB, default=lambda: {})
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="billing_events")
    
    def __repr__(self) -> str:
        return f"<BillingEvent(id={self.id}, type={self.event_type}, amount={self.amount})>"
