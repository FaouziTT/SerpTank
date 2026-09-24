"""Crawl and audit API models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from serptank.modules.audit.models import Severity
from serptank.modules.crawler.models import CrawlStatus
from serptank.modules.jobs.schemas import JobOut


class CrawlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None
    status: CrawlStatus
    start_url: str
    max_pages: int
    domain_verified: bool
    engines: list[str]
    pages_fetched: int
    pages_discovered: int
    budget_exhausted: bool
    render_available: bool
    score: float | None
    issue_counts: dict[str, Any]
    created_at: datetime
    finished_at: datetime | None


class CrawlStarted(BaseModel):
    job: JobOut
    pages_budget: int


class CrawlUsage(BaseModel):
    pages_used_this_month: int
    pages_per_month: int
    max_pages_next_crawl: int
    domain_verified: bool


class IssueSummary(BaseModel):
    rule_id: str
    title: str
    category: str
    category_label: str
    severity: Severity
    scope: str
    description: str
    fix: str
    reference: str | None
    effort: int
    affected: int
    priority: float
    examples: list[str]


class IssueOccurrence(BaseModel):
    url: str | None
    details: dict[str, Any]


class IssuePage(BaseModel):
    rule_id: str
    total: int
    items: list[IssueOccurrence]


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    depth: int | None
    status_code: int | None
    error: str | None
    content_type: str | None
    response_ms: int | None
    redirect_to: str | None
    in_sitemap: bool
    indexable_google: bool
    indexable_bing: bool
    title: str | None
    canonical: str | None
    word_count: int | None
    inlinks: int


class PageList(BaseModel):
    total: int
    items: list[PageOut]
