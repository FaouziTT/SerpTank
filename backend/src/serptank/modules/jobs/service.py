"""Job lifecycle: create, dispatch, execute, report progress, cancel.

Execution model
---------------
* The API creates a ``jobs`` row (status ``queued``) and hands ``(org_id, job_id)`` to a
  :class:`JobDispatcher`. Only identifiers cross the queue (JSON, never pickle).
* :func:`execute_job` binds the tenant, claims the row (``queued`` -> ``running``) with a
  conditional UPDATE - so a redelivered message cannot run a job twice - and calls the
  handler registered for the job's ``kind``.
* Handlers report progress through :class:`JobContext`, which commits in short
  transactions of its own and raises :class:`JobCancelledError` once a user asked to cancel.
* Failures are recorded with a stable ``error_code`` and a user-safe message. Unexpected
  exceptions are logged with a trace and shown to users only as a generic message.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank.core.config import Settings
from serptank.core.crypto import Keyring
from serptank.core.db import bind_identity
from serptank.core.errors import ConflictError
from serptank.core.http import EgressPolicy, SafeHttpClient
from serptank.core.models import uuid7
from serptank.modules.jobs.models import ACTIVE_STATUSES, Job, JobStatus

logger = structlog.get_logger(__name__)

HttpFactory = Callable[[EgressPolicy, str], SafeHttpClient]


class JobFailedError(Exception):
    """Raise from a handler to fail the job with a user-safe message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class JobCancelledError(Exception):
    """Raised inside a handler when the user cancelled the job."""


@dataclass
class JobRuntime:
    """Long-lived collaborators shared by all jobs in one process (API or worker)."""

    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    # Builds an SSRF-safe client with a given policy and user agent.
    http_factory: HttpFactory
    keyring: Keyring | None = None  # decrypts integration credentials
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobContext:
    runtime: JobRuntime
    organization_id: uuid.UUID
    job_id: uuid.UUID
    kind: str
    project_id: uuid.UUID | None
    params: dict[str, Any]
    user_id: uuid.UUID | None

    async def session(self) -> AsyncSession:
        """A new session bound to this job's tenant (caller closes it)."""
        session = self.runtime.session_factory()
        await bind_identity(session, organization_id=self.organization_id)
        return session

    async def report(
        self,
        *,
        progress: float | None = None,
        stage: str | None = None,
        counters: dict[str, Any] | None = None,
    ) -> None:
        """Persist progress (own transaction) and honour cancellation requests."""
        values: dict[str, Any] = {"heartbeat_at": datetime.now(UTC)}
        if progress is not None:
            values["progress"] = max(0.0, min(1.0, progress))
        if stage is not None:
            values["stage"] = stage
        if counters is not None:
            values["counters"] = counters
        async with await self.session() as db:
            cancelled = (
                await db.execute(
                    update(Job)
                    .where(Job.id == self.job_id)
                    .values(**values)
                    .returning(Job.cancel_requested)
                )
            ).scalar_one()
            await db.commit()
        if cancelled:
            raise JobCancelledError


JobHandler = Callable[[JobContext], Awaitable[dict[str, Any]]]
_HANDLERS: dict[str, JobHandler] = {}
# Celery queue per job kind (default queue otherwise).
QUEUES: dict[str, str] = {}


def register_handler(kind: str, *, queue: str = "default") -> Callable[[JobHandler], JobHandler]:
    def decorator(fn: JobHandler) -> JobHandler:
        _HANDLERS[kind] = fn
        QUEUES[kind] = queue
        return fn

    return decorator


def handler_for(kind: str) -> JobHandler | None:
    return _HANDLERS.get(kind)


# ------------------------------------------------------------------------ creation
async def create_job(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    kind: str,
    project_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    params: dict[str, Any] | None = None,
) -> Job:
    """Insert a queued job and commit. One active job per (project, kind)."""
    job = Job(
        id=uuid7(),
        organization_id=organization_id,
        kind=kind,
        project_id=project_id,
        created_by_user_id=user_id,
        params=params or {},
        status=JobStatus.QUEUED,
    )
    db.add(job)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("This task is already running for the project.") from exc
    return job


