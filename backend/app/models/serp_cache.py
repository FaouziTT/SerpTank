"""
SERP Cache model for storing SERP analysis results.

This model stores cached SERP analysis data to avoid repeated API calls
and provide historical tracking of SERP changes.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class SERPAnalysis(Base):
    """Model for cached SERP analysis data."""
    
    __tablename__ = "serp_analyses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    
    # Query information
    query: Mapped[str] = mapped_column(String(500), index=True)
    location: Mapped[str] = mapped_column(String(255), default="United States")
    device: Mapped[str] = mapped_column(String(50), default="desktop")
    
    # Analysis results (stored as JSON)
    organic_results: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    serp_features: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    competitors: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    
    # Metrics
    organic_count: Mapped[int] = mapped_column(Integer, default=0)
    paid_count: Mapped[int] = mapped_column(Integer, default=0)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    competition_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    opportunity_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="serp_analyses")
    
    def __repr__(self) -> str:
        return f"<SERPAnalysis(id={self.id}, query={self.query}, user_id={self.user_id})>"


class CompetitorTracking(Base):
    """Model for tracking competitor SERP positions over time."""
    
    __tablename__ = "competitor_tracking"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    
    # Competitor information
    domain: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Metrics
    authority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    backlinks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    traffic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    keywords: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Position tracking
    positions: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # {keyword: position}
    avg_position: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="competitor_tracking")
    
    def __repr__(self) -> str:
        return f"<CompetitorTracking(id={self.id}, domain={self.domain}, user_id={self.user_id})>"


class SERPFeatureTracking(Base):
    """Model for tracking SERP features over time."""
    
    __tablename__ = "serp_feature_tracking"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    query: Mapped[str] = mapped_column(String(500), index=True)
    
    # Feature information
    feature_name: Mapped[str] = mapped_column(String(100), index=True)
    feature_type: Mapped[str] = mapped_column(String(100))
    position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ctr_impact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="serp_feature_tracking")
    
    def __repr__(self) -> str:
        return f"<SERPFeatureTracking(id={self.id}, feature={self.feature_name}, query={self.query})>"