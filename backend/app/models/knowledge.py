"""
Database models for the Institutional Knowledge Engine.
"""
from datetime import datetime, timezone
# --- Import typing helpers ---
from typing import Optional, List, TYPE_CHECKING, Dict, Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
# --- Import modern syntax ---
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base_class import Base

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.user import User
# --- END: Add this type-checking block ---


class StrategicLedger(Base):
    __tablename__ = "strategic_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    strategy_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    strategy_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    execution_period: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    key_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    learnings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User")


class TuningInsight(Base):
    __tablename__ = "tuning_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    insight_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    model_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    performance_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User")


class PersonalizedRecommendation(Base):
    __tablename__ = "personalized_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recommendation_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    recommendations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User")


class CapturedKnowledge(Base):
    __tablename__ = "captured_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    knowledge_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    insights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User")


class CompetitiveIntelligence(Base):
    __tablename__ = "competitive_intelligence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    intelligence_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    competitors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    intelligence_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    insights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    analysis_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User")

    # The to_dict method is perfectly fine and can stay as is.
    # Added type hints for clarity.
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intelligence_id": self.intelligence_id,
            "user_id": self.user_id,
            "competitors": self.competitors,
            "intelligence_data": self.intelligence_data,
            "insights": self.insights,
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
        }