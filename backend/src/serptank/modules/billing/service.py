"""Billing: Stripe is the source of truth; we mirror it and derive entitlements.

* **Plans as data** - :data:`entitlements.PLANS` holds limits; ``SERPTANK_STRIPE_PRICES``
  maps plan and add-on codes to Stripe price ids. Nothing is granted client-side:
  the org's ``plan_code``/``addons`` change only from verified Stripe webhooks.
* **Webhooks** are signature-verified, recorded by event id (replays are no-ops) and
  applied to the org named in the event's ``org_id`` metadata / client reference, which
  only our server sets when creating the Checkout Session.
* **Dunning** - a failed payment starts a grace period (``billing_grace_days``); paid
  features stay on until it ends, then the org drops to free. Tracking for engines the
  plan no longer includes stops; history is kept.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.audit import record_audit_event
from serptank.core.config import Settings
from serptank.core.db import bind_identity
from serptank.modules.billing.entitlements import PLANS
from serptank.modules.billing.models import OrganizationBilling, StripeEvent
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

ADDONS = {
    "engines_bing": "Bing, Yahoo & DuckDuckGo",
    "engines_regional": "Yandex, Baidu, Naver & Seznam",
}
PAID_PLANS = ("pro", "agency")  # ascending tier
LIVE_STATUSES = frozenset({"active", "trialing", "past_due"})


def price_map(settings: Settings) -> dict[str, str]:
    """{"pro": "price_..", ...} from ``stripe_prices`` (unknown codes are ignored)."""
    out: dict[str, str] = {}
    for part in filter(None, (p.strip() for p in settings.stripe_prices.split(","))):
        code, _, price = part.partition("=")
        if (code in PLANS or code in ADDONS) and price.strip():
            out[code.strip()] = price.strip()
    return out


def configured(settings: Settings) -> bool:
    return bool(settings.stripe_secret_key.get_secret_value() and price_map(settings))


async def get_billing(db: AsyncSession, org_id: uuid.UUID) -> OrganizationBilling:
    billing = await db.get(OrganizationBilling, org_id)
    if billing is None:
        billing = OrganizationBilling(
            organization_id=org_id, status="none", plan_code="free", addons=[]
        )
        db.add(billing)
    return billing


def _ts(value: Any) -> datetime | None:
    return datetime.fromtimestamp(int(value), UTC) if isinstance(value, int | float) else None


def plan_from_items(items: list[dict[str, Any]], prices: dict[str, str]) -> tuple[str, list[str]]:
    """Highest paid plan and the add-ons present in a subscription's items."""
    by_price = {price: code for code, price in prices.items()}
    codes = {by_price.get(str((i.get("price") or {}).get("id", ""))) for i in items}
    plan = next((p for p in reversed(PAID_PLANS) if p in codes), "free")
    return plan, sorted(c for c in codes if c in ADDONS)


async def _apply(
    db: AsyncSession,
    org: Organization,
    billing: OrganizationBilling,
    *,
    plan: str,
    addons: list[str],
    reason: str,
) -> None:
    if (org.plan_code, sorted(org.addons or [])) != (plan, addons):
        record_audit_event(
            db,
            "billing.plan_changed",
            actor_user_id=None,
            organization_id=org.id,
            target_type="organization",
            target_id=org.id,
            details={"from": org.plan_code, "to": plan, "addons": addons, "reason": reason},
        )
    org.plan_code, org.addons = plan, addons
    billing.plan_code, billing.addons = plan, addons


async def apply_subscription(
    db: AsyncSession, org: Organization, subscription: dict[str, Any], prices: dict[str, str]
) -> None:
    billing = await get_billing(db, org.id)
    status = str(subscription.get("status", "none"))
    billing.stripe_subscription_id = str(subscription.get("id") or "") or None
    if subscription.get("customer"):
        billing.stripe_customer_id = str(subscription["customer"])
    billing.status = status
    billing.cancel_at_period_end = bool(subscription.get("cancel_at_period_end"))
    items = ((subscription.get("items") or {}).get("data")) or []
    billing.current_period_end = _ts(
        subscription.get("current_period_end")
        or (items[0].get("current_period_end") if items else None)
    )
    if status in LIVE_STATUSES:
        plan, addons = plan_from_items(items, prices)
        if status != "past_due":
            billing.grace_until = None
        await _apply(db, org, billing, plan=plan, addons=addons, reason=f"subscription {status}")
    else:  # canceled, unpaid, incomplete_expired, paused...
        billing.grace_until = None
        await _apply(db, org, billing, plan="free", addons=[], reason=f"subscription {status}")


