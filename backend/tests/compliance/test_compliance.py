"""Public pricing/config, personal data export, account deletion and retention."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.config import Settings
from serptank.core.email import MemoryEmailSender
from serptank.core.models import MemberRole
from serptank.modules.compliance.service import purge_expired
from serptank.modules.identity.models import User
from serptank.modules.tenancy.models import Membership, Organization
from tests.support.api import (
    STRONG_PASSWORD,
    Browser,
    create_org_with_member,
    login,
    make_client,
    signed_in_browser,
)


@pytest.fixture
def api_settings(api_settings: Settings) -> Settings:
    return api_settings.model_copy(
        update={
            "pricing_display": "pro=49,agency=199,engines_bing=19",
            "turnstile_site_key": "0x4AAA",
        }
    )


async def test_public_pricing_and_config(api_app: FastAPI) -> None:
    async with make_client(api_app) as anonymous:
        pricing = (await anonymous.get("/api/v1/public/plans")).json()
        config = (await anonymous.get("/api/v1/public/config")).json()
    prices = {p["code"]: p["monthly_price"] for p in pricing["plans"]}
    assert prices == {"free": 0.0, "pro": 49.0, "agency": 199.0}
    assert pricing["plans"][0]["limits"]["search_engines"] == ["google"]
    assert {a["code"]: a["monthly_price"] for a in pricing["addons"]} == {
        "engines_bing": 19.0,
        "engines_regional": None,  # not priced: the page says "contact us", never a guess
    }
    assert pricing["billing_enabled"] is False
    assert config["turnstile_site_key"] == "0x4AAA"
    assert config["billing_enabled"] is False
    names = [p["name"] for p in config["subprocessors"]]
    assert names == ["Google"]  # only what this deployment actually uses


async def test_personal_data_export(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    await b.post("/api/v1/orgs", {"name": "Mine"})
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    response = await b.get("/api/v1/auth/me/export")
    assert response.status_code == 200, response.text
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert data["profile"]["email"] == email
    assert data["profile"]["password_set"] is True
    assert data["memberships"][0]["organization"] == "Mine"
    assert data["memberships"][0]["role"] == "owner"
    assert len(data["sessions"]) >= 1
    assert any(e["action"] == "auth.login" for e in data["security_events"])
    assert "password_hash" not in response.text


async def test_account_deletion_and_retention(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    owner_engine: AsyncEngine,
) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Solo"})).json()["id"]
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    blocked = await b.delete("/api/v1/auth/me")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "last_owner"
    assert blocked.json()["organizations"] == ["Solo"]

    assert (await b.delete(f"/api/v1/orgs/{org}")).status_code == 204
    deleted = await b.delete("/api/v1/auth/me")
    assert deleted.status_code == 204, deleted.text
    assert (await b.get("/api/v1/auth/session")).status_code == 401
    user = (
        (await owner_session.execute(select(User).where(User.email.like("deleted+%"))))
        .scalars()
        .all()
    )
    anonymised = [u for u in user if u.deleted_at is not None and u.full_name == ""]
    assert anonymised
    assert all(u.password_hash is None for u in anonymised)
    # The address is free again, and the old credentials no longer work.
    fresh = make_client(api_app, ip="198.51.100.250")
    again = Browser(fresh)
    await again.refresh_csrf()
    assert (await login(again, email)).status_code == 401

    # Retention: 31 days later the org and the anonymised user are purged.
    await owner_session.execute(
        update(Organization)
        .where(Organization.id == uuid.UUID(org))
        .values(deleted_at=datetime.now(UTC) - timedelta(days=31))
    )
    await owner_session.execute(
        update(User)
        .where(User.id.in_([u.id for u in anonymised]))
        .values(deleted_at=datetime.now(UTC) - timedelta(days=31))
    )
    await owner_session.commit()
    async with async_sessionmaker(owner_engine, expire_on_commit=False)() as system:
        purged = await purge_expired(system, 30)
    assert purged["organizations"] >= 1
    assert purged["users"] >= 1
    owner_session.expire_all()
    assert await owner_session.get(Organization, uuid.UUID(org)) is None


async def test_deletion_leaves_shared_orgs(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    me = (await b.get("/api/v1/auth/session")).json()["user"]["id"]
    other, _ = await signed_in_browser(api_app, outbox)
    other_id = (await other.get("/api/v1/auth/session")).json()["user"]["id"]
    shared = await create_org_with_member(owner_session, uuid.UUID(other_id), MemberRole.OWNER)
    owner_session.add(
        Membership(organization_id=shared, user_id=uuid.UUID(me), role=MemberRole.EDITOR)
    )
    await owner_session.commit()
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    assert (await b.delete("/api/v1/auth/me")).status_code == 204
    members = (await other.get(f"/api/v1/orgs/{shared}/members")).json()
    assert [m["role"] for m in members] == ["owner"]
