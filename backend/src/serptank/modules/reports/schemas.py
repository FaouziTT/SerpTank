"""Reports, exports, alerts and notifications API models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from serptank.modules.jobs.schemas import JobOut

ExportKind = Literal["rankings", "audit_issues", "gsc_queries", "ai_answers"]
AlertKind = Literal[
    "rank_drop",
    "ai_citation_lost",
    "audit_regression",
    "cwv_poor",
    "indexing_lost",
    "weekly_digest",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PresenceOut(BaseModel):
    market_id: uuid.UUID
    generated_at: datetime
    score: int | None
    score_parts: dict[str, float | None]
    volumes_known: bool
    engines: list[dict[str, Any]]
    gsc: dict[str, Any] | None
    opportunities: list[dict[str, Any]]
    audit: dict[str, Any] | None
    vitals: dict[str, Any] | None
    ai: dict[str, Any]


class ExportRequest(StrictModel):
    kind: ExportKind


class ExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    status: str
    rows: int | None
    filename: str
    expires_at: datetime | None
    error: str | None
    created_at: datetime


class ExportStarted(BaseModel):
    export: ExportOut
    job: JobOut


class ExportLink(BaseModel):
    url: str
    expires_at: datetime


class AlertRuleIn(StrictModel):
    active: bool = True
    threshold: float | None = Field(default=None, ge=0, le=100)
    email: bool = False


class AlertRuleOut(BaseModel):
    kind: str
    label: str
    threshold_meaning: str | None
    configured: bool
    active: bool
    threshold: float | None
    email: bool
    last_evaluated_at: datetime | None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    kind: str
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]
