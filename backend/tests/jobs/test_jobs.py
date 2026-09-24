"""Job runtime edge cases, dispatchers and the scheduler."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.email import MemoryEmailSender
from serptank.core.models import uuid7
from serptank.modules.crawler.models import Crawl, CrawlStatus
from serptank.modules.crawler.scheduling import enqueue_due_crawls, fail_stale_jobs
from serptank.modules.jobs.models import Job, JobStatus
from serptank.modules.jobs.service import (
    CeleryDispatcher,
    JobContext,
    JobFailedError,
    create_job,
    execute_job,
    register_handler,
)
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization
from tests.support.api import signed_in_browser


@register_handler("test-crash")
async def _crash(_ctx: JobContext) -> dict[str, Any]:
    raise RuntimeError("secret internal detail")


@register_handler("test-fail")
async def _fail(_ctx: JobContext) -> dict[str, Any]:
    raise JobFailedError("nope", "A user-safe explanation.")


@register_handler("test-progress")
async def _progress(ctx: JobContext) -> dict[str, Any]:
    await ctx.report(progress=0.5, stage="halfway", counters={"n": 1})
    return {"ok": True}


async def _org_and_project(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> tuple[uuid.UUID, uuid.UUID]:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Jobs"})).json()["id"]
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "P", "domain": "jobs-test.com"})
    ).json()["id"]
    return uuid.UUID(org), uuid.UUID(project)


async def _job(
    api_app: FastAPI, org: uuid.UUID, kind: str, project: uuid.UUID | None = None
) -> Job:
    factory: async_sessionmaker[AsyncSession] = api_app.state.session_factory
    async with factory() as db:
        await bind_identity(db, organization_id=org)
        return await create_job(db, organization_id=org, kind=kind, project_id=project)


async def _status(api_app: FastAPI, org: uuid.UUID, job_id: uuid.UUID) -> Job:
    async with api_app.state.session_factory() as db:
        await bind_identity(db, organization_id=org)
        job: Job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one()
        return job


@pytest.mark.parametrize(
    ("kind", "status", "code", "message_part"),
    [
        ("test-crash", JobStatus.FAILED, "internal_error", "Something went wrong"),
        ("test-fail", JobStatus.FAILED, "nope", "user-safe"),
        ("test-progress", JobStatus.SUCCEEDED, None, None),
        ("unknown-kind", JobStatus.FAILED, "unsupported_job", "not available"),
    ],
)
async def test_job_outcomes(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    kind: str,
    status: JobStatus,
    code: str | None,
    message_part: str | None,
) -> None:
    org, _ = await _org_and_project(api_app, outbox)
    job = await _job(api_app, org, kind)
    await execute_job(api_app.state.job_runtime, org, job.id)
    stored = await _status(api_app, org, job.id)
    assert stored.status is status
    assert stored.error_code == code
    if message_part:
        assert message_part in (stored.error_message or "")
        assert "secret internal detail" not in (stored.error_message or "")  # never leaked
    if status is JobStatus.SUCCEEDED:
        assert stored.result == {"ok": True}
        assert stored.stage == "halfway"
        assert stored.progress == 1.0
    assert stored.attempts == 1
    # A duplicate delivery does not run it again.
    await execute_job(api_app.state.job_runtime, org, job.id)
    assert (await _status(api_app, org, job.id)).attempts == 1


async def test_wrong_tenant_cannot_claim_job(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    org, _ = await _org_and_project(api_app, outbox)
    job = await _job(api_app, org, "test-progress")
    # A forged message naming another organization finds nothing under RLS.
    await execute_job(api_app.state.job_runtime, uuid.uuid4(), job.id)
    assert (await _status(api_app, org, job.id)).status is JobStatus.QUEUED


async def test_celery_dispatcher_sends_ids_only() -> None:
    sent: list[tuple[str, dict[str, Any]]] = []

    def send_task(name: str, **kwargs: Any) -> None:
        sent.append((name, kwargs))

    job = Job(id=uuid7(), organization_id=uuid7(), kind="crawl")
    await CeleryDispatcher(send_task).dispatch(job)
    assert sent == [
        ("serptank.run_job", {"args": [str(job.organization_id), str(job.id)], "queue": "crawl"})
    ]


class _Recorder:
    def __init__(self) -> None:
        self.jobs: list[Job] = []

    async def dispatch(self, job: Job) -> None:
        self.jobs.append(job)


async def test_scheduler_enqueues_due_verified_projects(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_engine: AsyncEngine,
    owner_session: AsyncSession,
) -> None:
    org, project = await _org_and_project(api_app, outbox)
    system = async_sessionmaker(owner_engine, expire_on_commit=False)
    recorder = _Recorder()
    # Unverified or unscheduled projects are never picked.
    await owner_session.execute(
        update(Project).where(Project.id == project).values(crawl_schedule="weekly")
    )
    await owner_session.commit()
    await enqueue_due_crawls(system, api_app.state.session_factory, recorder)
    assert not any(j.project_id == project for j in recorder.jobs)

    await owner_session.execute(
        update(Project).where(Project.id == project).values(domain_verified_at=datetime.now(UTC))
    )
    await owner_session.commit()
    await enqueue_due_crawls(system, api_app.state.session_factory, recorder)
    mine = [j for j in recorder.jobs if j.project_id == project]
    assert len(mine) == 1
    assert mine[0].params == {"scheduled": True}
    # Already queued: not enqueued twice.
    await enqueue_due_crawls(system, api_app.state.session_factory, recorder)
    assert len([j for j in recorder.jobs if j.project_id == project]) == 1

    # A recent crawl makes the project not due.
    await owner_session.execute(
        update(Job).where(Job.project_id == project).values(status=JobStatus.SUCCEEDED)
    )
    owner_session.add(
        Crawl(
            id=uuid7(),
            organization_id=org,
            project_id=project,
            start_url="https://jobs-test.com/",
            max_pages=1,
            domain_verified=True,
            engines=["google"],
            site={},
            issue_counts={},
        )
    )
    await owner_session.commit()
    await enqueue_due_crawls(system, api_app.state.session_factory, recorder)
    assert len([j for j in recorder.jobs if j.project_id == project]) == 1
    org_row = await owner_session.get(Organization, org)
    assert org_row is not None


async def test_stale_running_jobs_are_failed(
    api_app: FastAPI,
    outbox: MemoryEmailSender,
    owner_engine: AsyncEngine,
    owner_session: AsyncSession,
) -> None:
    org, project = await _org_and_project(api_app, outbox)
    job = await _job(api_app, org, "crawl", project)
    crawl = Crawl(
        id=uuid7(),
        organization_id=org,
        project_id=project,
        job_id=job.id,
        start_url="https://jobs-test.com/",
        max_pages=1,
        domain_verified=False,
        engines=[],
        site={},
        issue_counts={},
        status=CrawlStatus.RUNNING,
    )
    owner_session.add(crawl)
    await owner_session.execute(
        update(Job)
        .where(Job.id == job.id)
        .values(status=JobStatus.RUNNING, heartbeat_at=datetime.now(UTC) - timedelta(hours=1))
    )
    await owner_session.commit()
    system = async_sessionmaker(owner_engine, expire_on_commit=False)
    assert await fail_stale_jobs(system) >= 1
    stored = await _status(api_app, org, job.id)
    assert stored.status is JobStatus.FAILED
    assert stored.error_code == "worker_lost"
    await owner_session.refresh(crawl)
    assert crawl.status is CrawlStatus.FAILED


def test_worker_module_is_configured_safely() -> None:
    from serptank.workers.app import celery

    conf = celery.conf
    assert conf.accept_content == ["json"]
    assert conf.task_serializer == "json"
    assert conf.task_acks_late is True
    assert "serptank.run_job" in celery.tasks
