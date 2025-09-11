"""
Database models for the Market Simulation Engine.
"""
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING # Import TYPE_CHECKING and others

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column # Import modern syntax

from app.db.base_class import Base

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization
# --- END: Add this type-checking block ---


class Scenario(Base):
    __tablename__ = "scenarios"

    # Using modern mapped_column syntax for consistency and better type hinting
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships are now correctly typed
    organization: Mapped["Organization"] = relationship("Organization", back_populates="scenarios")
    user: Mapped["User"] = relationship("User", back_populates="scenarios")
    playbooks: Mapped[List["Playbook"]] = relationship("Playbook", back_populates="scenario")


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    playbook_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    scenario_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenarios.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pathway_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    estimated_success_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_timeframe_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_resource_cost: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    estimated_roi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strategy: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timeline: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    outcomes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="playbooks")


class ThreatScenario(Base):
    __tablename__ = "threat_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    threat_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    threat_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    priority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="threat_scenarios")
    user: Mapped["User"] = relationship("User", back_populates="threat_scenarios")