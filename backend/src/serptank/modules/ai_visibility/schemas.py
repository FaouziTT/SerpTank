"""AI-visibility API models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from serptank.core.models import AIEngine


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EngineStatus(BaseModel):
    engine: str
    selected: bool  # in at least one market's AI engines
    entitled: bool  # included in the plan
    available: bool  # this server can sample it
    note: str | None


class AiSettingsOut(BaseModel):
    brand_terms: list[str]
    samples_per_prompt: int
    prompts_used_this_month: int
    prompts_per_month: int
    engines: list[EngineStatus]


class AiSettingsIn(StrictModel):
    brand_terms: list[str] = Field(default_factory=list, max_length=10)
    samples_per_prompt: int = Field(default=3, ge=1, le=10)


class PromptsIn(StrictModel):
    market_id: uuid.UUID
    prompts: list[str] = Field(min_length=1, max_length=50)
    keyword: str | None = Field(default=None, max_length=300)
    engines: list[AIEngine] = Field(default_factory=list)


class PromptUpdate(StrictModel):
    active: bool


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_id: uuid.UUID
    prompt: str
    keyword: str | None
    engines: list[str]
    active: bool
    created_at: datetime


class PromptsAdded(BaseModel):
    added: int
    skipped_existing: int


class PromptSuggestion(BaseModel):
    prompt: str
    keyword: str
    intent: str


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date
    prompt_id: uuid.UUID
    engine: str
    sample: int
    answered: bool
    mentioned: bool
    cited: bool
    mention_rank: int | None
    sentiment: float | None
    competitors: dict[str, Any]
    citations: list[str]
    excerpt: str
    model: str


class RateOut(BaseModel):
    successes: int
    trials: int
    rate: float | None
    low: float | None
    high: float | None


class EngineVisibility(BaseModel):
    engine: str
    samples: int
    answer_rate: RateOut
    mention_rate: RateOut
    citation_rate: RateOut
    avg_sentiment: float | None
    avg_mention_rank: float | None


class ShareRow(BaseModel):
    domain: str
    is_own: bool
    mentions: int
    citations: int
    share: float | None


class PromptVisibility(BaseModel):
    prompt_id: uuid.UUID
    prompt: str
    keyword: str | None
    active: bool
    organic_position: float | None
    engines: dict[str, dict[str, int]]


class FirstPartyRow(BaseModel):
    source: str
    surface: str
    impressions: int
    clicks: int
    citations: int


class VisibilityOut(BaseModel):
    days: int
    engines: list[EngineVisibility]
    share_of_voice: list[ShareRow]
    prompts: list[PromptVisibility]
    first_party: list[FirstPartyRow]


class ReadinessComponent(BaseModel):
    id: str
    label: str
    weight: int
    score: int
    findings: list[str]


class ReadinessOut(BaseModel):
    available: bool
    score: int | None
    crawl_id: uuid.UUID | None
    components: list[ReadinessComponent]
    bots: dict[str, bool | None]
    note: str | None
