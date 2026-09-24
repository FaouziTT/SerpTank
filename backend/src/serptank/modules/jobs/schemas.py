"""Job API models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from serptank.modules.jobs.models import JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    status: JobStatus
    project_id: uuid.UUID | None
    progress: float
    stage: str | None
    counters: dict[str, Any]
    result: dict[str, Any]
    error_code: str | None
    error_message: str | None
    cancel_requested: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
