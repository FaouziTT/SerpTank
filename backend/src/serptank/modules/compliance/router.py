"""Public product data and data-subject rights.

* ``GET    /public/plans``       pricing-page data (limits from the plan catalog)
* ``GET    /public/config``      public client config (Turnstile site key, billing on/off)
* ``GET    /auth/me/export``     personal data export (JSON attachment, step-up)
* ``DELETE /auth/me``            delete the account (step-up; last-owner guard)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.billing.entitlements import PLANS
from serptank.modules.billing.service import ADDONS, configured
from serptank.modules.compliance import service
from serptank.modules.identity.deps import DbSession, Identity, RecentlyReauthenticated
from serptank.modules.identity.sessions import clear_session_cookie

public_router = APIRouter(prefix="/public", tags=["public"])
account_router = APIRouter(prefix="/auth/me", tags=["account"])
_EXPORT_RATE = rate_limit("account-export", Rate(10, 3600))


class PublicPlan(BaseModel):
    code: str
    name: str
    monthly_price: float | None  # None: shown at checkout / contact us
    currency: str
    limits: dict[str, Any]


class PublicPricing(BaseModel):
    plans: list[PublicPlan]
    addons: list[dict[str, Any]]
    billing_enabled: bool


class Subprocessor(BaseModel):
    name: str
    purpose: str
    data: str


class PublicConfig(BaseModel):
    turnstile_site_key: str | None
    billing_enabled: bool
    # Only the third parties this deployment is actually configured to use.
    subprocessors: list[Subprocessor]


def subprocessors(settings: Any) -> list[Subprocessor]:
    def secret(name: str) -> bool:
        value = getattr(settings, name, None)
        return bool(value.get_secret_value() if value is not None else "")

    out: list[Subprocessor] = []
    if configured(settings):
        out.append(
            Subprocessor(
                name="Stripe",
                purpose="Payments and invoicing",
                data="Billing contact, payment method (held by Stripe)",
            )
        )
    if secret("dataforseo_password"):
        out.append(
            Subprocessor(
                name="DataForSEO",
                purpose="Public search result pages",
                data="Keywords and locations queried (no personal data)",
            )
        )
    if settings.rawhtml_endpoint:
        out.append(
            Subprocessor(
                name="SERP fetch vendor",
                purpose="Public search result pages",
                data="Keywords and locations queried (no personal data)",
            )
        )
    if secret("openai_api_key") and settings.llm_enabled:
        out.append(
            Subprocessor(
                name="OpenAI",
                purpose="AI suggestions and ChatGPT answer sampling",
                data="Page titles/headings you analyse; your tracked prompts",
            )
        )
    if secret("perplexity_api_key") and settings.llm_enabled:
        out.append(
            Subprocessor(
                name="Perplexity", purpose="AI answer sampling", data="Your tracked prompts"
            )
        )
    if settings.google_data_client_id or settings.google_client_id:
        out.append(
            Subprocessor(
                name="Google",
                purpose="Sign-in and the Google APIs you connect",
                data="Account identifiers; Search Console/Analytics data you authorise",
            )
        )
    if secret("turnstile_secret"):
        out.append(
            Subprocessor(
                name="Cloudflare Turnstile",
                purpose="Bot protection on sign-in",
                data="Browser signals during challenges",
            )
        )
    if settings.email_backend == "smtp":
        out.append(
            Subprocessor(
                name="Email delivery provider",
                purpose="Transactional email",
                data="Email address and message content",
            )
        )
    return out


def _display_prices(spec: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in filter(None, (p.strip() for p in spec.split(","))):
        code, _, value = part.partition("=")
        try:
            out[code.strip()] = float(value)
        except ValueError:
            continue
    return out


@public_router.get("/plans", response_model=PublicPricing)
async def public_plans(request: Request) -> PublicPricing:
    settings = request.app.state.settings
    prices = _display_prices(settings.pricing_display)
    return PublicPricing(
        plans=[
            PublicPlan(
                code=plan.code,
                name=plan.name,
                monthly_price=0.0 if plan.code == "free" else prices.get(plan.code),
                currency=settings.pricing_currency,
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
        addons=[
            {"code": code, "name": name, "monthly_price": prices.get(code)}
            for code, name in ADDONS.items()
        ],
        billing_enabled=configured(settings),
    )


@public_router.get("/config", response_model=PublicConfig)
async def public_config(request: Request) -> PublicConfig:
    settings = request.app.state.settings
    return PublicConfig(
        turnstile_site_key=settings.turnstile_site_key or None,
        billing_enabled=configured(settings),
        subprocessors=subprocessors(settings),
    )


@account_router.get("/export", response_class=Response, dependencies=[Depends(_EXPORT_RATE)])
async def export_my_data(
    auth: RecentlyReauthenticated, db: DbSession, identity: Identity
) -> Response:
    sessions = [
        {
            "created_at": datetime.fromtimestamp(s.created_at, UTC).isoformat(),
            "last_seen_at": datetime.fromtimestamp(s.last_seen_at, UTC).isoformat(),
            "ip": s.ip,
            "user_agent": s.user_agent,
        }
        for s in await identity.store.list_for_user(auth.user.id)
    ]
    data = await service.personal_data(db, auth.user, sessions)
    return Response(
        json.dumps(data, indent=2),
        media_type="application/json",
        headers={
            "content-disposition": 'attachment; filename="serptank-my-data.json"',
            "cache-control": "no-store",
        },
    )


@account_router.delete("", status_code=204)
async def delete_my_account(
    auth: RecentlyReauthenticated, db: DbSession, identity: Identity, response: Response
) -> None:
    await service.delete_account(db, auth.user)
    await identity.store.revoke_all(auth.user.id)
    clear_session_cookie(response, identity.settings)
