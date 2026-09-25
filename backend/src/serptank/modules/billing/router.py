"""Billing API.

* ``GET  /orgs/{org}/billing``           plan, subscription state, catalog, usage meters
* ``POST /orgs/{org}/billing/checkout``  Stripe Checkout URL (billing managers, step-up)
* ``POST /orgs/{org}/billing/portal``    Stripe Customer Portal URL (plan changes, cards)
* ``GET  /orgs/{org}/billing/invoices``  real invoices from Stripe (never generated here)
* ``POST /billing/stripe/webhook``       signature-verified events (CSRF-exempt path)

There is deliberately no endpoint that changes a plan directly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from serptank.core.errors import AppError, ConflictError
from serptank.core.http import SafeHttpClient
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.billing import service
from serptank.modules.billing.entitlements import PLANS, plan_of
from serptank.modules.billing.models import OrganizationBilling
from serptank.modules.billing.stripe import (
    BillingUnavailableError,
    StripeClient,
    WebhookSignatureError,
    verify_webhook,
)
from serptank.modules.crawler.service import pages_used_this_month
from serptank.modules.identity.deps import DbSession, RecentlyReauthenticated
from serptank.modules.llm.gateway import LlmGateway, requests_this_month
from serptank.modules.projects.models import Project
from serptank.modules.search_data.models import SerpUsage, TrackedKeyword
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.models import Membership
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/billing", tags=["billing"])
BillingManage = Annotated[OrgContext, Depends(org_access(Permission.BILLING_MANAGE))]
WEBHOOK_PATH = "/api/v1/billing/stripe/webhook"
_CHECKOUT_RATE = rate_limit("billing-checkout", Rate(10, 3600))


class InvalidWebhookError(AppError):
    status = 400
    code = "invalid_webhook"
    title = "Invalid webhook"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckoutRequest(StrictModel):
    plan: Literal["pro", "agency"]
    addons: list[Literal["engines_bing", "engines_regional"]] = Field(
        default_factory=list, max_length=2
    )


class RedirectOut(BaseModel):
    url: str


class PlanOut(BaseModel):
    code: str
    name: str
    purchasable: bool
    limits: dict[str, Any]


class Meter(BaseModel):
    used: int
    limit: int


class BillingOut(BaseModel):
    configured: bool
    plan: str
    addons: list[str]
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool
    grace_until: datetime | None
    has_customer: bool
    plans: list[PlanOut]
    addons_catalog: list[dict[str, Any]]
    usage: dict[str, Meter]


class InvoiceOut(BaseModel):
    id: str
    number: str | None
    status: str | None
    total: int
    currency: str
    created: datetime
    hosted_invoice_url: str | None
    invoice_pdf: str | None


def _stripe(request: Request) -> StripeClient:
    settings = request.app.state.settings
    if not service.configured(settings):
        raise BillingUnavailableError("Billing isn't configured on this server.")
    http: SafeHttpClient = request.app.state.job_runtime.extras["billing_http"]
    return StripeClient(http, settings.stripe_secret_key.get_secret_value())


async def _usage(db: DbSession, ctx: OrgContext, request: Request) -> dict[str, Meter]:
    plan = plan_of(ctx.organization)
    org = ctx.organization_id

    async def count(stmt: Any) -> int:
        return int((await db.execute(stmt)).scalar_one())

    gateway: LlmGateway = request.app.state.job_runtime.extras["llm"]
    return {
        "projects": Meter(
            used=await count(
                select(func.count()).where(
                    Project.organization_id == org, Project.deleted_at.is_(None)
                )
            ),
            limit=plan.max_projects,
        ),
        "members": Meter(
            used=await count(select(func.count()).where(Membership.organization_id == org)),
            limit=plan.max_members,
        ),
        "tracked_keywords": Meter(
            used=await count(select(func.count()).where(TrackedKeyword.organization_id == org)),
            limit=plan.max_tracked_keywords,
        ),
        "crawl_pages_this_month": Meter(
            used=await pages_used_this_month(db, org), limit=plan.max_crawl_pages_per_month
        ),
        "serp_requests_today": Meter(
            used=await count(
                select(func.coalesce(func.sum(SerpUsage.requests), 0)).where(
                    SerpUsage.organization_id == org, SerpUsage.day == datetime.now(UTC).date()
                )
            ),
            limit=plan.serp_requests_per_day,
        ),
        "ai_samples_this_month": Meter(
            used=await requests_this_month(db, org, "ai_sampling"), limit=plan.ai_prompts_per_month
        ),
        "llm_tokens_this_month": Meter(
            used=await gateway.tokens_used(db, org), limit=plan.llm_tokens_per_month
        ),
    }


@router.get("", response_model=BillingOut)
async def get_billing(ctx: BillingManage, db: DbSession, request: Request) -> BillingOut:
    settings = request.app.state.settings
    prices = service.price_map(settings)
    billing = await db.get(OrganizationBilling, ctx.organization_id)
    org = ctx.organization
    return BillingOut(
        configured=service.configured(settings),
        plan=org.plan_code,
        addons=list(org.addons or []),
        status=billing.status if billing else "none",
        current_period_end=billing.current_period_end if billing else None,
        cancel_at_period_end=billing.cancel_at_period_end if billing else False,
        grace_until=billing.grace_until if billing else None,
        has_customer=bool(billing and billing.stripe_customer_id),
        plans=[
            PlanOut(
                code=plan.code,
                name=plan.name,
                purchasable=plan.code in prices,
                limits={
                    "projects": plan.max_projects,
                    "members": plan.max_members,
                    "tracked_keywords": plan.max_tracked_keywords,
                    "crawl_pages_per_month": plan.max_crawl_pages_per_month,
                    "ai_prompts_per_month": plan.ai_prompts_per_month,
                    "rank_check_interval_hours": plan.rank_check_interval_hours,
                    "search_engines": sorted(e.value for e in plan.search_engines),
                    "ai_engines": sorted(e.value for e in plan.ai_engines),
                },
            )
            for plan in PLANS.values()
        ],
        addons_catalog=[
            {"code": code, "name": name, "purchasable": code in prices}
            for code, name in service.ADDONS.items()
        ],
        usage=await _usage(db, ctx, request),
    )


@router.post("/checkout", response_model=RedirectOut, dependencies=[Depends(_CHECKOUT_RATE)])
async def checkout(
    body: CheckoutRequest,
    ctx: BillingManage,
    user: RecentlyReauthenticated,
    db: DbSession,
    request: Request,
) -> RedirectOut:
    settings = request.app.state.settings
    stripe = _stripe(request)
    prices = service.price_map(settings)
    wanted = [body.plan, *dict.fromkeys(body.addons)]
    if any(code not in prices for code in wanted):
        raise BillingUnavailableError("That plan or add-on isn't available for purchase yet.")
    billing = await db.get(OrganizationBilling, ctx.organization_id)
    if billing and billing.status in service.LIVE_STATUSES:
        raise ConflictError("You already have a subscription; change it from Manage billing.")
    base = f"{settings.public_origin}/orgs/{ctx.organization_id}/billing"
    url = await stripe.checkout_session(
        org_id=str(ctx.organization_id),
        customer_id=billing.stripe_customer_id if billing else None,
        email=user.user.email,
        prices=[prices[c] for c in wanted],
        success_url=f"{base}?checkout=success",
        cancel_url=f"{base}?checkout=cancelled",
        # One Checkout Session per org, selection and minute (double clicks reuse it).
        idempotency=f"checkout:{ctx.organization_id}:{'+'.join(wanted)}:"
        f"{datetime.now(UTC):%Y%m%d%H%M}",
    )
    return RedirectOut(url=url)


@router.post("/portal", response_model=RedirectOut)
async def portal(ctx: BillingManage, db: DbSession, request: Request) -> RedirectOut:
    stripe = _stripe(request)
    billing = await db.get(OrganizationBilling, ctx.organization_id)
    if billing is None or not billing.stripe_customer_id:
        raise ConflictError("There's no billing account yet; choose a plan first.")
    url = await stripe.portal_session(
        customer_id=billing.stripe_customer_id,
        return_url=f"{request.app.state.settings.public_origin}/orgs/{ctx.organization_id}/billing",
    )
    return RedirectOut(url=url)


@router.get("/invoices", response_model=list[InvoiceOut])
async def invoices(ctx: BillingManage, db: DbSession, request: Request) -> list[InvoiceOut]:
    billing = await db.get(OrganizationBilling, ctx.organization_id)
    if billing is None or not billing.stripe_customer_id:
        return []
    rows = await _stripe(request).invoices(customer_id=billing.stripe_customer_id)
    return [
        InvoiceOut(
            id=str(i["id"]),
            number=i.get("number"),
            status=i.get("status"),
            total=int(i.get("total") or 0),
            currency=str(i.get("currency") or ""),
            created=datetime.fromtimestamp(int(i.get("created") or 0), UTC),
            hosted_invoice_url=_https(i.get("hosted_invoice_url")),
            invoice_pdf=_https(i.get("invoice_pdf")),
        )
        for i in rows
    ]


def _https(value: Any) -> str | None:
    """Only pass through https links (they are rendered as hrefs)."""
    return value if isinstance(value, str) and value.startswith("https://") else None


@webhook_router.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    secret = settings.stripe_webhook_secret.get_secret_value()
    if not secret:
        raise BillingUnavailableError("Billing isn't configured on this server.")
    payload = await request.body()
    try:
        event = verify_webhook(payload, request.headers.get("stripe-signature", ""), secret)
    except WebhookSignatureError as exc:
        raise InvalidWebhookError("The webhook signature is invalid.") from exc
    result = await service.handle_event(request.app.state.session_factory, settings, event)
    return {"result": result}
