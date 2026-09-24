"""Keyword, rank and competitor API models."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KeywordsAdd(StrictModel):
    market_id: uuid.UUID
    keywords: list[str] = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=10)


class PositionOut(BaseModel):
    engine: str
    source: str
    position: float | None
    previous: float | None
    date: date
    url: str | None
    features: list[str]
    ai_cited: bool | None


class TrackedKeywordOut(BaseModel):
    id: uuid.UUID
    keyword: str
    market_id: uuid.UUID
    tags: list[str]
    intent: str
    volume: int | None
    volume_source: str | None
    positions: list[PositionOut]


class KeywordsAdded(BaseModel):
    added: int
    skipped_existing: int
    limit: int
    used: int


class CompetitorIn(StrictModel):
    domain: str = Field(min_length=3, max_length=253)
    label: str | None = Field(default=None, max_length=120)


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    label: str | None


class ShareOfVoiceRow(BaseModel):
    domain: str
    is_own: bool
    share: float
    keywords_ranking: int
    average_position: float | None


class ShareOfVoiceOut(BaseModel):
    engine: str
    date: date | None
    keywords: int
    volumes_known: bool
    rows: list[ShareOfVoiceRow]


class ResearchRequest(StrictModel):
    seed: str = Field(min_length=2, max_length=100)
    market_id: uuid.UUID


class KeywordIdeaOut(BaseModel):
    keyword: str
    volume: int | None
    volume_source: str
    competition: str | None
    cpc_low: float | None
    cpc_high: float | None
    intent: str
    intent_reasons: list[str]
    difficulty: int | None
    tracked: bool


class ResearchOut(BaseModel):
    source: Literal["google_ads", "bing"]
    ideas: list[KeywordIdeaOut]


class AnalyzeRequest(StrictModel):
    keyword: str = Field(min_length=1, max_length=300)
    market_id: uuid.UUID
    engine: str = Field(default="google", max_length=20)


class SerpResultOut(BaseModel):
    position: int
    url: str
    domain: str
    title: str
    is_own: bool
    is_competitor: bool


class DifficultyOut(BaseModel):
    score: int
    prominence: float
    targeting: float
    root_pages: float
    crowding: float
    confidence: str


class AnalyzeOut(BaseModel):
    keyword: str
    engine: str
    fetched_on: date
    from_cache: bool
    intent: str
    intent_reasons: list[str]
    difficulty: DifficultyOut
    features: list[str]
    ai_answer_cites: list[str]
    people_also_ask: list[str]
    results: list[SerpResultOut]


class OpportunityOut(BaseModel):
    query: str
    kind: Literal["striking_distance", "low_ctr"]
    clicks: int
    impressions: int
    ctr: float
    position: float
    expected_ctr: float
    potential_clicks: int
    tracked: bool


class OpportunitiesOut(BaseModel):
    has_data: bool
    curve_source: Literal["own", "default"]
    date_from: date | None
    date_to: date | None
    items: list[OpportunityOut]
