"""AI visibility API end to end: settings, prompts, sampling, visibility, readiness."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.email import MemoryEmailSender
from serptank.core.models import uuid7
from serptank.modules.ai_visibility.scheduling import enqueue_due_ai_sampling
from serptank.modules.audit.models import AuditIssue, Severity
from serptank.modules.crawler.models import Crawl, CrawlPage, CrawlStatus
from serptank.modules.integrations.models import AiPerformanceDaily
from serptank.modules.jobs.models import Job
from serptank.modules.jobs.service import InProcessDispatcher
from serptank.modules.llm.gateway import month_start
from serptank.modules.llm.models import LlmUsage
from serptank.modules.search_data.collector import CollectorRouter
from serptank.modules.tenancy.models import Organization
from tests.ai_visibility.fakes import FakeEngine
from tests.search_data.fakes import FakeVendor
from tests.support.api import Browser, signed_in_browser

DOMAIN = "example-shop.com"
AI_ENGINES = ["google_ai_overview", "chatgpt", "perplexity", "gemini"]


@pytest.fixture
def engines(api_app: FastAPI) -> dict[str, FakeEngine]:
    fakes = {
        "chatgpt": FakeEngine(
            "chatgpt",
            "Example Shop is the best and most reliable store. Rival is also popular.",
            ["https://www.example-shop.com/trail", "https://rival.com/x"],
        ),
        "perplexity": FakeEngine("perplexity", "Top picks: Rival and GearLab.", []),
    }
    extras = api_app.state.job_runtime.extras
    extras["answer_engines"] = fakes
    extras["serp"] = CollectorRouter(
        adapters={"fake": FakeVendor(ai_cites=["www.example-shop.com"])},
        order={"*": ["fake"]},
        global_daily_requests=10_000,
    )
    return fakes


async def _setup(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, plan: str = "pro"
) -> tuple[Browser, str, str, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "AI"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code=plan)
    )
    await owner_session.commit()
    market = {
        "country": "US",
        "language": "en",
        "search_engines": ["google"],
        "ai_engines": AI_ENGINES,
    }
    project = (
        await b.post(
            f"/api/v1/orgs/{org}/projects",
            {"name": "Example Shop", "domain": DOMAIN, "markets": [market]},
        )
    ).json()
    assert "markets" in project, project
    base = f"/api/v1/orgs/{org}/projects/{project['id']}"
    return b, org, project["id"], project["markets"][0]["id"], base


async def _run(api_app: FastAPI, b: Browser, org: str, base: str) -> dict[str, Any]:
    started = await b.post(f"{base}/ai/run")
    assert started.status_code == 202, started.text
    dispatcher = api_app.state.job_dispatcher
    assert isinstance(dispatcher, InProcessDispatcher)
    await dispatcher.drain()
    return (await b.get(f"/api/v1/orgs/{org}/jobs/{started.json()['id']}")).json()  # type: ignore[no-any-return]


async def test_prompts_sampling_and_visibility(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    engines: dict[str, FakeEngine],
) -> None:
    b, org, project, market, base = await _setup(api_app, outbox, owner_session)
    settings = (await b.get(f"{base}/ai/settings")).json()
    status = {e["engine"]: e for e in settings["engines"]}
    assert status["chatgpt"]["available"] is True
    assert status["gemini"] == {
        "engine": "gemini",
        "selected": True,
        "entitled": True,
        "available": False,
        "note": "No sampling adapter yet.",
    }
    assert settings["brand_terms"] == ["Example Shop"]
    assert (
        await b.client.put(
            f"{base}/ai/settings",
            json={"brand_terms": ["Example Shop", "ExShop"], "samples_per_prompt": 2},
            headers=b._headers(),
        )
    ).status_code == 204
    await b.post(f"{base}/competitors", {"domain": "rival.com", "label": "Rival"})

    # Prompt suggestions come from tracked keywords (no LLM involved).
    await b.post(f"{base}/keywords", {"market_id": market, "keywords": ["trail running shoes"]})
    suggestions = (
        await b.get(f"{base}/ai/prompts/suggestions", params={"market_id": market})
    ).json()
    assert suggestions[0]["keyword"] == "trail running shoes"
    added = await b.post(
        f"{base}/ai/prompts",
        {
            "market_id": market,
            "prompts": ["Best trail running shoes?", "best  trail running shoes?"],
            "keyword": "trail running shoes",
        },
    )
    assert added.status_code == 201, added.text
    assert added.json() == {"added": 1, "skipped_existing": 1}
    assert (
        await b.post(f"{base}/ai/prompts", {"market_id": market, "prompts": ["hi"]})
    ).status_code == 422

    job = await _run(api_app, b, org, base)
    assert job["status"] == "succeeded", job
    # 1 Google SERP + 2 samples x 2 engines; gemini is selected but unavailable.
    assert job["result"]["samples"] == 5
    assert job["result"]["unavailable"] == 1
    assert engines["chatgpt"].calls[0] == ("Best trail running shoes?", "US")

    vis = (await b.get(f"{base}/ai/visibility")).json()
    by_engine = {e["engine"]: e for e in vis["engines"]}
    assert vis["engines"][0]["engine"] == "google_ai_overview"  # Google first
    aio = by_engine["google_ai_overview"]
    assert aio["answer_rate"]["rate"] == 1.0
    assert aio["citation_rate"]["successes"] == 1
    chat = by_engine["chatgpt"]
    assert chat["mention_rate"]["successes"] == 2
    assert chat["mention_rate"]["trials"] == 2
    assert chat["mention_rate"]["low"] < 1.0  # an interval, not a bare 100%
    assert chat["avg_sentiment"] == 1.0
    assert by_engine["perplexity"]["mention_rate"]["rate"] == 0.0
    share = {r["domain"]: r for r in vis["share_of_voice"]}
    assert share[DOMAIN]["is_own"] is True
    assert share[DOMAIN]["mentions"] == 2
    assert share["rival.com"]["mentions"] == 4
    prompt_row = vis["prompts"][0]
    assert prompt_row["engines"]["chatgpt"] == {
        "samples": 2,
        "answered": 2,
        "mentioned": 2,
        "cited": 2,
    }

    answers = (await b.get(f"{base}/ai/answers", params={"engine": "chatgpt"})).json()
    assert len(answers) == 2
    assert "Example Shop" in answers[0]["excerpt"]
    assert answers[0]["competitors"]["rival.com"] == {"mentioned": True, "cited": True}
    usage = (await b.get(f"{base}/ai/settings")).json()
    assert usage["prompts_used_this_month"] == 4

    await _lifecycle(api_app, outbox, b, org, project, base)


async def _lifecycle(
    api_app: FastAPI, outbox: MemoryEmailSender, b: Browser, org: str, project: str, base: str
) -> None:
    """Same-day reruns, deactivation, deletion and tenant isolation of prompts."""
    # Re-running the same day replaces today's samples instead of doubling them.
    await _run(api_app, b, org, base)
    assert len((await b.get(f"{base}/ai/answers", params={"engine": "chatgpt"})).json()) == 2

    prompts = (await b.get(f"{base}/ai/prompts")).json()
    pid = prompts[0]["id"]
    patched = await b.client.patch(
        f"{base}/ai/prompts/{pid}", json={"active": False}, headers=b._headers()
    )
    assert patched.json()["active"] is False
    idle = await _run(api_app, b, org, base)
    assert idle["result"]["prompts"] == 0

    # Another tenant sees nothing.
    other, _ = await signed_in_browser(api_app, outbox)
    other_org = (await other.post("/api/v1/orgs", {"name": "Other"})).json()["id"]
    assert (await other.get(f"{base}/ai/visibility")).status_code == 404
    foreign = f"/api/v1/orgs/{other_org}/projects/{project}/ai/prompts/{pid}"
    assert (await other.delete(foreign)).status_code == 404
    assert (await b.delete(f"{base}/ai/prompts/{pid}")).status_code == 204


async def test_budget_and_plan_limits(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    engines: dict[str, FakeEngine],
) -> None:
    b, org, _, market, base = await _setup(api_app, outbox, owner_session)
    # Downgraded to free: markets keep their selections, but only entitled engines run.
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="free")
    )
    await owner_session.commit()
    await b.post(f"{base}/ai/prompts", {"market_id": market, "prompts": ["Best trail shoes?"]})
    job = await _run(api_app, b, org, base)
    # Free plan: Google AI surfaces only; ChatGPT is selected but not entitled.
    assert job["result"]["samples"] == 1
    assert engines["chatgpt"].calls == []
    status = {e["engine"]: e for e in (await b.get(f"{base}/ai/settings")).json()["engines"]}
    assert status["chatgpt"]["entitled"] is False

    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.execute(
        insert(LlmUsage).values(
            month=month_start(),
            organization_id=uuid.UUID(org),
            purpose="ai_sampling:chatgpt",
            requests=1999,
            input_tokens=0,
            output_tokens=0,
        )
    )
    await owner_session.commit()
    job = await _run(api_app, b, org, base)
    assert job["status"] == "succeeded"
    assert len(engines["chatgpt"].calls) == 1  # one sample left in the month
    assert job["result"]["note"] == "Your plan's monthly AI prompt samples are used up."


async def test_readiness_and_first_party(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, org, project, _, base = await _setup(api_app, outbox, owner_session)
    empty = (await b.get(f"{base}/ai/readiness")).json()
    assert empty["available"] is False
    assert empty["note"] == "Run a site audit to score AI readiness."
    org_id, project_id = uuid.UUID(org), uuid.UUID(project)
    crawl = Crawl(
        id=uuid7(),
        organization_id=org_id,
        project_id=project_id,
        status=CrawlStatus.COMPLETED,
        start_url=f"https://{DOMAIN}/",
        max_pages=10,
        domain_verified=True,
        site={
            "robots": {
                DOMAIN: {
                    "home_allowed": {"googlebot": True, "bingbot": True},
                    "ai_bots_allowed": {"perplexitybot": False, "gptbot": False},
                }
            }
        },
    )
    owner_session.add(crawl)
    await owner_session.flush()
    for depth, (url, indexable, data) in enumerate(
        [
            (f"https://{DOMAIN}/", True, {"json_ld": [{"@type": ["Organization"]}]}),
            (f"https://{DOMAIN}/a", True, {}),
            (f"https://{DOMAIN}/b", False, {}),
        ]
    ):
        owner_session.add(
            CrawlPage(
                id=uuid7(),
                organization_id=org_id,
                crawl_id=crawl.id,
                url=url,
                depth=depth,
                found_via="link",
                status_code=200,
                content_type="text/html; charset=utf-8",
                indexable_google=indexable,
                data=data,
            )
        )
    owner_session.add(
        AuditIssue(
            organization_id=org_id,
            crawl_id=crawl.id,
            rule_id="thin_content",
            severity=Severity.LOW,
            url=f"https://{DOMAIN}/a",
        )
    )
    await owner_session.execute(
        insert(AiPerformanceDaily).values(
            id=uuid7(),
            organization_id=org_id,
            project_id=project_id,
            date=datetime.now(UTC).date() - timedelta(days=1),
            source="gsc_genai",
            surface="ai_overview",
            impressions=120,
            clicks=3,
        )
    )
    await owner_session.commit()

    ready = (await b.get(f"{base}/ai/readiness")).json()
    assert ready["available"] is True
    parts = {c["id"]: c for c in ready["components"]}
    assert parts["access"]["score"] == 90  # PerplexityBot blocked (-10); GPTBot isn't penalised
    assert any("Training bots" in f for f in parts["access"]["findings"])
    assert parts["indexable"]["score"] == 67
    assert parts["entity"]["score"] == 100
    assert parts["content"]["score"] == 67
    assert ready["bots"]["perplexitybot"] is False
    assert 0 < ready["score"] < 100
    vis = (await b.get(f"{base}/ai/visibility")).json()
    assert vis["engines"] == []  # nothing sampled yet, and nothing invented
    assert vis["first_party"][0]["impressions"] == 120


async def test_weekly_scheduler(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    owner_engine: AsyncEngine,
) -> None:
    b, _, project, market, base = await _setup(api_app, outbox, owner_session)

    class Recorder:
        def __init__(self) -> None:
            self.projects: list[uuid.UUID | None] = []

        async def dispatch(self, job: Job) -> None:
            self.projects.append(job.project_id)

    system = async_sessionmaker(owner_engine, expire_on_commit=False)
    recorder = Recorder()
    await enqueue_due_ai_sampling(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project) not in recorder.projects  # no prompts yet
    await b.post(f"{base}/ai/prompts", {"market_id": market, "prompts": ["Best shoes?"]})
    await enqueue_due_ai_sampling(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project) in recorder.projects
    await owner_session.execute(
        update(Job)
        .where(Job.project_id == uuid.UUID(project))
        .values(status="succeeded", created_at=datetime.now(UTC) - timedelta(days=2))
    )
    await owner_session.commit()
    recorder.projects.clear()
    await enqueue_due_ai_sampling(system, api_app.state.session_factory, recorder)
    assert recorder.projects == []  # ran 2 days ago; weekly
