"""Own metrics: intent, CTR curves, share of voice, keyword difficulty, scheduling."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.email import MemoryEmailSender
from serptank.modules.jobs.models import Job
from serptank.modules.keywords import ctr
from serptank.modules.keywords.difficulty import compute
from serptank.modules.keywords.intent import classify
from serptank.modules.keywords.scheduling import enqueue_due_rank_checks
from serptank.modules.search_data.schema import SerpRequest
from serptank.modules.tenancy.models import Organization
from tests.search_data.fakes import FakeVendor
from tests.support.api import signed_in_browser


@pytest.mark.parametrize(
    ("keyword", "features", "expected"),
    [
        ("buy running shoes", [], "transactional"),
        ("best running shoes 2026", [], "commercial"),
        ("how to clean running shoes", [], "informational"),
        ("shoe repair near me", [], "local"),
        ("nike login", [], "navigational"),
        ("running shoes", ["shopping"], "transactional"),
        ("running shoes", [], "unknown"),
        ("are running shoes worth it?", [], "informational"),
    ],
)
def test_intent(keyword: str, features: list[str], expected: str) -> None:
    result = classify(keyword, features)
    assert result.primary == expected
    if expected != "unknown":
        assert result.reasons


def test_brand_terms_make_navigational() -> None:
    assert classify("acme pricing", brand_terms={"acme"}).primary in {
        "navigational",
        "transactional",
    }


def test_ctr_curve_fit_and_share_of_voice() -> None:
    assert ctr.expected_ctr(1) > ctr.expected_ctr(10) > ctr.expected_ctr(50)
    rows = [(1.0, 400, 1000), (2.0, 90, 1000), (3.0, 150, 1000), (15.0, 1, 10)]
    curve, own = ctr.fit_curve(rows)
    assert own is True
    assert curve[0] == 0.4
    assert curve[2] <= curve[1]  # monotonic even though position 3 beat position 2
    assert ctr.fit_curve([(1.0, 1, 10)])[1] is False
    assert ctr.share_of_voice([(1.0, 100), (None, 100)]) == 0.5
    assert ctr.share_of_voice([]) == 0.0


def test_difficulty_components() -> None:
    vendor = FakeVendor(ranking=["big.com", "big2.com", "small.org"], ai_cites=["big.com"])
    snapshot = asyncio.run(
        vendor.fetch(SerpRequest(engine="google", query="shoes", country="US", language="en"))
    )
    easy = compute(snapshot, {}, 10)
    hard = compute(snapshot, {"big.com": 80, "big2.com": 80, "small.org": 80}, 10_000)
    assert hard.score > easy.score
    assert hard.prominence == 1.0
    assert easy.confidence == "low"
    assert hard.confidence == "high"
    assert hard.crowding > 0
    empty = snapshot
    empty.organic = []
    assert compute(empty, {}, 0).score == 0


async def test_rank_checks_follow_plan_frequency(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    owner_engine: AsyncEngine,
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Sched"})).json()["id"]
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "S", "domain": "sched-kw.com"})
    ).json()
    await b.post(
        f"/api/v1/orgs/{org}/projects/{project['id']}/keywords",
        {"market_id": project["markets"][0]["id"], "keywords": ["one"]},
    )

    class Recorder:
        def __init__(self) -> None:
            self.projects: list[uuid.UUID | None] = []

        async def dispatch(self, job: Job) -> None:
            self.projects.append(job.project_id)

    system = async_sessionmaker(owner_engine, expire_on_commit=False)
    recorder = Recorder()
    await enqueue_due_rank_checks(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project["id"]) in recorder.projects
    # Finished 2 days ago: free plan checks weekly, so not due; pro (daily) is due.
    await owner_session.execute(
        update(Job)
        .where(Job.project_id == uuid.UUID(project["id"]))
        .values(status="succeeded", created_at=datetime.now(UTC) - timedelta(days=2))
    )
    await owner_session.commit()
    recorder.projects.clear()
    await enqueue_due_rank_checks(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project["id"]) not in recorder.projects
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.commit()
    await enqueue_due_rank_checks(system, api_app.state.session_factory, recorder)
    assert uuid.UUID(project["id"]) in recorder.projects
