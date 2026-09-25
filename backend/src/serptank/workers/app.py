"""Celery application.

Only JSON messages carrying identifiers cross the broker (never pickle - plan §2.3 H6).
All job state lives in Postgres. Each worker process owns one asyncio event loop, one
database engine and one :class:`JobRuntime`, created at process start.

    celery -A serptank.workers.app worker -Q default,crawl -c 2
    celery -A serptank.workers.app beat
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from celery.signals import worker_process_init, worker_process_shutdown
from sqlalchemy.ext.asyncio import create_async_engine

from serptank.core.config import get_settings
from serptank.core.crypto import keyring_from_settings
from serptank.core.db import create_engine, create_session_factory
from serptank.core.logging import configure_logging
from serptank.maintenance import rotate_keys
from serptank.modules.ai_visibility.scheduling import enqueue_due_ai_sampling
from serptank.modules.billing.service import expire_grace_periods
from serptank.modules.compliance.service import purge_expired
from serptank.modules.crawler.scheduling import enqueue_due_crawls, fail_stale_jobs
from serptank.modules.integrations.scheduling import enqueue_due_syncs
from serptank.modules.jobs.service import CeleryDispatcher, JobRuntime, execute_job
from serptank.modules.keywords.scheduling import enqueue_due_rank_checks
from serptank.modules.reports.scheduling import enqueue_due_alert_checks
from serptank.workers.celery_config import make_celery
from serptank.workers.runtime import build_runtime, close_runtime

settings = get_settings()
celery = make_celery(settings)

_state: dict[str, Any] = {}


def _loop() -> asyncio.AbstractEventLoop:
    loop = _state.get("loop")
    if loop is None:
        loop = asyncio.new_event_loop()
        _state["loop"] = loop
    return loop


def _runtime() -> JobRuntime:
    runtime = _state.get("runtime")
    if runtime is None:
        configure_logging(settings.log_level, json=settings.log_json)
        engine = create_engine(settings, application_name="serptank-worker")
        _state["engine"] = engine
        runtime = build_runtime(settings, create_session_factory(engine))
        _state["runtime"] = runtime
    return runtime


@worker_process_init.connect
def _init(**_: Any) -> None:
    _loop()
    _runtime()


@worker_process_shutdown.connect
def _shutdown(**_: Any) -> None:
    runtime = _state.get("runtime")
    loop = _state.get("loop")
    if runtime is not None and loop is not None:
        loop.run_until_complete(close_runtime(runtime))
        loop.run_until_complete(_state["engine"].dispose())


@celery.task(name="serptank.run_job")
def run_job(organization_id: str, job_id: str) -> None:
    _loop().run_until_complete(
        execute_job(_runtime(), uuid.UUID(organization_id), uuid.UUID(job_id))
    )


@celery.task(name="serptank.schedule_due_work")
def schedule_due_work() -> None:
    url = settings.scheduler_database_url.get_secret_value()
    if not url:
        return  # scheduling disabled (no scheduler credentials configured)

    async def run() -> None:
        engine = create_async_engine(url, pool_size=1, max_overflow=0)
        try:
            system = create_session_factory(engine)
            await fail_stale_jobs(system)
            dispatcher = CeleryDispatcher(celery.send_task)
            await enqueue_due_crawls(system, _runtime().session_factory, dispatcher)
            await enqueue_due_rank_checks(system, _runtime().session_factory, dispatcher)
            await enqueue_due_ai_sampling(system, _runtime().session_factory, dispatcher)
            await enqueue_due_alert_checks(system, _runtime().session_factory, dispatcher)
            async with system() as billing_session:
                await expire_grace_periods(billing_session)
            async with system() as retention_session:
                await purge_expired(retention_session, settings.deletion_grace_days)
            async with system() as rotation_session:
                await rotate_keys(
                    rotation_session, _runtime().keyring or keyring_from_settings(settings)
                )
            await enqueue_due_syncs(
                system,
                _runtime().session_factory,
                dispatcher,
                vitals_enabled=bool(settings.google_api_key.get_secret_value()),
            )
        finally:
            await engine.dispose()

    _loop().run_until_complete(run())
