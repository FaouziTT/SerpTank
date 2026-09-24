"""Cross-module guards: RLS on every tenant table, refresh, scheduling, auto-submission."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.email import MemoryEmailSender
from serptank.core.models import Base
from serptank.modules.integrations.credentials import google_access_token, seal
from serptank.modules.integrations.models import Connection, ProjectSource, Provider, SourceKind
from serptank.modules.integrations.scheduling import enqueue_due_syncs
from serptank.modules.jobs.models import Job
from serptank.modules.jobs.service import InProcessDispatcher
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization
from tests.crawler import fixture_site
from tests.integrations.fakes import FakeGoogle, FakeIndexNow
from tests.support.api import Browser, FakeInternet, signed_in_browser


async def test_every_tenant_table_has_forced_rls(owner_session: AsyncSession) -> None:
    tenant_tables = sorted(
        t.name for t in Base.metadata.tables.values() if "organization_id" in t.c
    )
    assert "gsc_daily" in tenant_tables
    rows = await owner_session.execute(
        text(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
            "(SELECT count(*) FROM pg_policies p WHERE p.tablename = c.relname) "
            "FROM pg_class c WHERE c.relname = ANY(:names)"
        ),
        {"names": tenant_tables},
    )
    state = {name: (enabled, forced, policies) for name, enabled, forced, policies in rows}
    unprotected = [
        table
        for table in tenant_tables
        if table not in state or not state[table][0] or not state[table][1] or state[table][2] == 0
    ]
    assert unprotected == [], f"tables without forced RLS and a policy: {unprotected}"


async def _setup(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, domain: str
) -> tuple[Browser, str, str]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Guard"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.commit()
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "S", "domain": domain})
    ).json()["id"]
    return b, org, project


async def test_expired_access_token_is_refreshed(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    google = FakeGoogle()
    google.install(internet)
    _, org, _ = await _setup(api_app, outbox, owner_session, "refresh-test.com")
    keyring = api_app.state.identity.keyring
    org_id = uuid.UUID(org)
    owner_session.add(
        Connection(
            organization_id=org_id,
            provider=Provider.GOOGLE,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
            credentials=seal(
                keyring,
                org_id,
                Provider.GOOGLE,
                {
                    "refresh_token": "refresh-1",
                    "access_token": "stale",
                    "expires_at": time.time() - 10,
                },
            ),
        )
    )
    await owner_session.commit()
    async with api_app.state.session_factory() as db:
        from serptank.core.db import bind_identity

        await bind_identity(db, organization_id=org_id)
        token = await google_access_token(
            db,
            org_id,
            keyring=keyring,
            settings=api_app.state.settings,
            http=api_app.state.identity.http,
        )
        assert token in google.issued_access
        # Cached now: no second refresh.
        again = await google_access_token(
            db,
            org_id,
            keyring=keyring,
            settings=api_app.state.settings,
            http=api_app.state.identity.http,
        )
        assert again == token
        assert google.counter == 1


async def test_scheduler_enqueues_stale_sources(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    owner_engine: AsyncEngine,
) -> None:
    _, org, project = await _setup(api_app, outbox, owner_session, "sched-test.com")
    org_id, project_id = uuid.UUID(org), uuid.UUID(project)
    keyring = api_app.state.identity.keyring
    owner_session.add(
        Connection(
            organization_id=org_id,
            provider=Provider.BING,
            credentials=seal(keyring, org_id, Provider.BING, {"api_key": "k"}),
        )
    )
    owner_session.add(
        ProjectSource(
            organization_id=org_id,
            project_id=project_id,
            kind=SourceKind.BING,
            property_id="https://sched-test.com/",
        )
    )
    await owner_session.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(crawl_schedule="weekly", domain_verified_at=datetime.now(UTC))
    )
    await owner_session.commit()

    class Recorder:
        def __init__(self) -> None:
            self.kinds: list[tuple[uuid.UUID | None, str]] = []

        async def dispatch(self, job: Job) -> None:
            self.kinds.append((job.project_id, job.kind))

    recorder = Recorder()
    system = async_sessionmaker(owner_engine, expire_on_commit=False)
    await enqueue_due_syncs(system, api_app.state.session_factory, recorder, vitals_enabled=True)
    mine = {k for p, k in recorder.kinds if p == project_id}
    assert mine == {"bing_sync", "vitals_sync"}
    # Recently synced sources and a dead grant are skipped.
    await owner_session.execute(
        text("UPDATE jobs SET status = 'succeeded' WHERE project_id = :p"), {"p": project_id}
    )
    await owner_session.execute(
        update(ProjectSource)
        .where(ProjectSource.project_id == project_id)
        .values(last_sync_at=datetime.now(UTC) - timedelta(hours=1))
    )
    await owner_session.commit()
    recorder.kinds.clear()
    await enqueue_due_syncs(system, api_app.state.session_factory, recorder, vitals_enabled=False)
    assert not [k for p, k in recorder.kinds if p == project_id]


async def test_changed_urls_are_auto_submitted_after_a_crawl(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession, internet: FakeInternet
) -> None:
    indexnow = FakeIndexNow()
    indexnow.install(internet)
    pages = dict(fixture_site.PAGES)
    key_holder: dict[str, str] = {}

    def site(request: httpx.Request) -> httpx.Response:
        if key_holder and request.url.path == f"/{key_holder['key']}.txt":
            return httpx.Response(200, text=key_holder["key"])
        return fixture_site.handler(request)

    internet.handlers[fixture_site.HOST] = site
    b, org, project = await _setup(api_app, outbox, owner_session, fixture_site.HOST)
    await owner_session.execute(
        update(Project)
        .where(Project.id == uuid.UUID(project))
        .values(domain_verified_at=datetime.now(UTC))
    )
    await owner_session.commit()
    base = f"/api/v1/orgs/{org}/projects/{project}"
    key_holder["key"] = (await b.post(f"{base}/indexnow")).json()["property_id"]
    await b.post(f"{base}/indexnow/verify")
    await b.client.patch(
        f"{base}/indexnow",
        json={"auto_submit": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf},
    )

    async def crawl() -> None:
        assert (await b.post(f"{base}/crawls")).status_code == 202
        dispatcher = api_app.state.job_dispatcher
        assert isinstance(dispatcher, InProcessDispatcher)
        await dispatcher.drain()

    await crawl()
    assert indexnow.received == []  # first audit: nothing to compare with
    fixture_site.PAGES["/about"] = pages["/about"].replace(
        "<h1>About</h1>", "<h1>About us, updated</h1>"
    )
    try:
        await crawl()
    finally:
        fixture_site.PAGES.clear()
        fixture_site.PAGES.update(pages)
    assert len(indexnow.received) == 1
    assert indexnow.received[0]["urlList"] == [f"{fixture_site.BASE}/about"]
    log = (await b.get(f"{base}/submissions")).json()
    assert log[0]["trigger"] == "crawl"