def _org_id(obj: dict[str, Any]) -> str | None:
    candidates = [
        (obj.get("metadata") or {}).get("org_id"),
        obj.get("client_reference_id"),
        ((obj.get("subscription_details") or {}).get("metadata") or {}).get("org_id"),
        ((((obj.get("parent") or {}).get("subscription_details") or {}).get("metadata")) or {}).get(
            "org_id"
        ),
    ]
    return next((str(c) for c in candidates if c), None)


async def handle_event(
    factory: async_sessionmaker[AsyncSession], settings: Settings, event: dict[str, Any]
) -> str:
    """Apply one verified event. Returns "processed" | "duplicate" | "ignored"."""
    obj = ((event.get("data") or {}).get("object")) or {}
    raw_org = _org_id(obj) if isinstance(obj, dict) else None
    try:
        org_id = uuid.UUID(raw_org) if raw_org else None
    except ValueError:
        org_id = None
    async with factory() as db:
        if org_id is not None:
            await bind_identity(db, organization_id=org_id)
        stored = await db.execute(
            pg_insert(StripeEvent)
            .values(id=str(event["id"])[:80], type=str(event["type"])[:80], org_ref=org_id)
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(StripeEvent.id)
        )
        if stored.scalar_one_or_none() is None:
            return "duplicate"
        org = await db.get(Organization, org_id) if org_id else None
        if org is None:
            await db.commit()
            logger.info("stripe_event_without_org", type=event["type"])
            return "ignored"
        result = await _dispatch(db, settings, org, str(event["type"]), obj)
        await db.commit()
        return result


async def _dispatch(
    db: AsyncSession, settings: Settings, org: Organization, kind: str, obj: dict[str, Any]
) -> str:
    prices = price_map(settings)
    if kind == "checkout.session.completed":
        billing = await get_billing(db, org.id)
        billing.stripe_customer_id = str(obj.get("customer") or "") or billing.stripe_customer_id
        billing.stripe_subscription_id = (
            str(obj.get("subscription") or "") or billing.stripe_subscription_id
        )
        return "processed"
    if kind in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        if kind.endswith("deleted"):
            obj = {**obj, "status": "canceled"}
        await apply_subscription(db, org, obj, prices)
        return "processed"
    if kind == "invoice.payment_failed":
        billing = await get_billing(db, org.id)
        billing.status = "past_due"
        if billing.grace_until is None:
            billing.grace_until = datetime.now(UTC) + timedelta(days=settings.billing_grace_days)
        return "processed"
    if kind == "invoice.paid":
        billing = await get_billing(db, org.id)
        billing.grace_until = None
        if billing.status == "past_due":
            billing.status = "active"
        return "processed"
    return "ignored"


async def expire_grace_periods(system: AsyncSession, now: datetime | None = None) -> int:
    """Drop orgs whose payment grace period ended to free (scheduler session)."""
    now = now or datetime.now(UTC)
    expired = list(
        (
            await system.execute(
                select(OrganizationBilling.organization_id).where(
                    OrganizationBilling.grace_until.is_not(None),
                    OrganizationBilling.grace_until < now,
                )
            )
        ).scalars()
    )
    for org_id in expired:
        await system.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(plan_code="free", addons=[])
        )
        await system.execute(
            update(OrganizationBilling)
            .where(OrganizationBilling.organization_id == org_id)
            .values(plan_code="free", addons=[], status="unpaid", grace_until=None)
        )
        record_audit_event(
            system,
            "billing.plan_changed",
            actor_user_id=None,
            organization_id=org_id,
            target_type="organization",
            target_id=org_id,
            details={"to": "free", "reason": "payment grace period ended"},
        )
    await system.commit()
    return len(expired)
