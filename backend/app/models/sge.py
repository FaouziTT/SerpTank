
"""
Database models for the SGE Readiness Engine.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base_class import Base

class SGEAnalysis(Base):
    __tablename__ = "sge_analyses"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text)
    target_queries = Column(JSONB)
    content_type = Column(String)
    optimization_results = Column(JSONB)
    overall_sge_readiness = Column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User")

class SGEMonitor(Base):
    __tablename__ = "sge_monitors"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    monitor_data = Column(JSONB)
    status = Column(String, nullable=False, default="ACTIVE")
    results = Column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
