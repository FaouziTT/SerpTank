"""Stripe billing: client encoding, webhook verification, checkout/portal, entitlements."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.config import Settings
from serptank.core.email import MemoryEmailSender
from serptank.modules.billing.models import OrganizationBilling
from serptank.modules.billing.service import expire_grace_periods, plan_from_items, price_map
from serptank.modules.billing.stripe import WebhookSignatureError, flatten, verify_webhook
from tests.support.api import STRONG_PASSWORD, Browser, FakeInternet, make_client, signed_in_browser

WEBHOOK_SECRET = "whsec_test_secret"
PRICES = "pro=price_pro,agency=price_agency,engines_bing=price_bing,engines_regional=price_reg"


@pytest.fixture
def api_settings(api_settings: Settings) -> Settings:
    return api_settings.model_copy(
        update={
            "stripe_secret_key": SecretStr("sk_test_123"),
            "stripe_webhook_secret": SecretStr(WEBHOOK_SECRET),
            "stripe_prices": PRICES,
        }
    )


@pytest.fixture
def stripe_api(internet: FakeInternet) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["authorization"] == "Bearer sk_test_123"
        if request.url.path == "/v1/checkout/sessions":
            return httpx.Response(
                200, json={"id": "cs_1", "url": "https://checkout.stripe.com/c/pay/cs_1"}
            )
        if request.url.path == "/v1/billing_portal/sessions":
            return httpx.Response(200, json={"url": "https://billing.stripe.com/p/session/1"})
        if request.url.path == "/v1/invoices":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "in_1",
                            "number": "ST-0001",
                            "status": "paid",
                            "total": 4900,
                            "currency": "usd",
                            "created": 1790000000,
                            "hosted_invoice_url": "https://invoice.stripe.com/i/1",
                            "invoice_pdf": "javascript:alert(1)",
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"error": {"type": "invalid_request_error"}})

    internet.handlers["api.stripe.com"] = handler
    return seen


def signed(
    event: dict[str, Any], secret: str = WEBHOOK_SECRET, at: int | None = None
) -> tuple[bytes, str]:
    body = json.dumps(event).encode()
    ts = at if at is not None else int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={ts},v1={sig}"


def subscription_event(org: str, kind: str, status: str, prices: list[str]) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": kind,
        "data": {
            "object": {
                "id": f"sub_{org}", "customer": f"cus_{org}", "status": status,
                "metadata": {"org_id": org}, "cancel_at_period_end": False,
                "items": {"data": [
                    {"price": {"id": p}, "current_period_end": 1790000000} for p in prices
                ]},
            }
        },
    }  # fmt: skip


async def post_webhook(api_app: FastAPI, event: dict[str, Any], **kw: Any) -> httpx.Response:
    body, header = signed(event, **kw)
    async with make_client(api_app) as client:
        # No session, no CSRF token, hostile Origin: the path is signature-verified instead.
        return await client.post(
            "/api/v1/billing/stripe/webhook",
            content=body,
            headers={"stripe-signature": header, "origin": "https://evil.example"},
        )


def test_flatten_and_prices() -> None:
    assert flatten({"a": {"b": 1}, "l": [{"x": 2}, {"x": 3}], "t": True, "n": None}) == [
        ("a[b]", "1"), ("l[0][x]", "2"), ("l[1][x]", "3"), ("t", "true"),
    ]  # fmt: skip
    prices = price_map(Settings(stripe_prices=PRICES + ",bogus=price_x, pro_bad"))
    assert prices == {
        "pro": "price_pro", "agency": "price_agency",
        "engines_bing": "price_bing", "engines_regional": "price_reg",
    }  # fmt: skip
    items = [
        {"price": {"id": "price_pro"}},
        {"price": {"id": "price_agency"}},
        {"price": {"id": "price_bing"}},
    ]
    assert plan_from_items(items, prices) == ("agency", ["engines_bing"])
    assert plan_from_items([{"price": {"id": "unknown"}}], prices) == ("free", [])


def test_webhook_signature() -> None:
    event = {"id": "evt_1", "type": "invoice.paid", "data": {"object": {}}}
    body, header = signed(event)
    assert verify_webhook(body, header, WEBHOOK_SECRET)["id"] == "evt_1"
    with pytest.raises(WebhookSignatureError):
        verify_webhook(body, header, "whsec_other")
    with pytest.raises(WebhookSignatureError):
        verify_webhook(body + b" ", header, WEBHOOK_SECRET)
    old_body, old_header = signed(event, at=int(time.time()) - 600)
    with pytest.raises(WebhookSignatureError):
        verify_webhook(old_body, old_header, WEBHOOK_SECRET)  # replay window
    with pytest.raises(WebhookSignatureError):
        verify_webhook(body, "v1=abc", WEBHOOK_SECRET)
    # Several v1 signatures (secret rotation): any match is accepted.
    rotated = header + ",v1=" + "0" * 64
    assert verify_webhook(body, rotated, WEBHOOK_SECRET)["type"] == "invoice.paid"


async def _org(api_app: FastAPI, outbox: MemoryEmailSender) -> tuple[Browser, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Billing"})).json()["id"]
    return b, org


async def test_billing_overview_checkout_and_portal(
    api_app: FastAPI, outbox: MemoryEmailSender, stripe_api: list[httpx.Request]
) -> None:
    b, org = await _org(api_app, outbox)
    overview = (await b.get(f"/api/v1/orgs/{org}/billing")).json()
    assert overview["configured"] is True
    assert overview["plan"] == "free"
    assert overview["status"] == "none"
    assert {p["code"]: p["purchasable"] for p in overview["plans"]} == {
        "free": False, "pro": True, "agency": True,
    }  # fmt: skip
    assert overview["usage"]["projects"] == {"used": 0, "limit": 1}
    assert (await b.post(f"/api/v1/orgs/{org}/billing/portal")).status_code == 409

    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    checkout = await b.post(
        f"/api/v1/orgs/{org}/billing/checkout", {"plan": "pro", "addons": ["engines_bing"]}
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["url"] == "https://checkout.stripe.com/c/pay/cs_1"
    form = parse_qs(stripe_api[-1].content.decode())
    assert form["client_reference_id"] == [org]
    assert form["subscription_data[metadata][org_id]"] == [org]
    assert form["line_items[0][price]"] == ["price_pro"]
    assert form["line_items[1][price]"] == ["price_bing"]
    assert form["mode"] == ["subscription"]
    assert stripe_api[-1].headers["idempotency-key"].startswith(f"checkout:{org}:pro+engines_bing:")
    bad = await b.post(f"/api/v1/orgs/{org}/billing/checkout", {"plan": "free"})
    assert bad.status_code == 422
    # Nothing changed locally: only a verified webhook can grant a plan.
    assert (await b.get(f"/api/v1/orgs/{org}/billing")).json()["plan"] == "free"

    completed = {
        "id": f"evt_{uuid.uuid4().hex}", "type": "checkout.session.completed",
        "data": {"object": {
            "client_reference_id": org, "customer": f"cus_{org}", "subscription": f"sub_{org}",
        }},
    }  # fmt: skip
    assert (await post_webhook(api_app, completed)).json() == {"result": "processed"}
    portal = await b.post(f"/api/v1/orgs/{org}/billing/portal")
    assert portal.json()["url"] == "https://billing.stripe.com/p/session/1"
    invoices = (await b.get(f"/api/v1/orgs/{org}/billing/invoices")).json()
    assert invoices[0]["number"] == "ST-0001"
    assert invoices[0]["invoice_pdf"] is None  # non-https links are dropped


async def test_webhooks_drive_entitlements_and_dunning(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    owner_engine: AsyncEngine,
) -> None:
    b, org = await _org(api_app, outbox)
    created = subscription_event(
        org, "customer.subscription.created", "active", ["price_pro", "price_bing"]
    )
    assert (await post_webhook(api_app, created)).json() == {"result": "processed"}
    assert (await post_webhook(api_app, created)).json() == {"result": "duplicate"}  # replay
    ent = (await b.get(f"/api/v1/orgs/{org}/entitlements")).json()
    assert ent["plan_code"] == "pro"
    assert "bing" in ent["search_engines"]
    billing = (await b.get(f"/api/v1/orgs/{org}/billing")).json()
    assert billing["addons"] == ["engines_bing"]
    assert billing["status"] == "active"
    assert billing["current_period_end"].startswith("2026-09")
    log = (await b.get(f"/api/v1/orgs/{org}/audit-events")).json()
    changes = [e for e in log if e["action"] == "billing.plan_changed"]
    assert changes
    assert changes[0]["details"]["to"] == "pro"

    # Forged or unsigned events change nothing.
    forged = subscription_event(org, "customer.subscription.updated", "active", ["price_agency"])
    assert (await post_webhook(api_app, forged, secret="whsec_attacker")).status_code == 400
    assert (await b.get(f"/api/v1/orgs/{org}/billing")).json()["plan"] == "pro"

    failed = {
        "id": f"evt_{uuid.uuid4().hex}", "type": "invoice.payment_failed",
        "data": {"object": {"parent": {"subscription_details": {"metadata": {"org_id": org}}}}},
    }  # fmt: skip
    await post_webhook(api_app, failed)
    state = (await b.get(f"/api/v1/orgs/{org}/billing")).json()
    assert state["status"] == "past_due"
    assert state["plan"] == "pro"  # grace period keeps paid features
    assert state["grace_until"] is not None
    # Grace ends: the scheduler drops the org to free.
    await owner_session.execute(
        update(OrganizationBilling)
        .where(OrganizationBilling.organization_id == uuid.UUID(org))
        .values(grace_until=datetime.now(UTC) - timedelta(minutes=1))
    )
    await owner_session.commit()
    async with async_sessionmaker(owner_engine, expire_on_commit=False)() as system:
        assert await expire_grace_periods(system) >= 1
    after = (await b.get(f"/api/v1/orgs/{org}/billing")).json()
    assert (after["plan"], after["addons"], after["status"]) == ("free", [], "unpaid")

    # A new subscription, then cancellation.
    renewed = subscription_event(org, "customer.subscription.updated", "active", ["price_agency"])
    await post_webhook(api_app, renewed)
    assert (await b.get(f"/api/v1/orgs/{org}/entitlements")).json()["plan_code"] == "agency"
    deleted = subscription_event(org, "customer.subscription.deleted", "active", ["price_agency"])
    await post_webhook(api_app, deleted)
    assert (await b.get(f"/api/v1/orgs/{org}/billing")).json()["plan"] == "free"
    unknown = {"id": f"evt_{uuid.uuid4().hex}", "type": "customer.created", "data": {"object": {}}}
    assert (await post_webhook(api_app, unknown)).json() == {"result": "ignored"}


async def test_billing_permissions_and_unconfigured(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, org = await _org(api_app, outbox)
    other, _ = await signed_in_browser(api_app, outbox)
    assert (await other.get(f"/api/v1/orgs/{org}/billing")).status_code == 404
    # Without Stripe credentials the server says so instead of pretending.
    api_app.state.settings = api_app.state.settings.model_copy(
        update={"stripe_secret_key": SecretStr(""), "stripe_webhook_secret": SecretStr("")}
    )
    overview = (await b.get(f"/api/v1/orgs/{org}/billing")).json()
    assert overview["configured"] is False
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    checkout = await b.post(f"/api/v1/orgs/{org}/billing/checkout", {"plan": "pro"})
    assert checkout.status_code == 503
    assert checkout.json()["code"] == "billing_unavailable"
    hook = await post_webhook(api_app, {"id": "evt_x", "type": "invoice.paid", "data": {}})
    assert hook.status_code == 503
