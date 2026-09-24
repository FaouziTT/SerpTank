"""Job status, cancellation and a Server-Sent Events progress stream.

SSE (not WebSockets, plan §4.3): cookie-authenticated, one-way, proxy-friendly. The
stream polls the job row with a fresh short-lived session each second - it never holds
a database transaction open - and ends when the job finishes, after 30 minutes, or when
the client disconnects.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.db import bind_identity
from serptank.core.repository import TenantRepository
from serptank.modules.identity.deps import DbSession
from serptank.modules.jobs.models import TERMINAL_STATUSES, Job
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import request_cancel
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/jobs", tags=["jobs"])

JobsRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
JobsWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]

STREAM_MAX_SECONDS = 30 * 60
POLL_SECONDS = 1.0
KEEPALIVE_SECONDS = 15.0


class JobRepository(TenantRepository[Job]):
    model = Job
    not_found_message = "Task not found."


@router.get("", response_model=list[JobOut])
async def list_jobs(
    ctx: JobsRead,
    db: DbSession,
    project_id: uuid.UUID | None = None,
    kind: str | None = Query(default=None, max_length=50),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Job]:
    stmt = select(Job).where(Job.organization_id == ctx.organization_id)
    if project_id is not None:
        stmt = stmt.where(Job.project_id == project_id)
    if kind is not None:
        stmt = stmt.where(Job.kind == kind)
    rows = await db.execute(stmt.order_by(Job.created_at.desc()).limit(limit))
    return list(rows.scalars())


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, ctx: JobsRead, db: DbSession) -> Job:
    return await JobRepository(db, ctx.organization_id).get(job_id)


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: uuid.UUID, ctx: JobsWrite, db: DbSession) -> Job:
    job = await JobRepository(db, ctx.organization_id).get(job_id)
    return await request_cancel(db, job)


def _event(name: str, payload: str) -> bytes:
    return f"event: {name}\ndata: {payload}\n\n".encode()


async def _job_stream(
    request: Request,
    factory: async_sessionmaker[AsyncSession],
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
) -> AsyncIterator[bytes]:
    started = last_sent = time.monotonic()
    last_payload = ""
    yield b"retry: 3000\n\n"
    while time.monotonic() - started < STREAM_MAX_SECONDS:
        if await request.is_disconnected():
            return
        async with factory() as db:
            await bind_identity(db, organization_id=organization_id)
            job = await JobRepository(db, organization_id).find(job_id)
            payload = JobOut.model_validate(job).model_dump_json() if job else ""
        if job is None:
            yield _event("gone", "{}")
            return
        if payload != last_payload:
            yield _event("job", payload)
            last_payload, last_sent = payload, time.monotonic()
            if job.status in TERMINAL_STATUSES:
                return
        elif time.monotonic() - last_sent > KEEPALIVE_SECONDS:
            yield b": keepalive\n\n"
            last_sent = time.monotonic()
        await asyncio.sleep(POLL_SECONDS)
    yield _event("timeout", json.dumps({"reconnect": True}))


@router.get(
    "/{job_id}/events",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def job_events(
    job_id: uuid.UUID, ctx: JobsRead, db: DbSession, request: Request
) -> StreamingResponse:
    # Resolve now so an unknown/foreign job is a normal 404 rather than an empty stream.
    await JobRepository(db, ctx.organization_id).get(job_id)
    return StreamingResponse(
        _job_stream(request, request.app.state.session_factory, ctx.organization_id, job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
