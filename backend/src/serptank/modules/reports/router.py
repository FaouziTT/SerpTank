"""Reports API.

* ``/orgs/{org}/projects/{project}/presence``           Search Presence dashboard data
* ``/orgs/{org}/projects/{project}/exports``            CSV exports (+ signed links)
* ``/orgs/{org}/projects/{project}/alerts``             alert rules
* ``/orgs/{org}/notifications`` (+ ``/stream`` SSE)     the caller's notifications
* ``/exports/{org}/{export}?exp&sig``                   signed download (no session)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.errors import AppError, ConflictError, NotFoundError
from serptank.core.models import uuid7
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.identity.deps import DbSession
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.projects.router import ProjectRepository
from serptank.modules.reports import alerts, exports
from serptank.modules.reports.models import AlertRule, Export, Notification
from serptank.modules.reports.presence import presence
from serptank.modules.reports.schemas import (
    AlertKind,
    AlertRuleIn,
    AlertRuleOut,
    ExportLink,
    ExportOut,
    ExportRequest,
    ExportStarted,
    NotificationList,
    NotificationOut,
    PresenceOut,
)
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects/{project_id}", tags=["reports"])
org_router = APIRouter(prefix="/orgs/{org_id}/notifications", tags=["notifications"])
download_router = APIRouter(prefix="/exports", tags=["exports"])
ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
OrgRead = Annotated[OrgContext, Depends(org_access(Permission.ORG_READ))]
_EXPORT_RATE = rate_limit("exports", Rate(30, 3600))
_EVALUATE_RATE = rate_limit("alerts-evaluate", Rate(30, 3600))
STREAM_MAX_SECONDS = 300
POLL_SECONDS = 5.0
MAX_NOTIFICATIONS = 50


class InvalidLinkError(AppError):
    status = 403
    code = "invalid_link"
    title = "This download link is invalid or has expired"


async def _project(db: AsyncSession, ctx: OrgContext, project_id: uuid.UUID) -> Project:
    return await ProjectRepository(db, ctx.organization_id).get(project_id)


# -------------------------------------------------------------------------- presence
@router.get("/presence", response_model=PresenceOut)
async def get_presence(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession, market_id: uuid.UUID | None = None
) -> PresenceOut:
    project = await _project(db, ctx, project_id)
    query = select(ProjectMarket).where(ProjectMarket.project_id == project.id)
    if market_id is not None:
        query = query.where(ProjectMarket.id == market_id)
    market = (
        await db.execute(query.order_by(ProjectMarket.created_at, ProjectMarket.id).limit(1))
    ).scalar_one_or_none()
    if market is None:
        raise NotFoundError("Market not found.")
    return PresenceOut.model_validate(await presence(db, project, market))


# --------------------------------------------------------------------------- exports
@router.post(
    "/exports", response_model=ExportStarted, status_code=202, dependencies=[Depends(_EXPORT_RATE)]
)
async def start_export(
    project_id: uuid.UUID, body: ExportRequest, ctx: ProjectRead, db: DbSession, request: Request
) -> ExportStarted:
    project = await _project(db, ctx, project_id)
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=exports.JOB_KIND,
        project_id=project.id,
        user_id=ctx.actor_user_id,
        params={},
    )
    export = Export(
        id=uuid7(),
        organization_id=ctx.organization_id,
        project_id=project.id,
        job_id=job.id,
        created_by_user_id=ctx.actor_user_id,
        kind=body.kind,
        status="running",
    )
    db.add(export)
    job.params = {"id": str(export.id)}
    await db.commit()
    await db.refresh(export)
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return ExportStarted(export=ExportOut.model_validate(export), job=JobOut.model_validate(job))


@router.get("/exports", response_model=list[ExportOut])
async def list_exports(project_id: uuid.UUID, ctx: ProjectRead, db: DbSession) -> list[ExportOut]:
    project = await _project(db, ctx, project_id)
    rows = await db.execute(
        select(Export)
        .where(Export.project_id == project.id)
        .order_by(desc(Export.created_at))
        .limit(50)
    )
    return [ExportOut.model_validate(r) for r in rows.scalars()]


@router.post("/exports/{export_id}/link", response_model=ExportLink)
async def export_link(
    project_id: uuid.UUID, export_id: uuid.UUID, ctx: ProjectRead, db: DbSession, request: Request
) -> ExportLink:
    project = await _project(db, ctx, project_id)
    export = await db.get(Export, export_id)
    if export is None or export.project_id != project.id:
        raise NotFoundError("Export not found.")
    if export.status != "completed" or (
        export.expires_at is not None and export.expires_at < datetime.now(UTC)
    ):
        raise ConflictError("This export isn't available for download.")
    secret = request.app.state.settings.session_secret.get_secret_value()
    url, expires = exports.signed_path(secret, ctx.organization_id, export.id)
    return ExportLink(url=url, expires_at=expires)


@download_router.get("/{org_id}/{export_id}", response_class=Response)
async def download_export(
    org_id: uuid.UUID,
    export_id: uuid.UUID,
    request: Request,
    exp: Annotated[int, Query()],
    sig: Annotated[str, Query(min_length=64, max_length=64)],
) -> Response:
    secret = request.app.state.settings.session_secret.get_secret_value()
    if not exports.verify(secret, org_id, export_id, exp, sig):
        raise InvalidLinkError()
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as db:
        await bind_identity(db, organization_id=org_id)
        # ``content`` is deferred on the model; load it explicitly (no async lazy loads).
        row = (
            await db.execute(
                select(Export.content, Export.filename).where(
                    Export.id == export_id, Export.status == "completed"
                )
            )
        ).first()
        if row is None or row.content is None:
            raise NotFoundError("Export not found.")
        return Response(
            row.content,
            media_type="text/csv; charset=utf-8",
            headers={
                "content-disposition": f'attachment; filename="{row.filename}"',
                "cache-control": "no-store",
            },
        )


# ---------------------------------------------------------------------------- alerts
@router.get("/alerts", response_model=list[AlertRuleOut])
async def list_alerts(project_id: uuid.UUID, ctx: ProjectRead, db: DbSession) -> list[AlertRuleOut]:
    project = await _project(db, ctx, project_id)
    rules = {
        r.kind: r
        for r in (
            await db.execute(select(AlertRule).where(AlertRule.project_id == project.id))
        ).scalars()
    }
    out = []
    for kind, (label, default, meaning) in alerts.KINDS.items():
        rule = rules.get(kind)
        out.append(
            AlertRuleOut(
                kind=kind,
                label=label,
                threshold_meaning=meaning,
                configured=rule is not None,
                active=rule.active if rule else False,
                threshold=(rule.threshold if rule and rule.threshold is not None else default),
                email=rule.email if rule else False,
                last_evaluated_at=rule.last_evaluated_at if rule else None,
            )
        )
    return out


@router.put("/alerts/{kind}", status_code=204)
async def set_alert(
    project_id: uuid.UUID, kind: AlertKind, body: AlertRuleIn, ctx: ProjectWrite, db: DbSession
) -> None:
    project = await _project(db, ctx, project_id)
    rule = (
        await db.execute(
            select(AlertRule).where(AlertRule.project_id == project.id, AlertRule.kind == kind)
        )
    ).scalar_one_or_none()
    if rule is None:
        rule = AlertRule(organization_id=ctx.organization_id, project_id=project.id, kind=kind)
        db.add(rule)
    rule.active = body.active
    rule.threshold = body.threshold if alerts.KINDS[kind][2] else None
    rule.email = body.email
    await db.commit()


@router.post(
    "/alerts/evaluate",
    response_model=JobOut,
    status_code=202,
    dependencies=[Depends(_EVALUATE_RATE)],
)
async def evaluate_alerts(
    project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession, request: Request
) -> JobOut:
    project = await _project(db, ctx, project_id)
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=alerts.JOB_KIND,
        project_id=project.id,
        user_id=ctx.actor_user_id,
    )
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return JobOut.model_validate(job)


# --------------------------------------------------------------------- notifications
async def _notifications(db: AsyncSession, ctx: OrgContext) -> NotificationList:
    if ctx.actor_user_id is None:  # API keys have no inbox
        return NotificationList(unread=0, items=[])
    mine = (
        Notification.organization_id == ctx.organization_id,
        Notification.user_id == ctx.actor_user_id,
    )
    unread = (
        await db.execute(select(func.count()).where(*mine, Notification.read_at.is_(None)))
    ).scalar_one()
    rows = await db.execute(
        select(Notification)
        .where(*mine)
        .order_by(desc(Notification.created_at))
        .limit(MAX_NOTIFICATIONS)
    )
    return NotificationList(
        unread=int(unread), items=[NotificationOut.model_validate(r) for r in rows.scalars()]
    )


@org_router.get("", response_model=NotificationList)
async def list_notifications(ctx: OrgRead, db: DbSession) -> NotificationList:
    return await _notifications(db, ctx)


@org_router.post("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: uuid.UUID, ctx: OrgRead, db: DbSession) -> None:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.organization_id == ctx.organization_id,
            Notification.user_id == ctx.actor_user_id,
        )
        .values(read_at=func.coalesce(Notification.read_at, func.now()))
        .returning(Notification.id)
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("Notification not found.")
    await db.commit()


@org_router.post("/read-all", status_code=204)
async def mark_all_read(ctx: OrgRead, db: DbSession) -> None:
    await db.execute(
        update(Notification)
        .where(
            Notification.organization_id == ctx.organization_id,
            Notification.user_id == ctx.actor_user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=func.now())
    )
    await db.commit()


async def _stream(
    request: Request, factory: async_sessionmaker[AsyncSession], ctx: OrgContext
) -> AsyncIterator[bytes]:
    started = time.monotonic()
    last = ""
    yield b"retry: 5000\n\n"
    while time.monotonic() - started < STREAM_MAX_SECONDS:
        if await request.is_disconnected():
            return
        async with factory() as db:
            await bind_identity(db, organization_id=ctx.organization_id)
            payload = (await _notifications(db, ctx)).model_dump_json()
        if payload != last:
            yield f"event: notifications\ndata: {payload}\n\n".encode()
            last = payload
        else:
            yield b": keepalive\n\n"
        await asyncio.sleep(POLL_SECONDS)
    yield f"event: timeout\ndata: {json.dumps({'reconnect': True})}\n\n".encode()


@org_router.get(
    "/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def notification_stream(ctx: OrgRead, request: Request) -> StreamingResponse:
    return StreamingResponse(
        _stream(request, request.app.state.session_factory, ctx),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
