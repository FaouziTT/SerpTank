"""
Activity model for tracking user activities and system events.

This module defines the SQLAlchemy model for activities, including user actions,
system events, and audit trail functionality.
"""
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization


class Activity(Base):
    """Model for tracking user activities and system events."""
    
    __tablename__ = "activities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Activity identification
    activity_type: Mapped[str] = mapped_column(String(50), index=True)  # crawl, content, performance, user, system
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    
    # User and organization context
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    
    # Activity details
    status: Mapped[str] = mapped_column(String(50), default="completed")  # pending, processing, completed, failed
    activity_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional activity-specific data
    
    # Timestamps - Use timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="activities")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="activities")
    
    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, type={self.activity_type}, title={self.title})>"
    
    @property
    def timestamp(self) -> str:
        """Return a human-readable timestamp for the activity."""
        now = datetime.now(timezone.utc)
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now" 