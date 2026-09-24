"""On-page API end to end: optimizer, AI rewrite, briefs, keyword map, cannibalization."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.core.models import uuid7
from serptank.modules.crawler.models import Crawl, CrawlLink, CrawlPage, CrawlStatus
from serptank.modules.integrations.models import GscDaily
from serptank.modules.jobs.service import InProcessDispatcher
from serptank.modules.llm.gateway import LlmGateway
from serptank.modules.search_data.collector import CollectorRouter
from serptank.modules.tenancy.models import Organization
from tests.llm.fakes import FakeLlm
from tests.onpage.site import COMPETITORS, KEYWORD, install
from tests.search_data.fakes import FakeVendor
from tests.support.api import Browser, FakeInternet, signed_in_browser

DOMAIN = "example-shop.com"
OWN_URL = "https://www.example-shop.com/trail"


@pytest.fixture
def vendor(api_app: FastAPI, internet: FakeInternet) -> FakeVendor:
    install(internet)
    fake = FakeVendor(ranking=[*COMPETITORS[:2], "www.example-shop.com", *COMPETITORS[2:]])
    api_app.state.job_runtime.extras["serp"] = CollectorRouter(
        adapters={"fake": fake}, order={"*": ["fake"]}, global_daily_requests=10_000
    )
    return fake


@pytest.fixture
def llm(api_app: FastAPI) -> FakeLlm:
    fake = FakeLlm(
        reply=json.dumps(
            {
                "title": "Trail Running Shoes: Grip, Cushioning & Fit",
                "meta_description": "Compare our trail running shoes by grip and cushioning.",
                "h1": "Trail running shoes",
                "sections_to_add": ["Cushioning and stack height"],
                "notes": [],
            }
        )
    )
    api_app.state.job_runtime.extras["llm"] = LlmGateway(provider=fake)
    return fake


async def _setup(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> tuple[Browser, str, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "OnPage"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.commit()
    market = {"country": "US", "language": "en", "search_engines": ["google"]}
    project = (
        await b.post(
            f"/api/v1/orgs/{org}/projects", {"name": "Shop", "domain": DOMAIN, "markets": [market]}
        )
    ).json()
    return b, org, project["id"], project["markets"][0]["id"]


async def _drain(api_app: FastAPI) -> None:
    dispatcher = api_app.state.job_dispatcher
    assert isinstance(dispatcher, InProcessDispatcher)
    await dispatcher.drain()


async def _crawl(owner_session: AsyncSession, org: str, project: str) -> None:
    """A completed crawl where one relevant page could link to OWN_URL but doesn't."""
    org_id, project_id = uuid.UUID(org), uuid.UUID(project)
    crawl = Crawl(
        id=uuid7(),
        organization_id=org_id,
        project_id=project_id,
        status=CrawlStatus.COMPLETED,
        start_url=f"https://{DOMAIN}/",
        max_pages=10,
        domain_verified=True,
    )
    owner_session.add(crawl)
    await owner_session.flush()
    pages = {
        "own": (OWN_URL, "Shoes", 1),
        "guide": ("https://www.example-shop.com/guide", "Trail running guide", 4),
        "linker": ("https://www.example-shop.com/blog", "Running shoes for trail races", 2),
        "other": ("https://www.example-shop.com/about", "About us", 3),
    }
    ids = {}
    for key, (url, title, inlinks) in pages.items():
        ids[key] = uuid7()
        owner_session.add(
            CrawlPage(
                id=ids[key],
                organization_id=org_id,
                crawl_id=crawl.id,
                url=url,
                found_via="link",
                status_code=200,
                indexable_google=True,
                title=title,
                inlinks=inlinks,
            )
        )
    await owner_session.flush()
    await owner_session.execute(
        insert(CrawlLink).values(
            id=uuid7(),
            organization_id=org_id,
            crawl_id=crawl.id,
            source_page_id=ids["linker"],
            target_url=OWN_URL,
            internal=True,
        )
    )
    await owner_session.commit()


