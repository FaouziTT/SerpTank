"""Hourly alert evaluation for projects with active rules; purge expired exports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.errors import AppError
from serptank.modules.jobs.models import ACTIVE_STATUSES, Job
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.models import Project
from serptank.modules.reports.alerts import JOB_KIND
from serptank.modules.reports.exports import purge_expired
from serptank.modules.reports.models import AlertRule

logger = structlog.get_logger(__name__)
INTERVAL = timedelta(hours=1)


async def enqueue_due_alert_checks(
    system_factory: async_sessionmaker[AsyncSession],
    app_factory: async_sessionmaker[AsyncSession],
    dispatcher: JobDispatcher,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    due_rule = exists().where(
        and_(
            AlertRule.project_id == Project.id,
            AlertRule.active.is_(True),
            or_(
                AlertRule.last_evaluated_at.is_(None), AlertRule.last_evaluated_at <= now - INTERVAL
            ),
        )
    )
    active_job = exists().where(
        and_(Job.project_id == Project.id, Job.kind == JOB_KIND, Job.status.in_(ACTIVE_STATUSES))
    )
    async with system_factory() as system:
        await purge_expired(system)
        rows = (
            await system.execute(
                select(Project.organization_id, Project.id)
                .where(Project.deleted_at.is_(None), due_rule, ~active_job)
                .order_by(func.random())
                .limit(5000)
            )
        ).all()
    started = 0
    for org_id, project_id in rows:
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
    logger.info("scheduled_alert_checks_enqueued", count=started)
    return started
