"""Celery configuration shared by workers, beat and the API (which only publishes)."""

from __future__ import annotations

from celery import Celery

from serptank.core.config import Settings


def make_celery(settings: Settings) -> Celery:
    app = Celery("serptank")
    app.conf.update(
        broker_url=settings.broker_url,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],  # never pickle (plan §2.3 H6)
        task_ignore_result=True,
        result_backend=None,
        task_acks_late=True,  # redeliver if a worker dies mid-task (execute_job is idempotent)
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_default_queue="default",
        task_time_limit=4 * 3600,
        broker_connection_retry_on_startup=True,
        worker_hijack_root_logger=False,
        beat_schedule={
            "schedule-due-work": {"task": "serptank.schedule_due_work", "schedule": 600.0},
        },
    )
    return app