async def test_optimizer_rewrite_and_isolation(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    vendor: FakeVendor,
    llm: FakeLlm,
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    await _crawl(owner_session, org, project)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    off_site = await b.post(
        f"{base}/optimizer", {"market_id": market, "keyword": KEYWORD, "url": "https://evil.com/"}
    )
    assert off_site.status_code == 422
    assert off_site.json()["code"] == "invalid_page_url"

    started = await b.post(
        f"{base}/optimizer", {"market_id": market, "keyword": "Trail Running Shoes", "url": OWN_URL}
    )
    assert started.status_code == 202, started.text
    opt_id = started.json()["optimization"]["id"]
    assert started.json()["optimization"]["status"] == "running"
    await _drain(api_app)
    out = (await b.get(f"{base}/optimizer/{opt_id}")).json()
    assert out["status"] == "completed", out
    assert out["keyword"] == KEYWORD
    result = out["result"]
    assert 0 < out["score"] < 50
    competitors = {c["domain"]: c for c in result["competitors"]}
    assert competitors["www.blocked.example"]["skipped"] == "robots"  # robots.txt honoured
    assert competitors["www.gearlab.example"]["word_count"] > 100
    assert "www.example-shop.com" not in competitors
    assert result["serp"]["own_position"] == 3
    checks = {c["id"]: c for c in result["checks"]}
    assert checks["title_keyword"]["status"] == "fail"
    assert checks["internal_links"]["status"] == "warn"  # 1 inlink in the crawl
    suggestions = [s["url"] for s in checks["internal_links"]["detail"]["suggestions"]]
    assert suggestions == ["https://www.example-shop.com/guide"]  # blog already links
    assert "text" not in result["page"]
    listed = (await b.get(f"{base}/optimizer")).json()
    assert [row["id"] for row in listed] == [opt_id]

    rewritten = await b.post(f"{base}/optimizer/{opt_id}/rewrite")
    assert rewritten.status_code == 200, rewritten.text
    assert rewritten.json()["rewrite"]["h1"] == "Trail running shoes"
    prompt = llm.calls[0]["user"]
    assert "<untrusted>" in prompt
    assert "Current title: Shoes" in prompt
    usage = (await b.get(f"/api/v1/orgs/{org}/ai-usage")).json()
    assert usage["available"] is True
    assert usage["tokens_used"] == 150
    assert usage["by_purpose"][0]["purpose"] == "onpage_rewrite"

    # Another tenant sees nothing.
    other, _ = await signed_in_browser(api_app, outbox)
    other_org = (await other.post("/api/v1/orgs", {"name": "Other"})).json()["id"]
    foreign = f"/api/v1/orgs/{other_org}/projects/{project}/optimizer/{opt_id}"
    assert (await other.get(foreign)).status_code == 404
    assert (await other.get(f"{base}/optimizer/{opt_id}")).status_code == 404


async def test_optimizer_failures_are_recorded(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    started = await b.post(
        f"{base}/optimizer",
        {"market_id": market, "keyword": KEYWORD, "url": "https://example-shop.com/x"},
    )
    await _drain(api_app)  # example-shop.com (no www) isn't served by the fake internet
    out = (await b.get(f"{base}/optimizer/{started.json()['optimization']['id']}")).json()
    assert out["status"] == "failed"
    assert out["error"].startswith("The site's robots.txt returned a server error")
    no_rewrite = await b.post(f"{base}/optimizer/{out['id']}/rewrite")
    assert no_rewrite.status_code == 409
    usage = (await b.get(f"/api/v1/orgs/{org}/ai-usage")).json()
    assert usage["tokens_used"] == 0


async def test_rewrite_without_llm_is_honest(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    started = await b.post(
        f"{base}/optimizer", {"market_id": market, "keyword": KEYWORD, "url": OWN_URL}
    )
    await _drain(api_app)
    opt = started.json()["optimization"]["id"]
    response = await b.post(f"{base}/optimizer/{opt}/rewrite")  # no OpenAI key in tests
    assert response.status_code == 503
    assert response.json()["code"] == "llm_unavailable"


async def test_brief_and_markdown_export(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    started = await b.post(f"{base}/briefs", {"market_id": market, "keyword": KEYWORD})
    assert started.status_code == 202, started.text
    brief_id = started.json()["brief"]["id"]
    assert (await b.get(f"{base}/briefs/{brief_id}/markdown")).status_code == 409
    await _drain(api_app)
    brief = (await b.get(f"{base}/briefs/{brief_id}")).json()
    assert brief["status"] == "completed"
    data: dict[str, Any] = brief["brief"]
    assert data["outline"][0]["heading"] == "How to choose trail running shoes"
    assert "What are good shoes?" in data["questions"]
    assert data["schema_type"] == "Article"
    assert data["word_count_range"] is not None
    md = await b.get(f"{base}/briefs/{brief_id}/markdown")
    assert md.headers["content-type"].startswith("text/markdown")
    assert "attachment" in md.headers["content-disposition"]
    assert "# Content brief: trail running shoes" in md.text
    assert [r["id"] for r in (await b.get(f"{base}/briefs")).json()] == [brief_id]


async def test_brief_without_serp_budget(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    api_app.state.job_runtime.extras["serp"] = CollectorRouter(
        adapters={}, order={}, global_daily_requests=0
    )
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    # A query nobody fetched today (the public SERP cache is shared across tests/orgs).
    fresh = f"uncached query {uuid.uuid4().hex[:8]}"
    started = await b.post(f"{base}/briefs", {"market_id": market, "keyword": fresh})
    await _drain(api_app)
    brief = (await b.get(f"{base}/briefs/{started.json()['brief']['id']}")).json()
    assert brief["status"] == "completed"
    assert brief["brief"]["outline"] == []
    assert len(brief["brief"]["notes"]) >= 2


async def test_keyword_map_and_cannibalization(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    empty = (await b.get(f"{base}/cannibalization")).json()
    assert empty == {"has_search_console_data": False, "window_days": 28, "issues": []}
    await b.post(f"{base}/keywords", {"market_id": market, "keywords": [KEYWORD, "hiking boots"]})
    rows = {r["keyword"]: r for r in (await b.get(f"{base}/keyword-map")).json()}
    assert rows[KEYWORD]["status"] == "unassigned"
    kid = rows[KEYWORD]["keyword_id"]
    bad = await b.client.put(
        f"{base}/keyword-map/{kid}",
        json={"target_url": "https://other.com/"},
        headers=b._headers(),
    )
    assert bad.status_code == 422
    ok = await b.client.put(
        f"{base}/keyword-map/{kid}", json={"target_url": OWN_URL}, headers=b._headers()
    )
    assert ok.status_code == 204
    today = datetime.now(UTC).date()
    await owner_session.execute(
        insert(GscDaily),
        [
            {
                "id": uuid7(),
                "organization_id": uuid.UUID(org),
                "project_id": uuid.UUID(project),
                "date": today - timedelta(days=2),
                "query": KEYWORD,
                "page": page,
                "country": "usa",
                "device": "desktop",
                "clicks": clicks,
                "impressions": imps,
                "position": pos,
            }
            for page, clicks, imps, pos in (
                (OWN_URL, 5, 120, 6.0),
                ("https://www.example-shop.com/blog", 3, 80, 9.0),
                ("https://www.example-shop.com/tiny", 0, 5, 40.0),
            )
        ],
    )
    await owner_session.commit()
    report = (await b.get(f"{base}/cannibalization")).json()
    assert report["has_search_console_data"] is True
    issue = report["issues"][0]
    assert issue["query"] == KEYWORD
    assert issue["impressions"] == 205
    assert [p["page"] for p in issue["pages"]] == [OWN_URL, "https://www.example-shop.com/blog"]

    # The rank check records GSC's page, so the map shows it aligned.
    job = await b.post(f"{base}/keywords/check")
    assert job.status_code == 202
    await _drain(api_app)
    rows = {r["keyword"]: r for r in (await b.get(f"{base}/keyword-map")).json()}
    assert rows[KEYWORD]["ranking_url"] == OWN_URL
    assert rows[KEYWORD]["status"] == "aligned"
    assert rows["hiking boots"]["status"] == "unassigned"
