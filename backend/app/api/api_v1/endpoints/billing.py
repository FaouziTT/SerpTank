"""
Stripe billing integration endpoints.
"""
import logging

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None
    STRIPE_AVAILABLE = False
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.core.config import settings
from app.models.user import User
from app.models.subscription import Subscription as SubscriptionModel
from app.schemas.subscription import (
    SubscriptionDetails,
    UsageDetails,
    BillingHistory,
    StripeCheckoutSession,
    StripePortalSession,
    PaymentMethod,
    Invoice
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Stripe if available
if STRIPE_AVAILABLE and stripe:
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
else:
    logger.warning("Stripe module not available. Billing endpoints will return mock data.")


@router.get("/subscription", response_model=Optional[SubscriptionDetails])
async def get_subscription_details(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current subscription details from Stripe."""
    if not STRIPE_AVAILABLE:
        # Return mock data for testing
        return SubscriptionDetails(
            plan_name="Free Trial",
            plan_id="free-trial",
            status="active",
            current_period_start=datetime.utcnow().isoformat(),
            current_period_end=datetime.utcnow().isoformat(),
            cancel_at_period_end=False,
            amount=0,
            currency="usd",
            interval="month"
        )
    
    try:
        if not current_user.stripe_customer_id:
            return None
        
        # Get subscription from Stripe
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status='all',
            limit=1
        )
        
        if not subscriptions.data:
            return None
        
        subscription = subscriptions.data[0]
        
        # Map Stripe data to our schema
        return SubscriptionDetails(
            plan_name=subscription.items.data[0].price.nickname or "Custom Plan",
            plan_id=subscription.items.data[0].price.id,
            status=subscription.status,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start).isoformat(),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end).isoformat(),
            cancel_at_period_end=subscription.cancel_at_period_end,
            amount=subscription.items.data[0].price.unit_amount,
            currency=subscription.items.data[0].price.currency,
            interval=subscription.items.data[0].price.recurring.interval,
            stripe_customer_id=current_user.stripe_customer_id,
            stripe_subscription_id=subscription.id
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch subscription details"
        )
    except Exception as e:
        logger.error(f"Error getting subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch subscription details"
        )


@router.get("/usage", response_model=UsageDetails)
async def get_usage_details(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current usage details."""
    try:
        # Get project count
        from app.models.project import Project
        project_result = await db.execute(
            select(Project).where(Project.user_id == current_user.id)
        )
        projects = project_result.scalars().all()
        
        # Get usage from subscription service
        from app.services.subscription_service import SubscriptionService
        service = SubscriptionService(db)
        limits = await service.check_usage_limits(current_user.id)
        
        # Map to response schema
        return UsageDetails(
            projects={
                "used": len(projects),
                "limit": limits.get("websites_limit", 5)
            },
            api_calls={
                "used": limits.get("api_requests_used", 0),
                "limit": limits.get("api_requests_limit", 10000)
            },
            team_members={
                "used": 1,  # TODO: Get actual team member count
                "limit": limits.get("team_members_limit", 3)
            },
            storage_gb={
                "used": 0,  # TODO: Calculate actual storage
                "limit": limits.get("storage_limit_gb", 10)
            },
            crawl_pages={
                "used": limits.get("crawl_pages_used", 0),
                "limit": limits.get("crawl_pages_limit", 10000)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting usage details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch usage details"
        )


@router.get("/history", response_model=List[BillingHistory])
async def get_billing_history(
    limit: int = 10,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing history from Stripe."""
    try:
        if not current_user.stripe_customer_id:
            return []
        
        # Get invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=current_user.stripe_customer_id,
            limit=limit
        )
        
        history = []
        for invoice in invoices.data:
            history.append(BillingHistory(
                id=invoice.id,
                date=datetime.fromtimestamp(invoice.created).isoformat(),
                amount=invoice.amount_paid,
                currency=invoice.currency,
                status='paid' if invoice.paid else ('failed' if invoice.attempted else 'pending'),
                description=invoice.description or f"{invoice.lines.data[0].description}",
                invoice_url=invoice.hosted_invoice_url
            ))
        
        return history
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting billing history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch billing history"
        )
    except Exception as e:
        logger.error(f"Error getting billing history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch billing history"
        )


@router.post("/create-checkout-session", response_model=StripeCheckoutSession)
async def create_checkout_session(
    plan_id: str,
    billing_cycle: str = "month",  # month or year
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe checkout session for subscription."""
    try:
        # Get or create Stripe customer
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": str(current_user.id)}
            )
            customer_id = customer.id
            
            # Save customer ID
            user_result = await db.execute(
                select(User).where(User.id == current_user.id)
            )
            user = user_result.scalar_one()
            user.stripe_customer_id = customer_id
            await db.commit()
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/settings?tab=billing&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/settings?tab=billing",
            metadata={
                "user_id": str(current_user.id),
                "billing_cycle": billing_cycle
            }
        )
        
        return StripeCheckoutSession(
            session_id=session.id,
            url=session.url
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post("/create-portal-session", response_model=StripePortalSession)
async def create_portal_session(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe customer portal session."""
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No billing account found"
            )
        
        # Create portal session
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/settings?tab=billing"
        )
        
        return StripePortalSession(url=session.url)
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating portal session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create billing portal session"
        )
    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create billing portal session"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            await handle_checkout_session_completed(session, db)
            
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            await handle_subscription_updated(subscription, db)
            
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            await handle_subscription_deleted(subscription, db)
            
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            await handle_invoice_payment_succeeded(invoice, db)
            
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            await handle_invoice_payment_failed(invoice, db)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


async def handle_checkout_session_completed(session: Dict[str, Any], db: AsyncSession):
    """Handle successful checkout."""
    try:
        customer_id = session['customer']
        subscription_id = session['subscription']
        
        # Get user by customer ID
        user_result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            # Update user's subscription status
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Create or update local subscription record
            from app.models.subscription import Subscription, PlanType, BillingCycle
            
            local_sub_result = await db.execute(
                select(SubscriptionModel).where(SubscriptionModel.user_id == user.id)
            )
            local_sub = local_sub_result.scalar_one_or_none()
            
            if not local_sub:
                # Map Stripe plan to our plan types
                plan_mapping = {
                    'price_starter_monthly': (PlanType.PRO, BillingCycle.MONTHLY),
                    'price_starter_yearly': (PlanType.PRO, BillingCycle.YEARLY),
                    'price_professional_monthly': (PlanType.ENTERPRISE, BillingCycle.MONTHLY),
                    'price_professional_yearly': (PlanType.ENTERPRISE, BillingCycle.YEARLY),
                }
                
                plan_type, billing_cycle = plan_mapping.get(
                    subscription.items.data[0].price.id,
                    (PlanType.PRO, BillingCycle.MONTHLY)
                )
                
                local_sub = SubscriptionModel(
                    user_id=user.id,
                    stripe_subscription_id=subscription_id,
                    stripe_customer_id=customer_id,
                    plan_type=plan_type,
                    billing_cycle=billing_cycle,
                    status='active',
                    current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                    current_period_end=datetime.fromtimestamp(subscription.current_period_end)
                )
                db.add(local_sub)
            else:
                local_sub.stripe_subscription_id = subscription_id
                local_sub.status = 'active'
                local_sub.current_period_start = datetime.fromtimestamp(subscription.current_period_start)
                local_sub.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error handling checkout completion: {str(e)}")
        raise


async def handle_subscription_updated(subscription: Dict[str, Any], db: AsyncSession):
    """Handle subscription updates."""
    try:
        # Update local subscription record
        local_sub_result = await db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.stripe_subscription_id == subscription['id']
            )
        )
        local_sub = local_sub_result.scalar_one_or_none()
        
        if local_sub:
            local_sub.status = subscription['status']
            local_sub.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
            local_sub.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            local_sub.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
            
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error handling subscription update: {str(e)}")
        raise


async def handle_subscription_deleted(subscription: Dict[str, Any], db: AsyncSession):
    """Handle subscription cancellation."""
    try:
        local_sub_result = await db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.stripe_subscription_id == subscription['id']
            )
        )
        local_sub = local_sub_result.scalar_one_or_none()
        
        if local_sub:
            local_sub.status = 'canceled'
            local_sub.ended_at = datetime.utcnow()
            
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {str(e)}")
        raise


async def handle_invoice_payment_succeeded(invoice: Dict[str, Any], db: AsyncSession):
    """Handle successful payment."""
    # Log successful payment
    logger.info(f"Payment succeeded for invoice {invoice['id']}")
    
    # Could trigger webhook to notify user of successful payment
    from app.services.webhook_service import WebhookService, WebhookEvents
    
    user_result = await db.execute(
        select(User).where(User.stripe_customer_id == invoice['customer'])
    )
    user = user_result.scalar_one_or_none()
    
    if user:
        webhook_service = WebhookService(db)
        await webhook_service.trigger_event(
            project_id=None,  # User-level event
            event_type="billing.payment_succeeded",
            data={
                "user_id": user.id,
                "amount": invoice['amount_paid'],
                "currency": invoice['currency'],
                "invoice_url": invoice['hosted_invoice_url']
            }
        )


async def handle_invoice_payment_failed(invoice: Dict[str, Any], db: AsyncSession):
    """Handle failed payment."""
    logger.warning(f"Payment failed for invoice {invoice['id']}")
    
    # Could trigger webhook to notify user of failed payment
    from app.services.webhook_service import WebhookService
    
    user_result = await db.execute(
        select(User).where(User.stripe_customer_id == invoice['customer'])
    )
    user = user_result.scalar_one_or_none()
    
    if user:
        webhook_service = WebhookService(db)
        await webhook_service.trigger_event(
            project_id=None,  # User-level event
            event_type="billing.payment_failed",
            data={
                "user_id": user.id,
                "amount": invoice['amount_due'],
                "currency": invoice['currency'],
                "next_attempt": invoice.get('next_payment_attempt')
            }
        )