# ----------------------------------------------------------------------- execution
async def _finish(
    runtime: JobRuntime,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    status: JobStatus,
    **values: Any,
) -> None:
    async with runtime.session_factory() as db:
        await bind_identity(db, organization_id=organization_id)
        await db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=status, finished_at=datetime.now(UTC), **values)
        )
        await db.commit()


async def execute_job(runtime: JobRuntime, organization_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Run one job to completion. Safe to call more than once for the same job."""
    log = logger.bind(job_id=str(job_id), organization_id=str(organization_id))
    async with runtime.session_factory() as db:
        await bind_identity(db, organization_id=organization_id)
        claimed = (
            await db.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == JobStatus.QUEUED)
                .values(
                    status=JobStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    heartbeat_at=datetime.now(UTC),
                    attempts=Job.attempts + 1,
                )
                .returning(Job)
            )
        ).scalar_one_or_none()
        await db.commit()
    if claimed is None:
        log.info("job_not_claimed")  # already running/finished, cancelled, or unknown
        return

    handler = handler_for(claimed.kind)
    if handler is None:
        log.error("job_handler_missing", kind=claimed.kind)
        await _finish(
            runtime,
            organization_id,
            job_id,
            JobStatus.FAILED,
            error_code="unsupported_job",
            error_message="This task type is not available.",
        )
        return

    ctx = JobContext(
        runtime=runtime,
        organization_id=organization_id,
        job_id=job_id,
        kind=claimed.kind,
        project_id=claimed.project_id,
        params=dict(claimed.params),
        user_id=claimed.created_by_user_id,
    )
    log = log.bind(kind=claimed.kind)
    log.info("job_started")
    try:
        result = await handler(ctx)
    except JobCancelledError:
        log.info("job_cancelled")
        await _finish(runtime, organization_id, job_id, JobStatus.CANCELLED)
    except JobFailedError as exc:
        log.info("job_failed", error_code=exc.code)
        await _finish(
            runtime,
            organization_id,
            job_id,
            JobStatus.FAILED,
            error_code=exc.code,
            error_message=exc.message[:500],
        )
    except Exception:
        log.exception("job_crashed")
        await _finish(
            runtime,
            organization_id,
            job_id,
            JobStatus.FAILED,
            error_code="internal_error",
            error_message="Something went wrong while running this task. We've been notified.",
        )
    else:
        log.info("job_succeeded")
        await _finish(
            runtime, organization_id, job_id, JobStatus.SUCCEEDED, progress=1.0, result=result
        )


# ------------------------------------------------------------------------ dispatch
class JobDispatcher(Protocol):
    async def dispatch(self, job: Job) -> None: ...


class InProcessDispatcher:
    """Runs jobs as asyncio tasks in this process (development and tests only)."""

    def __init__(self, runtime: JobRuntime) -> None:
        self.runtime = runtime
        self.tasks: set[asyncio.Task[None]] = set()

    async def dispatch(self, job: Job) -> None:
        task = asyncio.create_task(execute_job(self.runtime, job.organization_id, job.id))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def drain(self) -> None:
        """Wait for every dispatched job (tests)."""
        while self.tasks:
            await asyncio.gather(*list(self.tasks), return_exceptions=True)


class CeleryDispatcher:
    """Publishes ``serptank.run_job(org_id, job_id)`` to the job kind's queue."""

    def __init__(self, send_task: Callable[..., Any]) -> None:
        self._send_task = send_task

    async def dispatch(self, job: Job) -> None:
        await asyncio.to_thread(
            self._send_task,
            "serptank.run_job",
            args=[str(job.organization_id), str(job.id)],
            queue=QUEUES.get(job.kind, "default"),
        )


async def request_cancel(db: AsyncSession, job: Job) -> Job:
    """Queued jobs cancel immediately; running jobs stop at their next progress report."""
    if job.status not in ACTIVE_STATUSES:
        raise ConflictError("This task has already finished.")
    if job.status is JobStatus.QUEUED:
        job.status = JobStatus.CANCELLED
        job.finished_at = datetime.now(UTC)
    job.cancel_requested = True
    await db.commit()
    return job


async def latest_job(
    db: AsyncSession, organization_id: uuid.UUID, project_id: uuid.UUID, kind: str
) -> Job | None:
    stmt = (
        select(Job)
        .where(
            Job.organization_id == organization_id,
            Job.project_id == project_id,
            Job.kind == kind,
        )
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()
