"""Project and target-market API models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from serptank.core.models import AIEngine, Device, SearchEngine
from serptank.modules.projects.verification import VerificationMethod


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MarketIn(StrictModel):
    country: str = Field(pattern=r"^[A-Za-z]{2}$", description="ISO 3166-1 alpha-2")
    language: str = Field(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", description="BCP 47")
    location: str | None = Field(default=None, max_length=200)
    device: Device = Device.DESKTOP
    search_engines: list[SearchEngine] = Field(default=[SearchEngine.GOOGLE], min_length=1)
    ai_engines: list[AIEngine] = Field(default_factory=list)


class MarketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    country: str
    language: str
    location: str | None
    device: Device
    search_engines: list[SearchEngine]
    ai_engines: list[AIEngine]


class ProjectCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    domain: str = Field(min_length=3, max_length=300)
    markets: list[MarketIn] = Field(
        default_factory=lambda: [MarketIn(country="US", language="en")], max_length=25
    )


class ProjectUpdate(StrictModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    primary_domain: str
    verified: bool
    verification_method: str | None
    created_at: datetime
    markets: list[MarketOut]


class VerificationStart(StrictModel):
    method: VerificationMethod


class VerificationInstructions(BaseModel):
    method: VerificationMethod
    token: str
    dns_record_name: str | None = None
    dns_record_value: str | None = None
    file_url: str | None = None
    file_contents: str | None = None


class VerificationResult(BaseModel):
    verified: bool
    detail: str
