"""Minimal Stripe client over :class:`SafeHttpClient` (no SDK: every outbound call goes
through the SSRF-guarded client, CLAUDE.md), plus webhook signature verification.

Only what SerpTank needs: Checkout Sessions (subscription mode), Billing Portal
sessions, and invoice listing. Webhooks are verified per Stripe's scheme:
``Stripe-Signature: t=<ts>,v1=<hex>`` where ``v1 = HMAC_SHA256(secret, f"{t}.{body}")``,
with a 5-minute tolerance against replay.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import structlog

from serptank.core.errors import AppError
from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient

logger = structlog.get_logger(__name__)

API = "https://api.stripe.com/v1"
POLICY = EgressPolicy(max_response_bytes=2 * 1024 * 1024, total_timeout_s=30)
TOLERANCE_S = 300


class BillingUnavailableError(AppError):
    status = 503
    code = "billing_unavailable"
    title = "Billing is unavailable right now"


class WebhookSignatureError(Exception):
    """The webhook body wasn't signed by Stripe with our secret (or is too old)."""


def flatten(params: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    """Stripe's bracketed form encoding: {"a": {"b": 1}, "l": [{"x": 2}]} ->
    a[b]=1, l[0][x]=2."""
    out: list[tuple[str, str]] = []
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else key
        if isinstance(value, dict):
            out += flatten(value, name)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    out += flatten(item, f"{name}[{index}]")
                else:
                    out.append((f"{name}[{index}]", str(item)))
        elif isinstance(value, bool):
            out.append((name, "true" if value else "false"))
        elif value is not None:
            out.append((name, str(value)))
    return out


class StripeClient:
    def __init__(self, http: SafeHttpClient, secret_key: str) -> None:
        self.http = http
        self.secret_key = secret_key

    async def _call(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        idempotency: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "authorization": f"Bearer {self.secret_key}",
            "stripe-version": "2025-09-30.clover",
        }
        content = None
        url = f"{API}{path}"
        if method == "GET" and params:
            url = f"{url}?{urlencode(flatten(params))}"
        elif params is not None:
            headers["content-type"] = "application/x-www-form-urlencoded"
            content = urlencode(flatten(params)).encode()
        if idempotency:
            headers["idempotency-key"] = idempotency
        try:
            response = await self.http.request(
                method, url, headers=headers, content=content, policy=POLICY
            )
        except EgressError as exc:
            raise BillingUnavailableError("The payment provider is unreachable.") from exc
        try:
            data = json.loads(response.content)
        except ValueError as exc:
            raise BillingUnavailableError("The payment provider returned bad data.") from exc
        if response.status_code >= 400:  # noqa: PLR2004
            error = (data.get("error") or {}) if isinstance(data, dict) else {}
            logger.warning(
                "stripe_error",
                status=response.status_code,
                type=error.get("type"),
                code=error.get("code"),
            )
            raise BillingUnavailableError("The payment provider refused the request.")
        if not isinstance(data, dict):
            raise BillingUnavailableError("The payment provider returned bad data.")
        return data

    async def checkout_session(
        self,
        *,
        org_id: str,
        customer_id: str | None,
        email: str,
        prices: list[str],
        success_url: str,
        cancel_url: str,
        idempotency: str,
    ) -> str:
        params: dict[str, Any] = {
            "mode": "subscription",
            "client_reference_id": org_id,
            "line_items": [{"price": p, "quantity": 1} for p in prices],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "allow_promotion_codes": True,
            "subscription_data": {"metadata": {"org_id": org_id}},
            "metadata": {"org_id": org_id},
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["customer_email"] = email
        data = await self._call("POST", "/checkout/sessions", params, idempotency=idempotency)
        return str(data["url"])

    async def portal_session(self, *, customer_id: str, return_url: str) -> str:
        data = await self._call(
            "POST", "/billing_portal/sessions", {"customer": customer_id, "return_url": return_url}
        )
        return str(data["url"])

    async def invoices(self, *, customer_id: str, limit: int = 24) -> list[dict[str, Any]]:
        data = await self._call("GET", "/invoices", {"customer": customer_id, "limit": limit})
        return [i for i in data.get("data", []) if isinstance(i, dict)]


def verify_webhook(
    payload: bytes, header: str, secret: str, now: float | None = None
) -> dict[str, Any]:
    """Return the parsed event if ``header`` is a valid, fresh Stripe signature."""
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        key, _, value = item.strip().partition("=")
        parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts["t"][0])
    except (KeyError, ValueError) as exc:
        raise WebhookSignatureError("missing timestamp") from exc
    if abs((now or time.time()) - timestamp) > TOLERANCE_S:
        raise WebhookSignatureError("timestamp outside tolerance")
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", [])):
        raise WebhookSignatureError("signature mismatch")
    try:
        event = json.loads(payload)
    except ValueError as exc:
        raise WebhookSignatureError("body is not JSON") from exc
    if not isinstance(event, dict) or "id" not in event or "type" not in event:
        raise WebhookSignatureError("not an event")
    return event
