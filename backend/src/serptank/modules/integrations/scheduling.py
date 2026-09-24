"""Daily data syncs (GSC, GA4, Bing) and weekly Core Web Vitals, enqueued by beat.

Due work is found with the scheduler's BYPASSRLS session; jobs are created through
tenant-bound sessions (same path as user-started syncs).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.errors import AppError
from serptank.modules.integrations.models import (
    Connection,
    ConnectionStatus,
    ProjectSource,
    Provider,
    SourceKind,
    VitalsDaily,
)
from serptank.modules.integrations.sync import SYNC_KINDS
from serptank.modules.jobs.models import ACTIVE_STATUSES, Job
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.models import Project
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

SYNC_EVERY = timedelta(hours=20)
VITALS_EVERY = timedelta(days=7)
PROVIDER_FOR = {
    SourceKind.GSC: Provider.GOOGLE,
    SourceKind.GA4: Provider.GOOGLE,
    SourceKind.BING: Provider.BING,
}


async def due_syncs(system: AsyncSession, now: datetime) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    due: list[tuple[uuid.UUID, uuid.UUID, str]] = []
    for kind, job_kind in SYNC_KINDS.items():
        active = exists().where(
            and_(
                Job.project_id == ProjectSource.project_id,
                Job.kind == job_kind,
                Job.status.in_(ACTIVE_STATUSES),
            )
        )
        healthy = exists().where(
            and_(
                Connection.organization_id == ProjectSource.organization_id,
                Connection.provider == PROVIDER_FOR[kind],
                Connection.status != ConnectionStatus.REAUTH_REQUIRED,  # don't hammer a dead grant
            )
        )
        rows = await system.execute(
            select(ProjectSource.organization_id, ProjectSource.project_id)
            .join(Project, Project.id == ProjectSource.project_id)
            .join(Organization, Organization.id == ProjectSource.organization_id)
            .where(
                ProjectSource.kind == kind,
                Project.deleted_at.is_(None),
                Organization.deleted_at.is_(None),
                or_(
                    ProjectSource.last_sync_at.is_(None),
                    ProjectSource.last_sync_at < now - SYNC_EVERY,
                ),
                healthy,
                ~active,
            )
            .limit(1000)
        )
        due.extend((org, project, job_kind) for org, project in rows)
    # Weekly field vitals for projects with scheduled audits.
    recent = exists().where(
        and_(VitalsDaily.project_id == Project.id, VitalsDaily.date >= (now - VITALS_EVERY).date())
    )
    active_vitals = exists().where(
        and_(
            Job.project_id == Project.id, Job.kind == "vitals_sync", Job.status.in_(ACTIVE_STATUSES)
        )
    )
    rows = await system.execute(
        select(Project.organization_id, Project.id)
        .join(Organization, Organization.id == Project.organization_id)
        .where(
            Project.crawl_schedule != "off",
            Project.deleted_at.is_(None),
            Organization.deleted_at.is_(None),
            ~recent,
            ~active_vitals,
        )
        .limit(1000)
    )
    due.extend((org, project, "vitals_sync") for org, project in rows)
    return due


async def enqueue_due_syncs(
    system_factory: async_sessionmaker[AsyncSession],
    app_factory: async_sessionmaker[AsyncSession],
    dispatcher: JobDispatcher,
    *,
    vitals_enabled: bool,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    async with system_factory() as system:
        due = await due_syncs(system, now)
    started = 0
    for org_id, project_id, kind in due:
        if kind == "vitals_sync" and not vitals_enabled:
            continue
        async with app_factory() as db:
            await bind_identity(db, organization_id=org_id)
            try:
                job = await create_job(
                    db,
                    organization_id=org_id,
                    kind=kind,
                    project_id=project_id,
                    params={"scheduled": True},
                )
            except AppError:
                continue
        await dispatcher.dispatch(job)
        started += 1
    logger.info("scheduled_syncs_enqueued", count=started)
    return started
