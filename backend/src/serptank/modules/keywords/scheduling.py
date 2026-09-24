"""Enqueue rank checks at each plan's frequency (free weekly, paid daily)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.errors import AppError
from serptank.modules.billing.entitlements import plan_for
from serptank.modules.jobs.models import ACTIVE_STATUSES, Job
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.keywords.ranks import JOB_KIND
from serptank.modules.projects.models import Project
from serptank.modules.search_data.models import TrackedKeyword
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)


async def enqueue_due_rank_checks(
    system_factory: async_sessionmaker[AsyncSession],
    app_factory: async_sessionmaker[AsyncSession],
    dispatcher: JobDispatcher,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    last = (
        select(Job.project_id, func.max(Job.created_at).label("last"))
        .where(Job.kind == JOB_KIND)
        .group_by(Job.project_id)
        .subquery()
    )
    active = exists().where(
        and_(Job.project_id == Project.id, Job.kind == JOB_KIND, Job.status.in_(ACTIVE_STATUSES))
    )
    has_keywords = exists().where(TrackedKeyword.project_id == Project.id)
    async with system_factory() as system:
        rows = (
            await system.execute(
                select(Project.organization_id, Project.id, Organization.plan_code, last.c.last)
                .join(Organization, Organization.id == Project.organization_id)
                .outerjoin(last, last.c.project_id == Project.id)
                .where(
                    Project.deleted_at.is_(None),
                    Organization.deleted_at.is_(None),
                    has_keywords,
                    ~active,
                )
                .limit(5000)
            )
        ).all()
    started = 0
    for org_id, project_id, plan_code, last_run in rows:
        interval = timedelta(hours=plan_for(plan_code).rank_check_interval_hours)
        if last_run is not None and last_run > now - interval:
            continue
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
                continue
        await dispatcher.dispatch(job)
        started += 1
    logger.info("scheduled_rank_checks_enqueued", count=started)
    return started
