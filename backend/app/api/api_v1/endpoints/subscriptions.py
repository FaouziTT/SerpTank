"""
Subscription API endpoints.

This module defines the FastAPI endpoints for subscription management,
including plan management, billing, and usage tracking.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.models.subscription import PlanType, BillingCycle
from app.schemas.subscription import (
    SubscriptionPlan,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionWithPlan,
    UsageRecord,
    UsageRecordCreate,
    UsageSummary,
    UsageLimits,
    BillingEvent,
    PlanComparison,
    PlanFeatureComparison,
    SubscriptionActionRequest,
    SubscriptionActionResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    """Get all available subscription plans."""
    try:
        service = SubscriptionService(db)
        plans = await service.get_available_plans()
        return plans
    except Exception as e:
        logger.error(f"Error getting subscription plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch subscription plans"
        )


@router.get("/plans/comparison", response_model=PlanComparison)
async def get_plan_comparison(
    db: AsyncSession = Depends(get_db)
):
    """Get detailed plan comparison with features."""
    try:
        service = SubscriptionService(db)
        plans = await service.get_available_plans()
        
        # Define feature comparison
        features = [
            PlanFeatureComparison(
                feature_name="API Requests",
                free_plan=True,
                pro_plan=True,
                enterprise_plan=True,
                description="Number of API requests per month"
            ),
            PlanFeatureComparison(
                feature_name="Websites Monitoring",
                free_plan=True,
                pro_plan=True,
                enterprise_plan=True,
                description="Number of websites you can monitor"
            ),
            PlanFeatureComparison(
                feature_name="Team Members",
                free_plan=False,
                pro_plan=True,
                enterprise_plan=True,
                description="Collaborate with team members"
            ),
            PlanFeatureComparison(
                feature_name="Advanced Analytics",
                free_plan=False,
                pro_plan=True,
                enterprise_plan=True,
                description="Detailed reports and insights"
            ),
            PlanFeatureComparison(
                feature_name="Priority Support",
                free_plan=False,
                pro_plan=False,
                enterprise_plan=True,
                description="24/7 priority customer support"
            ),
            PlanFeatureComparison(
                feature_name="Custom Integrations",
                free_plan=False,
                pro_plan=False,
                enterprise_plan=True,
                description="Custom API integrations and webhooks"
            ),
        ]
        
        return PlanComparison(plans=plans, features=features)
    except Exception as e:
        logger.error(f"Error getting plan comparison: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch plan comparison"
        )


@router.get("/current", response_model=Optional[SubscriptionWithPlan])
async def get_current_subscription(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's subscription."""
    try:
        service = SubscriptionService(db)
        subscription = await service.get_user_subscription(current_user.id)
        
        if not subscription:
            return None
        
        # Get plan details
        from sqlalchemy import select
        from app.models.subscription import SubscriptionPlan as SubscriptionPlanModel
        
        plan_query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.id == subscription.plan_id)
        plan_result = await db.execute(plan_query)
        plan = plan_result.scalar_one()
        
        # Create response with computed fields
        subscription_dict = {
            **subscription.__dict__,
            "is_active": subscription.is_active(),
            "is_trial": subscription.is_trial(),
            "days_remaining": subscription.days_remaining(),
            "plan": plan
        }
        
        return SubscriptionWithPlan(**subscription_dict)
    except Exception as e:
        logger.error(f"Error getting current subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch subscription"
        )


