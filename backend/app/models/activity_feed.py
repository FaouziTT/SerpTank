"""
Activity Feed models for tracking user and system activities.

This module defines database models for storing activity feed items
that are displayed in real-time dashboards and activity logs.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    JSON, Enum as SQLEnum, Index, Boolean, Float
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class ActivityType(str, Enum):
    """Types of activities."""
    # User activities
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_UPDATE = "user_update"
    
    # Site activities
    SITE_CREATED = "site_created"
    SITE_UPDATED = "site_updated"
    SITE_DELETED = "site_deleted"
    SITE_CRAWLED = "site_crawled"
    
    # Performance activities
    PERFORMANCE_ANALYZED = "performance_analyzed"
    PERFORMANCE_ALERT = "performance_alert"
    PERFORMANCE_IMPROVED = "performance_improved"
    PERFORMANCE_DEGRADED = "performance_degraded"
    
    # SEO activities
    SERP_ANALYZED = "serp_analyzed"
    KEYWORD_RANKED = "keyword_ranked"
    COMPETITOR_ADDED = "competitor_added"
    BACKLINK_GAINED = "backlink_gained"
    
    # Content activities
    CONTENT_CREATED = "content_created"
    CONTENT_PUBLISHED = "content_published"
    CONTENT_OPTIMIZED = "content_optimized"
    
    # Team activities
    MEMBER_INVITED = "member_invited"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    PERMISSION_CHANGED = "permission_changed"
    
    # System activities
    SYSTEM_UPDATE = "system_update"
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    API_KEY_CREATED = "api_key_created"


class ActivityFeed(Base):
    """Store activity feed items."""
    __tablename__ = "activity_feed"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Activity details
    type = Column(SQLEnum(ActivityType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Actor information
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name = Column(String(255), nullable=True)  # Denormalized for performance
    user_avatar = Column(String(512), nullable=True)  # Denormalized for performance
    
    # Related entities
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    
    # Metadata
    data = Column(JSON, nullable=True)  # Additional activity-specific data
    url = Column(String(512), nullable=True)  # Related URL if applicable
    ip_address = Column(String(45), nullable=True)  # IP address for security activities
    user_agent = Column(String(512), nullable=True)  # User agent for security activities
    
    # Visibility
    is_public = Column(Boolean, default=True)  # Whether visible to all org members
    is_system = Column(Boolean, default=False)  # System-generated activity
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="activity_feed_items")
    organization = relationship("Organization", back_populates="activity_feed")
    project = relationship("Project", back_populates="activity_feed")
    site = relationship("Site", back_populates="activity_feed")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_activity_org_created", "organization_id", "created_at"),
        Index("idx_activity_project_created", "project_id", "created_at"),
        Index("idx_activity_user_created", "user_id", "created_at"),
        Index("idx_activity_type_created", "type", "created_at"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert activity to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "user": {
                "id": self.user_id,
                "name": self.user_name,
                "avatar": self.user_avatar
            } if self.user_id else None,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "site_id": self.site_id,
            "data": self.data,
            "url": self.url,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ActivitySummary(Base):
    """Store daily activity summaries for performance."""
    __tablename__ = "activity_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Activity counts by type
    total_activities = Column(Integer, default=0)
    user_activities = Column(Integer, default=0)
    site_activities = Column(Integer, default=0)
    performance_activities = Column(Integer, default=0)
    seo_activities = Column(Integer, default=0)
    content_activities = Column(Integer, default=0)
    team_activities = Column(Integer, default=0)
    
    # Key metrics
    active_users = Column(Integer, default=0)
    pages_analyzed = Column(Integer, default=0)
    keywords_tracked = Column(Integer, default=0)
    alerts_triggered = Column(Integer, default=0)
    
    # Performance metrics
    avg_lcp = Column(Float, nullable=True)
    avg_fid = Column(Float, nullable=True)
    avg_cls = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="activity_summaries")
    
    # Indexes
    __table_args__ = (
        Index("idx_summary_org_date", "organization_id", "date", unique=True),
    )


# Import Float for the model
from sqlalchemy import Float