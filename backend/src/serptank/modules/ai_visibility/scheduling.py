"""Enqueue weekly AI-visibility sampling for projects with active prompts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.errors import AppError
from serptank.modules.ai_visibility.models import AiPrompt
from serptank.modules.ai_visibility.service import JOB_KIND
from serptank.modules.jobs.models import ACTIVE_STATUSES, Job
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)
INTERVAL = timedelta(days=7)


async def enqueue_due_ai_sampling(
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
    active_job = exists().where(
        and_(Job.project_id == Project.id, Job.kind == JOB_KIND, Job.status.in_(ACTIVE_STATUSES))
    )
    has_prompts = exists().where(and_(AiPrompt.project_id == Project.id, AiPrompt.active.is_(True)))
    async with system_factory() as system:
        rows = (
            await system.execute(
                select(Project.organization_id, Project.id)
                .join(Organization, Organization.id == Project.organization_id)
                .outerjoin(last, last.c.project_id == Project.id)
                .where(
                    Project.deleted_at.is_(None),
                    Organization.deleted_at.is_(None),
                    has_prompts,
                    ~active_job,
                    (last.c.last.is_(None)) | (last.c.last <= now - INTERVAL),
                )
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
    logger.info("scheduled_ai_sampling_enqueued", count=started)
    return started