@router.post("/subscribe", response_model=SubscriptionActionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription for the current user."""
    try:
        service = SubscriptionService(db)
        
        # Check if user already has an active subscription
        existing_subscription = await service.get_user_subscription(current_user.id)
        if existing_subscription and existing_subscription.is_active():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active subscription"
            )
        
        subscription = await service.create_subscription(
            user_id=current_user.id,
            plan_type=subscription_data.plan_type,
            billing_cycle=subscription_data.billing_cycle,
            trial_days=subscription_data.trial_days
        )
        
        return SubscriptionActionResponse(
            success=True,
            message=f"Successfully subscribed to {subscription_data.plan_type.value} plan",
            subscription=Subscription(
                **subscription.__dict__,
                is_active=subscription.is_active(),
                is_trial=subscription.is_trial(),
                days_remaining=subscription.days_remaining()
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )


@router.post("/action", response_model=SubscriptionActionResponse)
async def perform_subscription_action(
    action_data: SubscriptionActionRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform subscription actions (cancel, upgrade, downgrade)."""
    try:
        service = SubscriptionService(db)
        subscription = await service.get_user_subscription(current_user.id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        if action_data.action == "cancel":
            success = await service.cancel_subscription(subscription.id, action_data.reason)
            if success:
                return SubscriptionActionResponse(
                    success=True,
                    message="Subscription canceled successfully"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to cancel subscription"
                )
        
        elif action_data.action in ["upgrade", "downgrade"]:
            if not action_data.new_plan_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="new_plan_type is required for upgrade/downgrade"
                )
            
            updated_subscription = await service.upgrade_subscription(
                subscription.id,
                action_data.new_plan_type,
                action_data.billing_cycle
            )
            
            return SubscriptionActionResponse(
                success=True,
                message=f"Successfully {action_data.action}d to {action_data.new_plan_type.value} plan",
                subscription=Subscription(
                    **updated_subscription.__dict__,
                    is_active=updated_subscription.is_active(),
                    is_trial=updated_subscription.is_trial(),
                    days_remaining=updated_subscription.days_remaining()
                )
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {action_data.action}"
            )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error performing subscription action for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform subscription action"
        )


@router.get("/usage", response_model=UsageLimits)
async def get_usage_limits(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current usage and limits for the user."""
    try:
        service = SubscriptionService(db)
        limits_status = await service.check_usage_limits(current_user.id)
        
        return UsageLimits(**limits_status)
    except Exception as e:
        logger.error(f"Error getting usage limits for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch usage limits"
        )


@router.post("/usage/track", response_model=UsageRecord)
async def track_usage(
    usage_data: UsageRecordCreate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Track usage for a specific metric."""
    try:
        service = SubscriptionService(db)
        usage_record = await service.track_usage(
            user_id=current_user.id,
            metric_name=usage_data.metric_name,
            value=usage_data.value,
            period_start=usage_data.period_start,
            period_end=usage_data.period_end
        )
        
        return usage_record
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error tracking usage for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track usage"
        )


@router.get("/usage/can-perform/{action}")
async def can_perform_action(
    action: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if user can perform a specific action based on their plan limits."""
    try:
        service = SubscriptionService(db)
        can_perform, reason = await service.can_perform_action(current_user.id, action)
        
        return {
            "can_perform": can_perform,
            "reason": reason,
            "action": action
        }
    except Exception as e:
        logger.error(f"Error checking action permission for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check action permission"
        )


# Admin endpoints (protected by superuser check)
@router.post("/admin/plans", response_model=SubscriptionPlan)
async def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription plan (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        from app.models.subscription import SubscriptionPlan as SubscriptionPlanModel
        
        plan = SubscriptionPlanModel(**plan_data.dict())
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        
        return plan
    except Exception as e:
        logger.error(f"Error creating subscription plan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription plan"
        )


@router.put("/admin/plans/{plan_id}", response_model=SubscriptionPlan)
async def update_subscription_plan(
    plan_id: int,
    plan_data: SubscriptionPlanUpdate,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a subscription plan (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        from sqlalchemy import select
        from app.models.subscription import SubscriptionPlan as SubscriptionPlanModel
        
        query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.id == plan_id)
        result = await db.execute(query)
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found"
            )
        
        # Update fields
        for field, value in plan_data.dict(exclude_unset=True).items():
            setattr(plan, field, value)
        
        await db.commit()
        await db.refresh(plan)
        
        return plan
    except Exception as e:
        logger.error(f"Error updating subscription plan {plan_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription plan"
        )
