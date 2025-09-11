"""
Subscription API schemas.

This module defines Pydantic models for subscription-related API requests and responses.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.subscription import SubscriptionStatus, PlanType, BillingCycle


# Stripe-specific schemas
class SubscriptionDetails(BaseModel):
    plan_name: str
    plan_id: str
    status: str  # active, trialing, past_due, canceled, unpaid
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool
    amount: int  # in cents
    currency: str
    interval: str  # month or year
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


class UsageDetails(BaseModel):
    projects: Dict[str, int]  # {"used": 3, "limit": 5}
    api_calls: Dict[str, int]
    team_members: Dict[str, int]
    storage_gb: Dict[str, float]
    crawl_pages: Dict[str, int]


class BillingHistory(BaseModel):
    id: str
    date: str
    amount: int  # in cents
    currency: str
    status: str  # paid, pending, failed
    description: str
    invoice_url: Optional[str] = None


class StripeCheckoutSession(BaseModel):
    session_id: str
    url: str


class StripePortalSession(BaseModel):
    url: str


class PaymentMethod(BaseModel):
    id: str
    type: str  # card, bank_account
    last4: str
    brand: Optional[str] = None  # visa, mastercard, etc.
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None


class Invoice(BaseModel):
    id: str
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    created: datetime
    due_date: Optional[datetime] = None
    pdf_url: Optional[str] = None


class SubscriptionPlanBase(BaseModel):
    """Base subscription plan schema."""
    name: str
    plan_type: PlanType
    description: Optional[str] = None
    monthly_price: Decimal
    annual_price: Decimal
    api_requests_limit: int
    websites_limit: int
    team_members_limit: int
    data_storage_gb_limit: int
    crawl_frequency_hours: int
    features: Dict = Field(default_factory=dict)


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Schema for creating a subscription plan."""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating a subscription plan."""
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[Decimal] = None
    annual_price: Optional[Decimal] = None
    api_requests_limit: Optional[int] = None
    websites_limit: Optional[int] = None
    team_members_limit: Optional[int] = None
    data_storage_gb_limit: Optional[int] = None
    crawl_frequency_hours: Optional[int] = None
    features: Optional[Dict] = None
    is_active: Optional[bool] = None


class SubscriptionPlan(SubscriptionPlanBase):
    """Schema for subscription plan response."""
    id: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionBase(BaseModel):
    """Base subscription schema."""
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    amount: Decimal
    currency: str = "USD"


class SubscriptionCreate(BaseModel):
    """Schema for creating a subscription."""
    plan_type: PlanType
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    trial_days: Optional[int] = None


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    plan_type: Optional[PlanType] = None
    billing_cycle: Optional[BillingCycle] = None
    status: Optional[SubscriptionStatus] = None


class Subscription(SubscriptionBase):
    """Schema for subscription response."""
    id: int
    user_id: int
    plan_id: int
    start_date: datetime
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    extra_data: Dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    is_active: bool = Field(default=False)
    is_trial: bool = Field(default=False)
    days_remaining: Optional[int] = None
    
    class Config:
        from_attributes = True


class SubscriptionWithPlan(Subscription):
    """Schema for subscription response with plan details."""
    plan: SubscriptionPlan
    
    class Config:
        from_attributes = True


class UsageRecordBase(BaseModel):
    """Base usage record schema."""
    metric_name: str
    value: int
    period_start: datetime
    period_end: datetime
    extra_data: Dict = Field(default_factory=dict)


class UsageRecordCreate(BaseModel):
    """Schema for creating a usage record."""
    metric_name: str
    value: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class UsageRecord(UsageRecordBase):
    """Schema for usage record response."""
    id: int
    subscription_id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    """Schema for usage summary response."""
    api_requests: int = 0
    websites: int = 0
    team_members: int = 1
    data_storage_gb: float = 0.0
    
    class Config:
        from_attributes = True


class UsageLimitInfo(BaseModel):
    """Schema for usage limit information."""
    used: int
    limit: int
    percentage: float
    exceeded: bool


class UsageLimits(BaseModel):
    """Schema for usage limits response."""
    api_requests: UsageLimitInfo
    websites: UsageLimitInfo
    team_members: UsageLimitInfo
    
    class Config:
        from_attributes = True


class BillingEventBase(BaseModel):
    """Base billing event schema."""
    event_type: str
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    event_data: Dict = Field(default_factory=dict)


class BillingEvent(BillingEventBase):
    """Schema for billing event response."""
    id: int
    subscription_id: int
    user_id: int
    stripe_event_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    processed: bool
    processed_at: Optional[datetime] = None
    occurred_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class PlanFeatureComparison(BaseModel):
    """Schema for plan feature comparison."""
    feature_name: str
    free_plan: bool
    pro_plan: bool
    enterprise_plan: bool
    description: str


class PlanComparison(BaseModel):
    """Schema for plan comparison response."""
    plans: List[SubscriptionPlan]
    features: List[PlanFeatureComparison]


class SubscriptionActionRequest(BaseModel):
    """Schema for subscription action requests."""
    action: str  # "cancel", "upgrade", "downgrade", "pause"
    reason: Optional[str] = None
    new_plan_type: Optional[PlanType] = None
    billing_cycle: Optional[BillingCycle] = None


class SubscriptionActionResponse(BaseModel):
    """Schema for subscription action responses."""
    success: bool
    message: str
    subscription: Optional[Subscription] = None
