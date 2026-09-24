"""End-to-end crawl -> audit through the API, against the fixture site (fake internet)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.modules.crawler.models import Crawl
from serptank.modules.jobs.service import InProcessDispatcher, execute_job
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization
from tests.crawler import fixture_site
from tests.support.api import Browser, FakeInternet, signed_in_browser


async def _setup(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    *,
    plan: str = "pro",
    engines: list[str] | None = None,
    domain: str = fixture_site.HOST,
) -> tuple[Browser, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Crawl Co"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code=plan)
    )
    await owner_session.commit()
    market = {"country": "US", "language": "en", "search_engines": engines or ["google", "bing"]}
    project = await b.post(
        f"/api/v1/orgs/{org}/projects", {"name": "Fixture", "domain": domain, "markets": [market]}
    )
    assert project.status_code == 201, project.text
    return b, org, project.json()["id"]


async def _run_crawl(api_app: FastAPI, b: Browser, org: str, project: str) -> dict[str, Any]:
    started = await b.post(f"/api/v1/orgs/{org}/projects/{project}/crawls")
    assert started.status_code == 202, started.text
    dispatcher = api_app.state.job_dispatcher
    assert isinstance(dispatcher, InProcessDispatcher)
    await dispatcher.drain()
    response = await b.get(f"/api/v1/orgs/{org}/jobs/{started.json()['job']['id']}")
    return response.json()  # type: ignore[no-any-return]


async def test_golden_audit_of_fixture_site(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    internet: FakeInternet,
) -> None:
    internet.handlers[fixture_site.HOST] = fixture_site.handler
    b, org, project = await _setup(api_app, outbox, owner_session)
    job = await _run_crawl(api_app, b, org, project)
    assert job["status"] == "succeeded", job
    assert job["progress"] == 1.0
    crawl_id = job["result"]["crawl_id"]
    base = f"/api/v1/orgs/{org}/projects/{project}/crawls"

    crawls = (await b.get(base)).json()
    assert crawls[0]["id"] == crawl_id
    crawl = crawls[0]
    assert crawl["status"] == "completed"
    assert crawl["domain_verified"] is False  # shallow crawl budget applies
    assert 0 < crawl["score"] < 100
    assert set(crawl["issue_counts"]["scores"]) == {"google", "bing"}

    google = {i["rule_id"]: i for i in (await b.get(f"{base}/{crawl_id}/issues")).json()}
    expected = {
        "soft_404_site",
        "http_not_redirected",
        "broken_pages",
        "broken_internal_links",
        "redirect_chains",
        "links_to_redirects",
        "noindex_in_sitemap",
        "blocked_in_sitemap",
        "non_200_in_sitemap",
        "orphan_pages",
        "duplicate_content",
        "title_duplicate",
        "title_too_long",
        "description_missing",
        "viewport_missing",
        "mixed_content",
        "structured_data_missing_required",
        "hreflang_missing_return",
        "internal_nofollow",
        "canonical_missing",
    }
    missing = expected - set(google)
    assert not missing, f"expected rules not triggered: {missing}"
    # Engine deltas are not part of the Google lens...
    assert "bing_blocked_pages" not in google
    assert "bing_crawl_delay" not in google
    # ...but appear through the Bing lens.
    bing = {i["rule_id"] for i in (await b.get(f"{base}/{crawl_id}/issues?engine=bing")).json()}
    assert {"bing_blocked_pages", "bing_crawl_delay"} <= bing
    # Things the fixture does right are not flagged.
    assert "homepage_blocked" not in google
    assert "homepage_noindex" not in google
    assert "sitemap_missing" not in google

    broken = google["broken_pages"]
    assert broken["severity"] == "high"
    assert broken["examples"] == [f"{fixture_site.BASE}/gone"]
    assert broken["fix"]

    detail = (await b.get(f"{base}/{crawl_id}/issues/redirect_chains")).json()
    assert detail["total"] == 1
    assert detail["items"][0]["url"] == f"{fixture_site.BASE}/old"
    assert detail["items"][0]["details"]["hops"] == 2

    pages = (await b.get(f"{base}/{crawl_id}/pages?kind=errors")).json()
    assert {p["url"] for p in pages["items"]} >= {f"{fixture_site.BASE}/gone"}
    blocked = (await b.get(f"{base}/{crawl_id}/pages?kind=blocked")).json()
    assert [p["url"] for p in blocked["items"]] == [f"{fixture_site.BASE}/private/secret"]
    search = (await b.get(f"{base}/{crawl_id}/pages", params={"q": "dup-"})).json()
    assert search["total"] == 2
    home = (
        await b.get(
            f"{base}/{crawl_id}/pages", params={"q": "fixture-site.com/", "kind": "indexable"}
        )
    ).json()
    assert any(p["url"] == f"{fixture_site.BASE}/" and p["inlinks"] >= 1 for p in home["items"])

    # Our crawler never fetched the robots-disallowed page or the external site.
    fetched = {str(r.url) for r in internet.requests}
    assert not any("/private/secret" in u for u in fetched)
    assert not any("other.example.org" in u for u in fetched)
    # Every request identified itself as SerpTankBot.
    assert all("SerpTankBot" in r.headers["user-agent"] for r in internet.requests)

    jobs = (
        await b.get(f"/api/v1/orgs/{org}/jobs", params={"project_id": project, "kind": "crawl"})
    ).json()
    assert [j["id"] for j in jobs] == [job["id"]]
    usage = (await b.get(f"{base}/usage")).json()
    assert usage["pages_used_this_month"] == crawl["pages_fetched"]


async def test_sse_stream_reports_final_state(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    internet.handlers[fixture_site.HOST] = fixture_site.handler
    b, org, project = await _setup(api_app, outbox, owner_session)
    job = await _run_crawl(api_app, b, org, project)
    async with b.client.stream("GET", f"/api/v1/orgs/{org}/jobs/{job['id']}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join([chunk async for chunk in response.aiter_text()])
    assert "event: job" in body
    assert '"status":"succeeded"' in body


async def test_robots_server_error_fails_honestly(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(503)
        return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

    internet.handlers["down-robots.com"] = broken
    b, org, project = await _setup(api_app, outbox, owner_session, domain="down-robots.com")
    job = await _run_crawl(api_app, b, org, project)
    assert job["status"] == "failed"
    assert job["error_code"] == "robots_unreachable"
    assert "robots.txt" in job["error_message"]
    crawls = (await b.get(f"/api/v1/orgs/{org}/projects/{project}/crawls")).json()
    assert crawls[0]["status"] == "failed"


async def test_one_active_crawl_and_cancel(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    class Parked:
        async def dispatch(self, job: object) -> None:  # queue it but never run it
            return None

    api_app.state.job_dispatcher = Parked()
    b, org, project = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}/crawls"
    first = await b.post(base)
    assert first.status_code == 202
    second = await b.post(base)
    assert second.status_code == 409
    job_id = first.json()["job"]["id"]
    cancelled = await b.post(f"/api/v1/orgs/{org}/jobs/{job_id}/cancel")
    assert cancelled.json()["status"] == "cancelled"
    assert (await b.post(f"/api/v1/orgs/{org}/jobs/{job_id}/cancel")).status_code == 409
    # A redelivered message for a cancelled job does nothing.
    await execute_job(api_app.state.job_runtime, uuid.UUID(org), uuid.UUID(job_id))
    assert (await b.get(f"/api/v1/orgs/{org}/jobs/{job_id}")).json()["status"] == "cancelled"
    assert (await b.post(base)).status_code == 202  # a new crawl may start now


async def test_monthly_budget_is_enforced(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    internet.handlers[fixture_site.HOST] = fixture_site.handler
    b, org, project = await _setup(api_app, outbox, owner_session, plan="free", engines=["google"])
    job = await _run_crawl(api_app, b, org, project)
    assert job["status"] == "succeeded"
    await owner_session.execute(
        update(Crawl).where(Crawl.organization_id == uuid.UUID(org)).values(pages_fetched=500)
    )
    await owner_session.commit()
    response = await b.post(f"/api/v1/orgs/{org}/projects/{project}/crawls")
    assert response.status_code == 402
    assert response.json()["code"] == "plan_upgrade_required"


async def test_audits_are_tenant_isolated(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    internet.handlers[fixture_site.HOST] = fixture_site.handler
    b, org, project = await _setup(api_app, outbox, owner_session)
    job = await _run_crawl(api_app, b, org, project)
    crawl_id = job["result"]["crawl_id"]
    other, _ = await signed_in_browser(api_app, outbox)
    other_org = (await other.post("/api/v1/orgs", {"name": "Other"})).json()["id"]
    # Foreign org in the URL: 404. Own org with a foreign crawl id: 404.
    assert (
        await other.get(f"/api/v1/orgs/{org}/projects/{project}/crawls/{crawl_id}")
    ).status_code == 404
    assert (await other.get(f"/api/v1/orgs/{other_org}/jobs/{job['id']}")).status_code == 404
    assert (
        await other.get(f"/api/v1/orgs/{other_org}/projects/{project}/crawls/{crawl_id}/issues")
    ).status_code == 404


async def test_scheduling_requires_verification(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, org, project = await _setup(api_app, outbox, owner_session)
    url = f"/api/v1/orgs/{org}/projects/{project}"
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    refused = await b.client.patch(url, json={"crawl_schedule": "weekly"}, headers=headers)
    assert refused.status_code == 409
    await owner_session.execute(
        update(Project)
        .where(Project.id == uuid.UUID(project))
        .values(domain_verified_at=datetime.now(UTC) - timedelta(days=1))
    )
    await owner_session.commit()
    ok = await b.client.patch(url, json={"crawl_schedule": "weekly"}, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["crawl_schedule"] == "weekly"


async def test_rendering_stage_feeds_the_audit(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    class StubRenderer:
        """Stands in for the renderer service: JavaScript rewrites the title."""

        async def render(
            self, url: str, *, user_agent: str, mobile: bool = False
        ) -> dict[str, Any]:
            html = fixture_site.PAGES.get(url.removeprefix(fixture_site.BASE), "")
            return {
                "url": url,
                "status": 200,
                "html": html.replace("<title>", "<title>JS "),
                "timed_out": False,
                "requests": [
                    {
                        "url": f"{fixture_site.BASE}/private/app.js",
                        "resource_type": "script",
                        "status": 200,
                    }
                ],
            }

    internet.handlers[fixture_site.HOST] = fixture_site.handler
    api_app.state.job_runtime.extras["renderer"] = StubRenderer()
    b, org, project = await _setup(api_app, outbox, owner_session, engines=["google"])
    job = await _run_crawl(api_app, b, org, project)
    assert job["status"] == "succeeded", job
    base = f"/api/v1/orgs/{org}/projects/{project}/crawls/{job['result']['crawl_id']}"
    crawl = (await b.get(base)).json()
    assert crawl["render_available"] is True
    issues = {i["rule_id"] for i in (await b.get(f"{base}/issues")).json()}
    assert {"js_changes_critical_tags", "resources_blocked_google"} <= issues
