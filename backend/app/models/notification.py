"""
Notification models for real-time updates.

This module defines database models for storing user notifications
and managing real-time notification delivery.
"""
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.crawl import Site


class NotificationType(str, Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BILLING = "billing"
    COLLABORATION = "collaboration"


class NotificationCategory(str, Enum):
    """Categories for grouping notifications."""
    GENERAL = "general"
    PERFORMANCE = "performance"
    SEO = "seo"
    SECURITY = "security"
    BILLING = "billing"
    TEAM = "team"
    SYSTEM = "system"
    ALERTS = "alerts"


class Notification(Base):
    """Store user notifications."""
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Notification content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NotificationType] = mapped_column(SQLEnum(NotificationType), nullable=False, default=NotificationType.INFO)
    category: Mapped[NotificationCategory] = mapped_column(SQLEnum(NotificationCategory), nullable=False, default=NotificationCategory.GENERAL)
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Metadata
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional data for the notification
    action_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # URL to navigate to when clicked
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Icon identifier
    
    # Related entities
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    site_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Auto-delete after this time
    
    # Priority and delivery
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher number = higher priority
    deliver_email: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether to also send email
    deliver_push: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether to send push notification
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="notifications")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="notifications")
    site: Mapped[Optional["Site"]] = relationship("Site", back_populates="notifications")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_notification_user_unread", "user_id", "is_read", "is_archived"),
        Index("idx_notification_user_created", "user_id", "created_at"),
        Index("idx_notification_expires", "expires_at"),
    )
    
    def mark_as_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert notification to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "category": self.category,
            "is_read": self.is_read,
            "action_url": self.action_url,
            "icon": self.icon,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "priority": self.priority
        }


class UserNotificationPreference(Base):
    """Store user notification preferences."""
    __tablename__ = "user_notification_preferences"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Email preferences
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_performance_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    email_security_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    email_billing_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    email_team_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    email_weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # In-app preferences
    app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    app_performance_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    app_security_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    app_billing_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    app_team_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Push notification preferences (for future mobile app)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    push_performance_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    push_security_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    push_billing_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Quiet hours
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    quiet_hours_timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Frequency limits
    max_emails_per_day: Mapped[int] = mapped_column(Integer, default=10)
    max_notifications_per_hour: Mapped[int] = mapped_column(Integer, default=20)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notification_preferences")