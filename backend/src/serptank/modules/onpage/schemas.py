"""On-page API models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from serptank.modules.jobs.schemas import JobOut


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OptimizeRequest(StrictModel):
    market_id: uuid.UUID
    keyword: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=8, max_length=2000)


class BriefRequest(StrictModel):
    market_id: uuid.UUID
    keyword: str = Field(min_length=1, max_length=300)


class TargetUpdate(StrictModel):
    target_url: str | None = Field(default=None, max_length=2000)


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    keyword: str
    status: str
    error: str | None
    created_at: datetime


class OptimizationSummary(AnalysisSummary):
    url: str
    score: int | None


class OptimizationOut(OptimizationSummary):
    result: dict[str, Any]
    rewrite: dict[str, Any] | None


class OptimizationStarted(BaseModel):
    optimization: OptimizationSummary
    job: JobOut


class BriefOut(AnalysisSummary):
    brief: dict[str, Any]


class BriefStarted(BaseModel):
    brief: AnalysisSummary
    job: JobOut


class RewriteSuggestion(StrictModel):
    """What the LLM must return (validated; anything else is rejected)."""

    title: str = Field(max_length=80)
    meta_description: str = Field(max_length=180)
    h1: str = Field(max_length=120)
    sections_to_add: list[str] = Field(default_factory=list, max_length=8)
    notes: list[str] = Field(default_factory=list, max_length=5)


class CompetingPageOut(BaseModel):
    page: str
    impressions: int
    clicks: int
    position: float
    share: float


class CannibalizationOut(BaseModel):
    query: str
    impressions: int
    clicks: int
    pages: list[CompetingPageOut]


class CannibalizationReport(BaseModel):
    has_search_console_data: bool
    window_days: int
    issues: list[CannibalizationOut]


class KeywordMapRow(BaseModel):
    keyword_id: uuid.UUID
    keyword: str
    market_id: uuid.UUID
    target_url: str | None
    ranking_url: str | None
    ranking_source: str | None
    position: float | None
    status: str
