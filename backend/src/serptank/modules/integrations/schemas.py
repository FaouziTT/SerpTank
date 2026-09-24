"""Integration API models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from serptank.modules.integrations.models import ConnectionStatus, Provider, SourceKind


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConnectionOut(BaseModel):
    provider: Provider
    status: ConnectionStatus
    account_label: str | None
    scopes: list[str]
    features: list[str]
    last_error_code: str | None
    created_at: datetime
    settings: dict[str, Any]


class IntegrationsOverview(BaseModel):
    connections: list[ConnectionOut]
    google_available: bool
    vitals_available: bool
    keyword_planner_available: bool


class GoogleStart(StrictModel):
    features: list[Literal["gsc", "gsc_write", "ga4", "ads"]] = Field(min_length=1, max_length=4)


class AuthorizationUrl(BaseModel):
    authorization_url: str


class BingConnect(StrictModel):
    api_key: str = Field(min_length=16, max_length=200)


class AdsAccount(StrictModel):
    customer_id: str = Field(pattern=r"^\d{3}-?\d{3}-?\d{4}$")


class PropertyOption(BaseModel):
    id: str
    label: str


class GoogleProperties(BaseModel):
    gsc_sites: list[PropertyOption]
    ga4_properties: list[PropertyOption]


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: SourceKind
    property_id: str
    settings: dict[str, Any]
    last_sync_at: datetime | None
    last_sync_status: str | None
    synced_through: date | None


class SourceLink(StrictModel):
    property_id: str = Field(min_length=1, max_length=500)


class IndexNowSettings(StrictModel):
    auto_submit: bool


class UrlList(StrictModel):
    urls: list[str] = Field(min_length=1, max_length=1000)
    channel: Literal["indexnow", "bing"] = "indexnow"


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    submitted_at: datetime
    url_count: int
    status_code: int | None
    trigger: str
    urls: list[str]


class InspectRequest(StrictModel):
    url: str = Field(min_length=8, max_length=2048)


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    inspected_at: datetime
    verdict: str | None
    coverage_state: str | None
    indexing_state: str | None
    robots_state: str | None
    page_fetch_state: str | None
    last_crawl_time: datetime | None
    google_canonical: str | None
    user_canonical: str | None


class SitemapSubmit(StrictModel):
    url: str = Field(min_length=8, max_length=2048)


class ImportOut(BaseModel):
    rows: int
    bad_rows: int
    errors: list[str]
    date_from: date
    date_to: date
    columns: dict[str, str]
    missing_metrics: list[str]


class MetricRow(BaseModel):
    key: str
    clicks: int
    impressions: int
    ctr: float | None
    position: float | None


class PerformanceOut(BaseModel):
    source: str
    days: int
    date_from: date
    date_to: date
    has_data: bool
    clicks: int
    impressions: int
    ctr: float | None
    position: float | None
    top_queries: list[MetricRow]
    top_pages: list[MetricRow]


class VitalsOut(BaseModel):
    target: str
    scope: str
    form_factor: str
    date: date
    lcp_ms: float | None
    inp_ms: float | None
    cls: float | None
    fcp_ms: float | None
    ttfb_ms: float | None
    assessment: str


class AiSurfaceTotals(BaseModel):
    source: str
    surface: str
    impressions: int
    clicks: int
    citations: int
    date_from: date
    date_to: date
