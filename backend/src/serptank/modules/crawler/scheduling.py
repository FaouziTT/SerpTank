"""Scheduled audits and stale-job recovery (run by Celery beat through the scheduler).

Finding due work spans tenants, so it uses the ``serptank_system`` (BYPASSRLS) session -
read-only here except for failing stale jobs. Every job it creates is inserted through
a normal tenant-bound session, exactly like a user-started crawl.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.errors import AppError
from serptank.modules.crawler.models import Crawl
from serptank.modules.crawler.service import JOB_KIND
from serptank.modules.jobs.models import ACTIVE_STATUSES, Job, JobStatus
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

INTERVALS = {"weekly": timedelta(days=7), "monthly": timedelta(days=30)}
STALE_AFTER = timedelta(minutes=15)


async def due_crawls(system: AsyncSession, now: datetime) -> list[tuple[uuid.UUID, uuid.UUID]]:
    last_crawl = (
        select(Crawl.project_id, func.max(Crawl.created_at).label("last"))
        .group_by(Crawl.project_id)
        .subquery()
    )
    active = exists().where(
        and_(Job.project_id == Project.id, Job.kind == JOB_KIND, Job.status.in_(ACTIVE_STATUSES))
    )
    due: list[tuple[uuid.UUID, uuid.UUID]] = []
    for schedule, interval in INTERVALS.items():
        rows = await system.execute(
            select(Project.organization_id, Project.id)
            .join(Organization, Organization.id == Project.organization_id)
            .outerjoin(last_crawl, last_crawl.c.project_id == Project.id)
            .where(
                Project.crawl_schedule == schedule,
                Project.deleted_at.is_(None),
                Project.domain_verified_at.is_not(None),
                Organization.deleted_at.is_(None),
                (last_crawl.c.last.is_(None)) | (last_crawl.c.last < now - interval),
                ~active,
            )
            .limit(500)
        )
        due.extend((org_id, project_id) for org_id, project_id in rows)
    return due


async def enqueue_due_crawls(
    system_factory: async_sessionmaker[AsyncSession],
    app_factory: async_sessionmaker[AsyncSession],
    dispatcher: JobDispatcher,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    async with system_factory() as system:
        due = await due_crawls(system, now)
    started = 0
    for org_id, project_id in due:
        async with app_factory() as db:
            await bind_identity(db, organization_id=org_id)
            try:
                job = await create_job(
                    db,
                    organization_id=org_id,
                    kind=JOB_KIND,
                    project_id=project_id,
                    params={"scheduled": True},
                )
            except AppError:
                continue  # started meanwhile
        await dispatcher.dispatch(job)
        started += 1
    logger.info("scheduled_crawls_enqueued", count=started)
    return started


async def fail_stale_jobs(
    system_factory: async_sessionmaker[AsyncSession], now: datetime | None = None
) -> int:
    """Running jobs whose worker stopped heart-beating are failed honestly."""
    now = now or datetime.now(UTC)
    async with system_factory() as system:
        result = await system.execute(
            update(Job)
            .where(Job.status == JobStatus.RUNNING, Job.heartbeat_at < now - STALE_AFTER)
            .values(
                status=JobStatus.FAILED,
                finished_at=now,
                error_code="worker_lost",
                error_message="The task stopped unexpectedly. Please run it again.",
            )
            .returning(Job.id)
        )
        stale = [row[0] for row in result]
        if stale:
            await system.execute(
                update(Crawl)
                .where(Crawl.job_id.in_(stale), Crawl.status == "running")
                .values(status="failed", finished_at=now)
            )
        await system.commit()
    return len(stale)
