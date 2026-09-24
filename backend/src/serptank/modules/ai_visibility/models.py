"""AI-visibility data: per-project settings, prompt sets, and sampled observations."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, uuid7


class AiProfile(TenantMixin, TimestampMixin, Base):
    """How we recognise the brand in answers, and how many samples each run takes."""

    __tablename__ = "ai_profiles"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    brand_terms: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False, default=list)
    samples_per_prompt: Mapped[int] = mapped_column(Integer, nullable=False, default=3)


class AiPrompt(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "ai_prompts"
    __table_args__ = (Index("ix_ai_prompts_project", "project_id"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_markets.id", ondelete="CASCADE"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(String(500), nullable=False)
    # Topic link: the tracked keyword this prompt represents (organic rank side by side).
    keyword: Mapped[str | None] = mapped_column(String(300))
    engines: Mapped[list[str]] = mapped_column(ARRAY(String(30)), nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AiObservation(TenantMixin, Base):
    """One sampled answer (hypertable). Failed samples are not stored, only counted."""

    __tablename__ = "ai_observations"
    __table_args__ = (Index("ix_ai_obs_project_date", "project_id", "date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    prompt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine: Mapped[str] = mapped_column(String(30), nullable=False)
    sample: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # AIO shown?
    mentioned: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cited: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mention_rank: Mapped[int | None] = mapped_column(Integer)
    sentiment: Mapped[float | None] = mapped_column(Float)
    # Per competitor domain: whether it was mentioned and/or cited in this answer.
    competitors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    citations: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str] = mapped_column(String(80), nullable=False, default="")
