"""Keywords, hybrid rank tracking, competitors, share of voice, research, opportunities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.core.models import uuid7
from serptank.modules.integrations.credentials import seal
from serptank.modules.integrations.models import Connection, GscDaily, Provider
from serptank.modules.jobs.service import InProcessDispatcher
from serptank.modules.search_data.collector import CollectorRouter
from serptank.modules.tenancy.models import Organization
from tests.integrations.fakes import FakeBing
from tests.search_data.fakes import FakeVendor
from tests.support.api import Browser, FakeInternet, signed_in_browser

DOMAIN = "example-shop.com"


@pytest.fixture
def vendor(api_app: FastAPI) -> FakeVendor:
    fake = FakeVendor(ai_cites=["www.example-shop.com"])
    api_app.state.job_runtime.extras["serp"] = CollectorRouter(
        adapters={"fake": fake}, order={"*": ["fake"]}, global_daily_requests=10_000
    )
    return fake


async def _setup(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, plan: str = "pro"
) -> tuple[Browser, str, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "KW"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code=plan)
    )
    await owner_session.commit()
    market = {
        "country": "US",
        "language": "en",
        "search_engines": ["google", "bing"] if plan != "free" else ["google"],
    }
    project = (
        await b.post(
            f"/api/v1/orgs/{org}/projects", {"name": "Shop", "domain": DOMAIN, "markets": [market]}
        )
    ).json()
    return b, org, project["id"], project["markets"][0]["id"]


async def _run(api_app: FastAPI, b: Browser, org: str, path: str) -> dict[str, Any]:
    started = await b.post(path)
    assert started.status_code == 202, started.text
    dispatcher = api_app.state.job_dispatcher
    assert isinstance(dispatcher, InProcessDispatcher)
    await dispatcher.drain()
    return (await b.get(f"/api/v1/orgs/{org}/jobs/{started.json()['id']}")).json()  # type: ignore[no-any-return]


async def test_hybrid_rank_tracking_with_competitors(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    added = await b.post(
        f"{base}/keywords",
        {
            "market_id": market,
            "keywords": ["Best Running Shoes", "best running shoes", "trail shoes"],
            "tags": ["core"],
        },
    )
    assert added.status_code == 201, added.text
    assert added.json()["added"] == 2
    again = await b.post(f"{base}/keywords", {"market_id": market, "keywords": ["trail shoes"]})
    assert again.json()["skipped_existing"] == 1
    assert (
        await b.post(f"{base}/competitors", {"domain": "https://www.rival.com/"})
    ).status_code == 201
    assert (await b.post(f"{base}/competitors", {"domain": DOMAIN})).status_code == 409
    # First-party Google data from Search Console for one keyword.
    today = datetime.now(UTC).date()
    await owner_session.execute(
        insert(GscDaily),
        [
            {
                "id": uuid7(),
                "organization_id": uuid.UUID(org),
                "project_id": uuid.UUID(project),
                "date": today - timedelta(days=3 + i),
                "query": "best running shoes",
                "page": f"https://{DOMAIN}/running",
                "country": "usa",
                "device": "desktop",
                "clicks": 5,
                "impressions": 100,
                "position": 4.0 + i,
            }
            for i in range(2)
        ],
    )
    await owner_session.commit()

    job = await _run(api_app, b, org, f"{base}/keywords/check")
    assert job["status"] == "succeeded", job
    assert job["result"]["keywords"] == 2
    assert job["result"]["serp"] == 4
    assert job["result"]["first_party"] == 1
    listed = {k["keyword"]: k for k in (await b.get(f"{base}/keywords")).json()}
    shoes = listed["best running shoes"]
    by_source = {(p["engine"], p["source"]): p for p in shoes["positions"]}
    assert by_source[("google", "gsc")]["position"] == 4.5
    assert by_source[("google", "gsc")]["url"] == f"https://{DOMAIN}/running"
    assert by_source[("google", "serp")]["position"] == 2.0
    assert by_source[("google", "serp")]["ai_cited"] is True
    assert "ai_overview" in by_source[("google", "serp")]["features"]
    assert shoes["positions"][0]["engine"] == "google"  # Google first
    assert shoes["tags"] == ["core"]
    assert shoes["intent"] in {"commercial", "informational"}
    # The shared cache: a second check the same day costs nothing.
    calls = len(vendor.calls)
    job2 = await _run(api_app, b, org, f"{base}/keywords/check")
    assert job2["result"]["cached"] == 4
    assert len(vendor.calls) == calls

    sov = (await b.get(f"{base}/keywords/share-of-voice", params={"market_id": market})).json()
    shares = {r["domain"]: r for r in sov["rows"]}
    assert shares[DOMAIN]["average_position"] == 2.0
    assert shares["www.rival.com"]["average_position"] == 3.0
    assert shares[DOMAIN]["share"] > shares["www.rival.com"]["share"]
    assert sov["volumes_known"] is False  # honest: equal weights without volume data

    analysis = await b.post(
        f"{base}/keywords/analyze", {"keyword": "best running shoes", "market_id": market}
    )
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert body["from_cache"] is True
    assert body["results"][1]["is_own"] is True
    assert body["results"][2]["is_competitor"] is True
    assert 0 <= body["difficulty"]["score"] <= 100
    assert body["ai_answer_cites"] == ["https://www.example-shop.com/"]


async def test_plan_limits_and_budget_exhaustion(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session, plan="free")
    base = f"/api/v1/orgs/{org}/projects/{project}"
    too_many = await b.post(
        f"{base}/keywords", {"market_id": market, "keywords": [f"kw {i}" for i in range(101)]}
    )
    assert too_many.status_code == 402
    assert (
        await b.post(
            f"{base}/keywords", {"market_id": market, "keywords": [f"kw {i}" for i in range(3)]}
        )
    ).status_code == 201
    bing = await b.post(
        f"{base}/keywords/analyze", {"keyword": "kw 1", "market_id": market, "engine": "bing"}
    )
    assert bing.status_code == 402  # free plan: Google only
    # Exhaust the org's daily live-check budget.
    await owner_session.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO serp_usage (day, organization_id, requests) VALUES (:d, :o, 100)"
        ),
        {"d": datetime.now(UTC).date(), "o": uuid.UUID(org)},
    )
    await owner_session.commit()
    job = await _run(api_app, b, org, f"{base}/keywords/check")
    assert job["status"] == "succeeded"
    assert job["result"]["skipped"] == 3
    assert "daily live SERP checks are used up" in job["result"]["note"]
    unavailable = await b.post(
        f"{base}/keywords/analyze", {"keyword": "brand new query", "market_id": market}
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["reason"] == "serp_org_budget"


async def test_research_via_bing_and_opportunities(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    base = f"/api/v1/orgs/{org}/projects/{project}"
    none = await b.post(f"{base}/keywords/research", {"seed": "running shoes", "market_id": market})
    assert none.status_code == 409  # no source connected: say so
    fake = FakeBing()
    fake.install(internet)
    original = fake.handler

    def with_related(request: Any) -> Any:
        import httpx

        if request.url.path.endswith("GetRelatedKeywords"):
            return httpx.Response(
                200,
                json={
                    "d": [
                        {"Query": "Buy Running Shoes", "Impressions": 1200},
                        {"Query": "how to lace running shoes", "Impressions": 300},
                    ]
                },
            )
        return original(request)

    internet.handlers["ssl.bing.com"] = with_related
    keyring = api_app.state.identity.keyring
    owner_session.add(
        Connection(
            organization_id=uuid.UUID(org),
            provider=Provider.BING,
            credentials=seal(keyring, uuid.UUID(org), Provider.BING, {"api_key": fake.key}),
        )
    )
    await owner_session.commit()
    ideas = await b.post(
        f"{base}/keywords/research", {"seed": "running shoes", "market_id": market}
    )
    assert ideas.status_code == 200, ideas.text
    body = ideas.json()
    assert body["source"] == "bing"
    by_kw = {i["keyword"]: i for i in body["ideas"]}
    assert by_kw["buy running shoes"]["intent"] == "transactional"
    assert by_kw["how to lace running shoes"]["intent"] == "informational"
    assert by_kw["buy running shoes"]["volume_source"] == "bing"

    empty = (await b.get(f"{base}/keywords/opportunities")).json()
    assert empty["has_data"] is False
    day = datetime.now(UTC).date() - timedelta(days=3)
    rows = [
        ("striking query", 2, 900, 12.0),
        ("low ctr query", 1, 1000, 2.0),
        ("healthy query", 300, 1000, 1.5),
        ("tiny query", 0, 10, 9.0),
    ]
    await owner_session.execute(
        insert(GscDaily),
        [
            {
                "id": uuid7(),
                "organization_id": uuid.UUID(org),
                "project_id": uuid.UUID(project),
                "date": day,
                "query": q,
                "page": "https://x/",
                "country": "usa",
                "device": "desktop",
                "clicks": c,
                "impressions": i,
                "position": p,
            }
            for q, c, i, p in rows
        ],
    )
    await owner_session.commit()
    opps = (await b.get(f"{base}/keywords/opportunities")).json()
    kinds = {o["query"]: o["kind"] for o in opps["items"]}
    assert kinds == {"striking query": "striking_distance", "low ctr query": "low_ctr"}
    assert all(o["potential_clicks"] > 0 for o in opps["items"])


async def test_keywords_are_tenant_isolated(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, vendor: FakeVendor
) -> None:
    b, org, project, market = await _setup(api_app, outbox, owner_session)
    await b.post(
        f"/api/v1/orgs/{org}/projects/{project}/keywords",
        {"market_id": market, "keywords": ["secret keyword"]},
    )
    other, _ = await signed_in_browser(api_app, outbox)
    other_org = (await other.post("/api/v1/orgs", {"name": "Other"})).json()["id"]
    assert (
        await other.get(f"/api/v1/orgs/{other_org}/projects/{project}/keywords")
    ).status_code == 404
    assert (await other.get(f"/api/v1/orgs/{org}/projects/{project}/keywords")).status_code == 404
