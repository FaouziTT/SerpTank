"""
Subscription Service

This service handles subscription management, billing operations,
usage tracking, and plan-based feature restrictions.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscription import (
    SubscriptionPlan, 
    Subscription, 
    UsageRecord, 
    BillingEvent,
    SubscriptionStatus,
    PlanType,
    BillingCycle
)
from app.models.user import User

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Handle subscription management and billing operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_available_plans(self) -> List[SubscriptionPlan]:
        """Get all available subscription plans."""
        query = select(SubscriptionPlan).where(
            SubscriptionPlan.is_active == True
        ).order_by(SubscriptionPlan.sort_order)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_plan_by_type(self, plan_type: PlanType) -> Optional[SubscriptionPlan]:
        """Get a plan by its type."""
        query = select(SubscriptionPlan).where(
            and_(
                SubscriptionPlan.plan_type == plan_type,
                SubscriptionPlan.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's active subscription."""
        query = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE
                ])
            )
        ).order_by(Subscription.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_subscription(
        self,
        user_id: int,
        plan_type: PlanType,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        trial_days: Optional[int] = None
    ) -> Subscription:
        """
        Create a new subscription for a user.
        
        Args:
            user_id: ID of the user
            plan_type: Type of plan to subscribe to
            billing_cycle: Monthly or annual billing
            trial_days: Number of trial days (optional)
            
        Returns:
            Created subscription object
        """
        # Get the plan
        plan = await self.get_plan_by_type(plan_type)
        if not plan:
            raise ValueError(f"Plan type {plan_type} not found")
        
        # Cancel any existing active subscription
        existing_subscription = await self.get_user_subscription(user_id)
        if existing_subscription:
            await self.cancel_subscription(existing_subscription.id)
        
        # Determine pricing
        amount = plan.monthly_price if billing_cycle == BillingCycle.MONTHLY else plan.annual_price
        
        # Set up dates
        start_date = datetime.now()
        trial_end_date = None
        next_billing_date = None
        status = SubscriptionStatus.ACTIVE
        
        if trial_days and trial_days > 0:
            trial_end_date = start_date + timedelta(days=trial_days)
            next_billing_date = trial_end_date
            status = SubscriptionStatus.TRIALING
        else:
            # Set next billing date
            if billing_cycle == BillingCycle.MONTHLY:
                next_billing_date = start_date + timedelta(days=30)
            else:
                next_billing_date = start_date + timedelta(days=365)
        
        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status=status,
            billing_cycle=billing_cycle,
            amount=amount,
            start_date=start_date,
            trial_end_date=trial_end_date,
            next_billing_date=next_billing_date
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        # Update user's subscription plan field
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one()
        user.subscription_plan = plan_type.value
        user.subscription_status = status.value
        user.subscription_start_date = start_date
        
        await self.db.commit()
        
        logger.info(f"Created subscription {subscription.id} for user {user_id} with plan {plan_type}")
        
        return subscription
    
    async def cancel_subscription(self, subscription_id: int, reason: Optional[str] = None) -> bool:
        """Cancel a subscription."""
        query = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.now()
        
        if reason:
            subscription.extra_data = {**subscription.extra_data, "cancellation_reason": reason}
        
        # Update user's subscription status
        user_query = select(User).where(User.id == subscription.user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one()
        user.subscription_status = SubscriptionStatus.CANCELED.value
        
        await self.db.commit()
        
        logger.info(f"Canceled subscription {subscription_id}")
        
        return True
    
    async def upgrade_subscription(
        self,
        subscription_id: int,
        new_plan_type: PlanType,
        billing_cycle: Optional[BillingCycle] = None
    ) -> Subscription:
        """Upgrade/downgrade a subscription to a different plan."""
        # Get current subscription
        query = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Get new plan
        new_plan = await self.get_plan_by_type(new_plan_type)
        if not new_plan:
            raise ValueError(f"Plan type {new_plan_type} not found")
        
        # Update subscription
        old_plan_id = subscription.plan_id
        subscription.plan_id = new_plan.id
        
        if billing_cycle:
            subscription.billing_cycle = billing_cycle
        
        # Update pricing
        subscription.amount = (
            new_plan.monthly_price if subscription.billing_cycle == BillingCycle.MONTHLY 
            else new_plan.annual_price
        )
        
        # Update user's subscription plan
        user_query = select(User).where(User.id == subscription.user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one()
        user.subscription_plan = new_plan_type.value
        
        await self.db.commit()
        
        logger.info(f"Updated subscription {subscription_id} from plan {old_plan_id} to {new_plan.id}")
        
        return subscription
    
    async def track_usage(
        self,
        user_id: int,
        metric_name: str,
        value: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> UsageRecord:
        """
        Track usage for a specific metric.
        
        Args:
            user_id: ID of the user
            metric_name: Name of the metric (e.g., "api_requests", "websites")
            value: Usage value
            period_start: Start of the period (defaults to current month start)
            period_end: End of the period (defaults to current month end)
            
        Returns:
            Usage record
        """
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            raise ValueError(f"No active subscription found for user {user_id}")
        
        # Default to current month if period not specified
        if not period_start:
            now = datetime.now()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if not period_end:
            # Last day of current month
            next_month = period_start.replace(month=period_start.month + 1) if period_start.month < 12 else period_start.replace(year=period_start.year + 1, month=1)
            period_end = next_month - timedelta(seconds=1)
        
        # Check if usage record already exists for this period
        existing_query = select(UsageRecord).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.metric_name == metric_name,
                UsageRecord.period_start == period_start,
                UsageRecord.period_end == period_end
            )
        )
        
        result = await self.db.execute(existing_query)
        usage_record = result.scalar_one_or_none()
        
        if usage_record:
            # Update existing record
            usage_record.value += value
        else:
            # Create new record
            usage_record = UsageRecord(
                subscription_id=subscription.id,
                user_id=user_id,
                metric_name=metric_name,
                value=value,
                period_start=period_start,
                period_end=period_end
            )
            self.db.add(usage_record)
        
        await self.db.commit()
        await self.db.refresh(usage_record)
        
        return usage_record
    
    async def get_usage_summary(self, user_id: int, period_start: Optional[datetime] = None) -> Dict[str, int]:
        """
        Get usage summary for a user for a specific period.
        
        Args:
            user_id: ID of the user
            period_start: Start of the period (defaults to current month start)
            
        Returns:
            Dictionary of metric names and their usage values
        """
        if not period_start:
            now = datetime.now()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        query = select(UsageRecord).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.period_start >= period_start
            )
        )
        
        result = await self.db.execute(query)
        usage_records = result.scalars().all()
        
        # Aggregate usage by metric
        usage_summary = {}
        for record in usage_records:
            if record.metric_name in usage_summary:
                usage_summary[record.metric_name] += record.value
            else:
                usage_summary[record.metric_name] = record.value
        
        return usage_summary
    
    async def check_usage_limits(self, user_id: int) -> Dict[str, Dict]:
        """
        Check if user is within their plan limits.
        
        Returns:
            Dictionary with limit information for each metric
        """
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            # Default to free plan limits
            free_plan = await self.get_plan_by_type(PlanType.FREE)
            if not free_plan:
                return {}
            plan = free_plan
        else:
            # Get plan with relationship
            plan_query = select(SubscriptionPlan).where(SubscriptionPlan.id == subscription.plan_id)
            plan_result = await self.db.execute(plan_query)
            plan = plan_result.scalar_one()
        
        # Get current usage
        usage_summary = await self.get_usage_summary(user_id)
        
        # Check limits
        limits_status = {
            "api_requests": {
                "used": usage_summary.get("api_requests", 0),
                "limit": plan.api_requests_limit,
                "percentage": min(100, (usage_summary.get("api_requests", 0) / plan.api_requests_limit) * 100),
                "exceeded": usage_summary.get("api_requests", 0) > plan.api_requests_limit
            },
            "websites": {
                "used": usage_summary.get("websites", 0),
                "limit": plan.websites_limit,
                "percentage": min(100, (usage_summary.get("websites", 0) / plan.websites_limit) * 100),
                "exceeded": usage_summary.get("websites", 0) > plan.websites_limit
            },
            "team_members": {
                "used": usage_summary.get("team_members", 1),  # Default to 1 (user themselves)
                "limit": plan.team_members_limit,
                "percentage": min(100, (usage_summary.get("team_members", 1) / plan.team_members_limit) * 100),
                "exceeded": usage_summary.get("team_members", 1) > plan.team_members_limit
            }
        }
        
        return limits_status
    
    async def can_perform_action(self, user_id: int, action: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user can perform a specific action based on their plan limits.
        
        Args:
            user_id: ID of the user
            action: Action to check (e.g., "create_website", "api_request")
            
        Returns:
            Tuple of (can_perform, reason_if_not)
        """
        limits_status = await self.check_usage_limits(user_id)
        
        action_to_metric = {
            "create_website": "websites",
            "api_request": "api_requests",
            "add_team_member": "team_members"
        }
        
        metric = action_to_metric.get(action)
        if not metric:
            return True, None  # Unknown action, allow by default
        
        if metric not in limits_status:
            return True, None
        
        limit_info = limits_status[metric]
        if limit_info["exceeded"]:
            return False, f"You have exceeded your {metric} limit ({limit_info['used']}/{limit_info['limit']}). Please upgrade your plan."
        
        return True, None
