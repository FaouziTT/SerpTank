"""Search Presence, exports with signed links, alerts and notifications end to end."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.email import MemoryEmailSender
from serptank.core.models import uuid7
from serptank.modules.ai_visibility.models import AiObservation, AiPrompt
from serptank.modules.audit.models import AuditIssue, Severity
from serptank.modules.crawler.models import Crawl, CrawlStatus
from serptank.modules.integrations.models import GscDaily, UrlInspection, VitalsDaily
from serptank.modules.jobs.models import Job
from serptank.modules.jobs.service import InProcessDispatcher
from serptank.modules.reports import router as reports_router
from serptank.modules.reports.scheduling import enqueue_due_alert_checks
from serptank.modules.search_data.collector import CollectorRouter
from serptank.modules.search_data.models import RankObservation, TrackedKeyword
from serptank.modules.tenancy.models import Organization
from tests.search_data.fakes import FakeVendor
from tests.support.api import Browser, make_client, signed_in_browser

DOMAIN = "example-shop.com"


@pytest.fixture
def vendor(api_app: FastAPI) -> FakeVendor:
    fake = FakeVendor()
    api_app.state.job_runtime.extras["serp"] = CollectorRouter(
        adapters={"fake": fake}, order={"*": ["fake"]}, global_daily_requests=10_000
    )
    return fake


async def _setup(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> tuple[Browser, str, str, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Reports"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.commit()
    market = {"country": "US", "language": "en", "search_engines": ["google", "bing"]}
    project = (
        await b.post(
            f"/api/v1/orgs/{org}/projects", {"name": "Shop", "domain": DOMAIN, "markets": [market]}
        )
    ).json()
    base = f"/api/v1/orgs/{org}/projects/{project['id']}"
    return b, org, project["id"], project["markets"][0]["id"], base


async def _drain(api_app: FastAPI) -> None:
    dispatcher = api_app.state.job_dispatcher
    assert isinstance(dispatcher, InProcessDispatcher)
    await dispatcher.drain()


async def test_presence_dashboard(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market, base = await _setup(api_app, outbox, owner_session)
    empty = (await b.get(f"{base}/presence")).json()
    assert empty["score"] is None  # no data -> no score, nothing invented
    assert empty["gsc"] is None
    assert empty["audit"] is None
    # Unique keywords: the public SERP cache is shared across tests for the day.
    tag = uuid.uuid4().hex[:8]
    await b.post(
        f"{base}/keywords", {"market_id": market, "keywords": [f"shoes {tag}", f"boots {tag}"]}
    )
    await b.post(f"{base}/keywords/check")
    await _drain(api_app)
    today = datetime.now(UTC).date()
    await owner_session.execute(
        insert(GscDaily),
        [
            {
                "id": uuid7(),
                "organization_id": uuid.UUID(org),
                "project_id": uuid.UUID(project),
                "date": today - timedelta(days=d),
                "query": "trail shoes",
                "page": f"https://{DOMAIN}/t",
                "country": "usa",
                "device": "desktop",
                "clicks": 2,
                "impressions": 100,
                "position": 12.0,
            }
            for d in (1, 2, 40)
        ],
    )
    owner_session.add(
        Crawl(
            organization_id=uuid.UUID(org),
            project_id=uuid.UUID(project),
            status=CrawlStatus.COMPLETED,
            start_url=f"https://{DOMAIN}/",
            max_pages=5,
            domain_verified=True,
            score=81.0,
            pages_fetched=5,
        )
    )
    await owner_session.commit()
    data = (await b.get(f"{base}/presence", params={"market_id": market})).json()
    engines = {e["engine"]: e for e in data["engines"]}
    assert data["engines"][0]["engine"] == "google"
    assert engines["google"]["keywords"] == 2
    assert engines["google"]["distribution"] == {"top3": 2}  # FakeVendor ranks us #2
    assert 0 < engines["google"]["share_of_voice"] < 1
    assert data["score"] is not None
    assert data["score_parts"]["ai"] is None
    assert data["gsc"]["current"]["clicks"] == 4
    assert data["gsc"]["previous"]["clicks"] == 2
    assert data["opportunities"][0]["query"] == "trail shoes"
    assert data["audit"]["score"] == 81.0
    assert data["vitals"] is None
    other, _ = await signed_in_browser(api_app, outbox)
    assert (await other.get(f"{base}/presence")).status_code == 404


async def test_exports_with_signed_links(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, _, _, market, base = await _setup(api_app, outbox, owner_session)
    await b.post(
        f"{base}/keywords", {"market_id": market, "keywords": [f"=cmd|calc {uuid.uuid4().hex[:6]}"]}
    )
    await b.post(f"{base}/keywords/check")
    await _drain(api_app)
    started = await b.post(f"{base}/exports", {"kind": "rankings"})
    assert started.status_code == 202, started.text
    export_id = started.json()["export"]["id"]
    too_early = await b.post(f"{base}/exports/{export_id}/link")
    assert too_early.status_code in {200, 409}
    await _drain(api_app)
    listed = (await b.get(f"{base}/exports")).json()
    assert listed[0]["status"] == "completed"
    assert listed[0]["rows"] >= 1
    assert "content" not in listed[0]
    link = (await b.post(f"{base}/exports/{export_id}/link")).json()
    # Works without any session cookie (e.g. a script), until it expires.
    async with make_client(api_app) as anonymous:
        response = await anonymous.get(link["url"])
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]
        assert response.headers["cache-control"] == "no-store"
        text = response.content.decode("utf-8")
        assert text.startswith("﻿date,keyword,engine")
        assert "'=cmd|calc" in text  # formula neutralised
        tampered = link["url"].replace(export_id, str(uuid.uuid4()))
        assert (await anonymous.get(tampered)).status_code == 403
        forged = link["url"][:-4] + "0000"
        assert (await anonymous.get(forged)).status_code == 403
        missing_sig = link["url"].split("&sig=")[0]
        assert (await anonymous.get(missing_sig)).status_code == 422
    assert (await b.post(f"{base}/exports", {"kind": "passwords"})).status_code == 422
    other, _ = await signed_in_browser(api_app, outbox)
    assert (await other.post(f"{base}/exports/{export_id}/link")).status_code == 404


async def _seed_rank_drop(owner_session: AsyncSession, org: str, project: str, market: str) -> None:
    kid = uuid7()
    owner_session.add(
        TrackedKeyword(
            id=kid,
            organization_id=uuid.UUID(org),
            project_id=uuid.UUID(project),
            market_id=uuid.UUID(market),
            keyword="trail shoes",
            tags=[],
        )
    )
    await owner_session.flush()
    today = datetime.now(UTC).date()
    await owner_session.execute(
        insert(RankObservation),
        [
            {
                "id": uuid7(),
                "date": day,
                "organization_id": uuid.UUID(org),
                "project_id": uuid.UUID(project),
                "keyword_id": kid,
                "engine": "google",
                "source": "serp",
                "domain": DOMAIN,
                "is_own": True,
                "position": pos,
                "features": [],
            }
            for day, pos in ((today - timedelta(days=1), 4.0), (today, 14.0))
        ],
    )
    await owner_session.commit()


async def test_alerts_notifications_and_email(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The test transport buffers whole responses, so keep the SSE window tiny.
    monkeypatch.setattr(reports_router, "STREAM_MAX_SECONDS", 0.2)
    monkeypatch.setattr(reports_router, "POLL_SECONDS", 0.05)
    b, org, project, market, base = await _setup(api_app, outbox, owner_session)
    rules = {r["kind"]: r for r in (await b.get(f"{base}/alerts")).json()}
    assert rules["rank_drop"] == {
        "kind": "rank_drop", "label": "Ranking drops on Google",
        "threshold_meaning": "positions lost", "configured": False, "active": False,
        "threshold": 3.0, "email": False, "last_evaluated_at": None,
    }  # fmt: skip
    put = await b.client.put(
        f"{base}/alerts/rank_drop",
        json={"active": True, "threshold": 5, "email": True},
        headers=b._headers(),
    )
    assert put.status_code == 204
    bad = await b.client.put(f"{base}/alerts/nonsense", json={}, headers=b._headers())
    assert bad.status_code == 422
    await _seed_rank_drop(owner_session, org, project, market)
    sent_before = len(outbox.outbox)

    job = await b.post(f"{base}/alerts/evaluate")
    assert job.status_code == 202
    await _drain(api_app)
    inbox = (await b.get(f"/api/v1/orgs/{org}/notifications")).json()
    assert inbox["unread"] == 1
    note = inbox["items"][0]
    assert note["title"] == "“trail shoes” fell from #4 to #14"
    assert note["link"].endswith("/keywords")
    alerts_mail = outbox.outbox[sent_before:]
    assert len(alerts_mail) == 1
    assert alerts_mail[0].subject.startswith("[SerpTank] “trail shoes” fell")

    # Evaluating again never duplicates.
    await b.post(f"{base}/alerts/evaluate")
    await _drain(api_app)
    assert (await b.get(f"/api/v1/orgs/{org}/notifications")).json()["unread"] == 1
    assert len(outbox.outbox) == sent_before + 1

    async with b.client.stream("GET", f"/api/v1/orgs/{org}/notifications/stream") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        first = "".join([chunk async for chunk in stream.aiter_text()])
    assert "event: notifications" in first
    assert '"unread":1' in first
    assert "event: timeout" in first

    assert (await b.post(f"/api/v1/orgs/{org}/notifications/{note['id']}/read")).status_code == 204
    assert (await b.get(f"/api/v1/orgs/{org}/notifications")).json()["unread"] == 0
    assert (
        await b.post(f"/api/v1/orgs/{org}/notifications/{uuid.uuid4()}/read")
    ).status_code == 404
    assert (await b.post(f"/api/v1/orgs/{org}/notifications/read-all")).status_code == 204
    other, _ = await signed_in_browser(api_app, outbox)
    assert (await other.get(f"/api/v1/orgs/{org}/notifications")).status_code == 404


async def test_alert_scheduler(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    owner_engine: AsyncEngine,
) -> None:
    b, _, project, _, base = await _setup(api_app, outbox, owner_session)

    class Recorder:
        def __init__(self) -> None:
            self.projects: list[uuid.UUID | None] = []

        async def dispatch(self, job: Job) -> None:
            self.projects.append(job.project_id)

    system = async_sessionmaker(owner_engine, expire_on_commit=False)
    recorder = Recorder()
    await enqueue_due_alert_checks(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project) not in recorder.projects  # no rules yet
    await b.client.put(f"{base}/alerts/audit_regression", json={}, headers=b._headers())
    await enqueue_due_alert_checks(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project) in recorder.projects


async def test_other_alert_kinds_and_exports(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, org, project, market, base = await _setup(api_app, outbox, owner_session)
    org_id, project_id = uuid.UUID(org), uuid.UUID(project)
    now = datetime.now(UTC)
    today = now.date()
    # Two audits: the score fell 12 points and a critical issue appeared.
    old = Crawl(
        id=uuid7(),
        organization_id=org_id,
        project_id=project_id,
        status=CrawlStatus.COMPLETED,
        start_url=f"https://{DOMAIN}/",
        max_pages=5,
        domain_verified=True,
        score=90.0,
        created_at=now - timedelta(days=7),
    )
    new = Crawl(
        id=uuid7(),
        organization_id=org_id,
        project_id=project_id,
        status=CrawlStatus.COMPLETED,
        start_url=f"https://{DOMAIN}/",
        max_pages=5,
        domain_verified=True,
        score=78.0,
        created_at=now,
    )
    owner_session.add_all([old, new])
    await owner_session.flush()
    owner_session.add(
        AuditIssue(
            organization_id=org_id,
            crawl_id=new.id,
            rule_id="homepage_noindex",
            severity=Severity.CRITICAL,
            url=f"https://{DOMAIN}/",
        )
    )
    # A page that dropped out of Google's index, and poor field vitals.
    for when, verdict in ((now - timedelta(days=3), "PASS"), (now, "NEUTRAL")):
        owner_session.add(
            UrlInspection(
                organization_id=org_id,
                project_id=project_id,
                url=f"https://{DOMAIN}/p",
                inspected_at=when,
                verdict=verdict,
                raw={},
            )
        )
    await owner_session.execute(
        insert(VitalsDaily).values(
            id=uuid7(),
            organization_id=org_id,
            project_id=project_id,
            date=today,
            target=f"https://{DOMAIN}",
            scope="origin",
            form_factor="PHONE",
            lcp_ms=6000.0,
            inp_ms=900.0,
            cls=0.5,
        )
    )
    # AI citation lost: cited yesterday, not today.
    prompt = AiPrompt(
        id=uuid7(),
        organization_id=org_id,
        project_id=project_id,
        market_id=uuid.UUID(market),
        prompt="Best shoes?",
        engines=[],
        active=True,
    )
    owner_session.add(prompt)
    await owner_session.flush()
    await owner_session.execute(
        insert(AiObservation),
        [
            {
                "id": uuid7(),
                "date": day,
                "organization_id": org_id,
                "project_id": project_id,
                "prompt_id": prompt.id,
                "engine": "chatgpt",
                "sample": 0,
                "answered": True,
                "mentioned": cited,
                "cited": cited,
                "competitors": {},
                "citations": [],
                "excerpt": "",
                "model": "m",
            }
            for day, cited in ((today - timedelta(days=1), True), (today, False))
        ],
    )
    await owner_session.commit()
    for kind in ("audit_regression", "indexing_lost", "cwv_poor", "ai_citation_lost"):
        response = await b.client.put(
            f"{base}/alerts/{kind}", json={"active": True}, headers=b._headers()
        )
        assert response.status_code == 204
    await b.post(f"{base}/alerts/evaluate")
    await _drain(api_app)
    titles = {
        n["title"] for n in (await b.get(f"/api/v1/orgs/{org}/notifications")).json()["items"]
    }
    assert "Audit score fell 12 points to 78" in titles
    assert "1 new critical audit issue(s)" in titles
    assert "A page is no longer indexed by Google" in titles
    assert "Core Web Vitals are poor (PHONE)" in titles
    assert "No longer cited by chatgpt" in titles
    rules = {r["kind"]: r for r in (await b.get(f"{base}/alerts")).json()}
    assert rules["cwv_poor"]["threshold"] is None
    assert rules["audit_regression"]["last_evaluated_at"] is not None

    for kind, header in (
        ("audit_issues", "rule,severity,scope,url"),
        ("ai_answers", "date,engine,prompt"),
        ("gsc_queries", "query,page,clicks"),
    ):
        started = await b.post(f"{base}/exports", {"kind": kind})
        await _drain(api_app)
        link = (await b.post(f"{base}/exports/{started.json()['export']['id']}/link")).json()
        async with make_client(api_app) as anonymous:
            text = (await anonymous.get(link["url"])).content.decode("utf-8")
        assert text.startswith("﻿" + header), kind
