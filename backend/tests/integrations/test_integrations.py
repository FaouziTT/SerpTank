"""Connections, OAuth, property linking, syncs, indexing and imports (fake providers)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.modules.integrations.models import Connection, ConnectionStatus
from serptank.modules.jobs.service import InProcessDispatcher
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization
from tests.integrations.fakes import FakeBing, FakeGoogle, FakeIndexNow
from tests.support.api import Browser, FakeInternet, signed_in_browser

DOMAIN = "example-shop.com"


@pytest.fixture
def google(internet: FakeInternet) -> FakeGoogle:
    fake = FakeGoogle()
    fake.install(internet)
    return fake


@pytest.fixture
def bing(internet: FakeInternet) -> FakeBing:
    fake = FakeBing()
    fake.install(internet)
    return fake


@pytest.fixture
def indexnow(internet: FakeInternet) -> FakeIndexNow:
    fake = FakeIndexNow()
    fake.install(internet)
    return fake


async def _org_project(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> tuple[Browser, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Shop"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.commit()
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "Shop", "domain": DOMAIN})
    ).json()["id"]
    return b, org, project


async def _connect_google(
    b: Browser, org: str, google: FakeGoogle, features: list[str] | None = None
) -> httpx.Response:
    start = await b.post(
        f"/api/v1/orgs/{org}/integrations/google/start", {"features": features or ["gsc", "ga4"]}
    )
    assert start.status_code == 200, start.text
    params = parse_qs(urlsplit(start.json()["authorization_url"]).query)
    assert params["client_id"] == ["data-client.apps.googleusercontent.com"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["access_type"] == ["offline"]
    google.code_challenge = params["code_challenge"][0]
    return await b.get(
        "/api/v1/integrations/google/callback",
        params={"state": params["state"][0], "code": "good-code"},
    )


async def _drain(api_app: FastAPI) -> None:
    dispatcher = api_app.state.job_dispatcher
    assert isinstance(dispatcher, InProcessDispatcher)
    await dispatcher.drain()


async def _job(api_app: FastAPI, b: Browser, org: str, path: str) -> dict[str, Any]:
    started = await b.post(path)
    assert started.status_code == 202, started.text
    await _drain(api_app)
    return (await b.get(f"/api/v1/orgs/{org}/jobs/{started.json()['id']}")).json()  # type: ignore[no-any-return]


# ----------------------------------------------------------------------- connections
async def test_google_oauth_flow_stores_encrypted_grant(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, _ = await _org_project(api_app, outbox, owner_session)
    callback = await _connect_google(b, org, google)
    assert callback.status_code == 303
    assert callback.headers["location"] == f"/orgs/{org}/integrations?connected=google"
    overview = (await b.get(f"/api/v1/orgs/{org}/integrations")).json()
    assert overview["google_available"] is True
    connection = overview["connections"][0]
    assert connection["provider"] == "google"
    assert connection["status"] == "active"
    assert connection["account_label"] == "owner@example-shop.com"
    assert connection["features"] == ["ga4", "gsc"]
    stored = (
        (await owner_session.execute(text("SELECT credentials FROM connections"))).scalars().all()
    )
    assert all("refresh-1" not in value and value.startswith("v1.") for value in stored)
    audit = [e["action"] for e in (await b.get(f"/api/v1/orgs/{org}/audit-events")).json()]
    assert "integration.connected" in audit


async def test_oauth_state_is_single_use_and_bound_to_user(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, _ = await _org_project(api_app, outbox, owner_session)
    start = await b.post(f"/api/v1/orgs/{org}/integrations/google/start", {"features": ["gsc"]})
    params = parse_qs(urlsplit(start.json()["authorization_url"]).query)
    google.code_challenge = params["code_challenge"][0]
    # Another signed-in user can't complete this user's flow.
    other, _ = await signed_in_browser(api_app, outbox)
    stolen = await other.get(
        "/api/v1/integrations/google/callback",
        params={"state": params["state"][0], "code": "good-code"},
    )
    assert "error=google_state_invalid" in stolen.headers["location"]
    # The state was consumed by that attempt: replay fails too.
    replay = await b.get(
        "/api/v1/integrations/google/callback",
        params={"state": params["state"][0], "code": "good-code"},
    )
    assert "error=google_state_invalid" in replay.headers["location"]
    denied = await b.get(
        "/api/v1/integrations/google/callback", params={"state": "nope", "error": "access_denied"}
    )
    assert "error=google_state_invalid" in denied.headers["location"]
    assert (await b.get(f"/api/v1/orgs/{org}/integrations")).json()["connections"] == []


async def test_bad_pkce_verifier_is_rejected(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, _ = await _org_project(api_app, outbox, owner_session)
    start = await b.post(f"/api/v1/orgs/{org}/integrations/google/start", {"features": ["gsc"]})
    params = parse_qs(urlsplit(start.json()["authorization_url"]).query)
    google.code_challenge = "not-the-real-challenge"
    callback = await b.get(
        "/api/v1/integrations/google/callback",
        params={"state": params["state"][0], "code": "good-code"},
    )
    assert "error=google_request_failed" in callback.headers["location"]


async def test_bing_connection_validates_key(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, bing: FakeBing
) -> None:
    b, org, _ = await _org_project(api_app, outbox, owner_session)
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    bad = await b.client.put(
        f"/api/v1/orgs/{org}/integrations/bing",
        json={"api_key": "wrong-key-000000000"},
        headers=headers,
    )
    assert bad.status_code == 502
    assert bad.json()["provider_code"] == "bing_unauthorized"
    ok = await b.client.put(
        f"/api/v1/orgs/{org}/integrations/bing", json={"api_key": bing.key}, headers=headers
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "active"
    sites = (await b.get(f"/api/v1/orgs/{org}/integrations/bing/sites")).json()
    assert [s["id"] for s in sites] == ["https://example-shop.com/"]  # unverified sites hidden


async def test_viewers_cannot_connect(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, org, _ = await _org_project(api_app, outbox, owner_session)
    viewer, viewer_email = await signed_in_browser(api_app, outbox)
    await b.post(f"/api/v1/orgs/{org}/invitations", {"email": viewer_email, "role": "viewer"})
    token = outbox.outbox[-1].text.split("token=")[1].split()[0]
    await viewer.post("/api/v1/invitations/accept", {"token": token})
    assert (
        await viewer.post(f"/api/v1/orgs/{org}/integrations/google/start", {"features": ["gsc"]})
    ).status_code == 403
    assert (await viewer.get(f"/api/v1/orgs/{org}/integrations")).status_code == 200


# --------------------------------------------------------------- sources and syncs
async def test_gsc_link_verifies_ownership_and_sync_is_idempotent(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    await _connect_google(b, org, google)
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    base = f"/api/v1/orgs/{org}/projects/{project}"
    props = (await b.get(f"/api/v1/orgs/{org}/integrations/google/properties")).json()
    assert {p["id"] for p in props["gsc_sites"]} == {
        "sc-domain:example-shop.com",
        "https://other-site.com/",
    }
    assert props["ga4_properties"][0]["id"] == "properties/123"
    wrong = await b.client.put(
        f"{base}/sources/gsc", json={"property_id": "https://other-site.com/"}, headers=headers
    )
    assert wrong.status_code == 409
    linked = await b.client.put(
        f"{base}/sources/gsc", json={"property_id": "sc-domain:example-shop.com"}, headers=headers
    )
    assert linked.status_code == 200, linked.text
    project_out = (await b.get(base)).json()
    assert project_out["verified"] is True  # GSC owner proves ownership
    assert project_out["verification_method"] == "gsc"

    job = await _job(api_app, b, org, f"{base}/sources/gsc/sync")
    assert job["status"] == "succeeded", job
    days = job["result"]["days"]
    assert days == 90
    count = (await owner_session.execute(text("SELECT count(*) FROM gsc_daily"))).scalar_one()
    # Re-running replaces the overlapping days instead of duplicating them.
    job2 = await _job(api_app, b, org, f"{base}/sources/gsc/sync")
    assert job2["status"] == "succeeded"
    assert job2["result"]["days"] == 4
    assert (
        await owner_session.execute(text("SELECT count(*) FROM gsc_daily"))
    ).scalar_one() == count
    perf = (await b.get(f"{base}/performance", params={"days": 28})).json()
    assert perf["has_data"] is True
    assert perf["top_queries"][0]["key"] == "query 0"
    assert perf["clicks"] > 0
    assert perf["top_pages"]
    bing_perf = (await b.get(f"{base}/performance", params={"source": "bing"})).json()
    assert bing_perf["has_data"] is False  # honest empty state, no estimates


async def test_revoked_grant_fails_job_and_flags_connection(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    await _connect_google(b, org, google)
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    base = f"/api/v1/orgs/{org}/projects/{project}"
    await b.client.put(
        f"{base}/sources/gsc", json={"property_id": "sc-domain:example-shop.com"}, headers=headers
    )
    # Access token expired and the user revoked SerpTank in their Google account.
    # The cached access token is rejected (401) and refreshing is impossible.
    google.issued_access.clear()
    google.refresh_valid = False
    job = await _job(api_app, b, org, f"{base}/sources/gsc/sync")
    assert job["status"] == "failed"
    assert job["error_code"] in {"gsc_unauthorized", "google_reauth_required"}
    state = (
        await owner_session.execute(
            select(Connection.status).where(Connection.organization_id == uuid.UUID(org))
        )
    ).scalar_one()
    assert state is ConnectionStatus.REAUTH_REQUIRED
    overview = (await b.get(f"/api/v1/orgs/{org}/integrations")).json()
    assert overview["connections"][0]["status"] == "reauth_required"


async def test_ga4_and_bing_syncs(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    google: FakeGoogle,
    bing: FakeBing,
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    await _connect_google(b, org, google)
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    await b.client.put(
        f"/api/v1/orgs/{org}/integrations/bing", json={"api_key": bing.key}, headers=headers
    )
    base = f"/api/v1/orgs/{org}/projects/{project}"
    assert (
        await b.client.put(
            f"{base}/sources/ga4", json={"property_id": "properties/999"}, headers=headers
        )
    ).status_code == 409
    assert (
        await b.client.put(
            f"{base}/sources/ga4", json={"property_id": "properties/123"}, headers=headers
        )
    ).status_code == 200
    assert (
        await b.client.put(
            f"{base}/sources/bing", json={"property_id": "https://unverified.com/"}, headers=headers
        )
    ).status_code == 409
    assert (
        await b.client.put(
            f"{base}/sources/bing",
            json={"property_id": "https://example-shop.com/"},
            headers=headers,
        )
    ).status_code == 200
    ga4 = await _job(api_app, b, org, f"{base}/sources/ga4/sync")
    assert ga4["status"] == "succeeded", ga4
    assert ga4["result"]["rows"] == 1
    bing_job = await _job(api_app, b, org, f"{base}/sources/bing/sync")
    assert bing_job["status"] == "succeeded", bing_job
    rows = (
        await owner_session.execute(
            text("SELECT query, date, position FROM bing_daily ORDER BY date")
        )
    ).all()
    assert [r[0] for r in rows] == ["blue widgets", "red widgets"]
    assert str(rows[0][1]) == "2025-09-20"
    assert rows[1][2] is None  # -1 means "no position" in Bing's API
    perf = (await b.get(f"{base}/performance", params={"source": "bing", "days": 480})).json()
    assert perf["clicks"] == 9
    sources = {s["kind"]: s for s in (await b.get(f"{base}/sources")).json()}
    assert sources["bing"]["last_sync_status"] == "ok"
    # Disconnecting Bing removes its project links.
    assert (await b.delete(f"/api/v1/orgs/{org}/integrations/bing")).status_code == 204
    assert "bing" not in {s["kind"] for s in (await b.get(f"{base}/sources")).json()}


async def test_vitals_sync_is_honest_about_missing_data(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    job = await _job(api_app, b, org, f"{base}/sources/vitals/sync")
    assert job["status"] == "succeeded", job
    vitals = (await b.get(f"{base}/vitals")).json()
    origin = {v["form_factor"]: v for v in vitals if v["scope"] == "origin"}
    assert origin["PHONE"]["assessment"] == "poor"  # LCP 4.8 s
    assert origin["DESKTOP"]["assessment"] == "good"
    assert origin["PHONE"]["cls"] == 0.05


# ------------------------------------------------------------------------- indexing
async def test_indexnow_requires_ownership_and_key_file(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    internet: FakeInternet,
    indexnow: FakeIndexNow,
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    key_source = (await b.post(f"{base}/indexnow")).json()
    key = key_source["property_id"]
    assert key_source["settings"]["key_location"] == f"https://{DOMAIN}/{key}.txt"
    assert (await b.post(f"{base}/indexnow")).json()["property_id"] == key  # idempotent
    unverified = await b.post(f"{base}/submissions", {"urls": [f"https://{DOMAIN}/a"]})
    assert unverified.status_code == 409
    await owner_session.execute(
        update(Project)
        .where(Project.id == uuid.UUID(project))
        .values(domain_verified_at=datetime.now(UTC))
    )
    await owner_session.commit()
    no_key_file = await b.post(f"{base}/submissions", {"urls": [f"https://{DOMAIN}/a"]})
    assert no_key_file.status_code == 409

    internet.handlers[DOMAIN] = lambda r: httpx.Response(
        200, text=key if r.url.path == f"/{key}.txt" else ""
    )
    internet.handlers[f"www.{DOMAIN}"] = internet.handlers[DOMAIN]
    assert (await b.post(f"{base}/indexnow/verify")).json()["settings"]["verified"] is True
    foreign = await b.post(
        f"{base}/submissions", {"urls": [f"https://{DOMAIN}/a", "https://victim.example/"]}
    )
    assert foreign.status_code == 422
    assert foreign.json()["rejected"] == ["https://victim.example/"]
    ok = await b.post(
        f"{base}/submissions",
        {"urls": [f"https://{DOMAIN}/a", f"https://{DOMAIN}/a#frag", f"https://www.{DOMAIN}/b"]},
    )
    assert ok.status_code == 200, ok.text
    assert {r["host"] for r in indexnow.received} == {DOMAIN, f"www.{DOMAIN}"}
    first = next(r for r in indexnow.received if r["host"] == DOMAIN)
    assert first == {
        "host": DOMAIN,
        "key": key,
        "keyLocation": f"https://{DOMAIN}/{key}.txt",
        "urlList": [f"https://{DOMAIN}/a"],
    }
    log = (await b.get(f"{base}/submissions")).json()
    assert {e["status_code"] for e in log} == {200}
    indexnow.status = 403
    refused = await b.post(f"{base}/submissions", {"urls": [f"https://{DOMAIN}/c"]})
    assert refused.status_code == 502
    assert refused.json()["provider_code"] == "indexnow_403"
    auto = await b.client.patch(
        f"{base}/indexnow",
        json={"auto_submit": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf},
    )
    assert auto.json()["settings"]["auto_submit"] is True


async def test_url_inspection_and_sitemaps(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    await _connect_google(b, org, google)
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    base = f"/api/v1/orgs/{org}/projects/{project}"
    assert (
        await b.post(f"{base}/inspections", {"url": f"https://{DOMAIN}/p"})
    ).status_code == 409  # no source
    await b.client.put(
        f"{base}/sources/gsc", json={"property_id": "sc-domain:example-shop.com"}, headers=headers
    )
    inspected = await b.post(f"{base}/inspections", {"url": f"https://{DOMAIN}/p"})
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["coverage_state"] == "Submitted and indexed"
    assert inspected.json()["last_crawl_time"].startswith("2026-09-20")
    assert (
        await b.post(f"{base}/inspections", {"url": "https://elsewhere.org/p"})
    ).status_code == 422
    assert len((await b.get(f"{base}/inspections")).json()) == 1
    sitemaps = (await b.get(f"{base}/gsc/sitemaps")).json()
    assert sitemaps[0]["warnings"] == 2
    # Submitting sitemaps needs the extra write permission, which wasn't granted.
    refused = await b.post(f"{base}/gsc/sitemaps", {"url": f"https://{DOMAIN}/sitemap.xml"})
    assert refused.status_code == 502
    assert refused.json()["provider_code"] == "google_scope_missing"
    assert google.sitemap_submissions == []


async def test_disconnect_google_revokes(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, _ = await _org_project(api_app, outbox, owner_session)
    await _connect_google(b, org, google)
    assert (await b.delete(f"/api/v1/orgs/{org}/integrations/google")).status_code == 204
    assert google.revoked == ["refresh-1"]
    assert (await b.get(f"/api/v1/orgs/{org}/integrations")).json()["connections"] == []


async def test_integration_data_is_tenant_isolated(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, google: FakeGoogle
) -> None:
    b, org, project = await _org_project(api_app, outbox, owner_session)
    await _connect_google(b, org, google)
    other, _ = await signed_in_browser(api_app, outbox)
    other_org = (await other.post("/api/v1/orgs", {"name": "Other"})).json()["id"]
    assert (await other.get(f"/api/v1/orgs/{org}/integrations")).status_code == 404
    assert (
        await other.get(f"/api/v1/orgs/{other_org}/projects/{project}/performance")
    ).status_code == 404
    assert (await other.get(f"/api/v1/orgs/{other_org}/integrations")).json()["connections"] == []
