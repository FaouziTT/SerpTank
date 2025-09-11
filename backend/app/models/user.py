"""
User model for authentication and authorization.

This module defines the SQLAlchemy model for users, including authentication
and authorization-related fields and methods.
"""
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.db.base_class import Base
from app.core.encryption import field_encryption

# This TYPE_CHECKING block is crucial for preventing circular imports
# while still providing type hints to the IDE and type checkers.
if TYPE_CHECKING:
    from .activity import Activity
    from .activity_feed import ActivityFeed
    from .audit_log import AuditLog
    from .crawl import Site, Crawl
    from .domain import Domain
    from .file import File
    from .organization import OrganizationMember, OrganizationInvitation
    from .project import Project
    from .project_team_member import ProjectTeamMember
    from .scenario import Scenario, ThreatScenario
    from .serp_cache import SERPAnalysis, CompetitorTracking, SERPFeatureTracking
    from .settings import (
        ApiKey,
        Integration,
        TeamMember,
        UsageStatistics,
        NotificationSetting,
    )
    from .subscription import Subscription, UsageRecord, BillingEvent
    from .password_reset import PasswordResetToken
    from .notification import Notification, UserNotificationPreference
    from .background_task import BackgroundTask


class User(Base):
    """Model for a user of the application."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # --- Columns Section ---
    # All columns here are correctly defined with modern syntax and optional types.
    # The datetime columns are timezone-aware.
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    organization_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    password_last_changed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    subscription_plan: Mapped[str] = mapped_column(String(50), default="free")
    subscription_status: Mapped[str] = mapped_column(String(50), default="active")
    subscription_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Encrypted API key storage
    _api_key: Mapped[Optional[str]] = mapped_column("api_key", Text, nullable=True, unique=True, index=True)
    
    @hybrid_property
    def api_key(self) -> Optional[str]:
        """Decrypt API key on access."""
        return field_encryption.decrypt(self._api_key) if self._api_key else None
    
    @api_key.setter
    def api_key(self, value: Optional[str]):
        """Encrypt API key on set."""
        self._api_key = field_encryption.encrypt(value) if value else None
    
    # Encrypted Google OAuth tokens
    _google_access_token: Mapped[Optional[str]] = mapped_column("google_access_token", Text, nullable=True)
    _google_refresh_token: Mapped[Optional[str]] = mapped_column("google_refresh_token", Text, nullable=True)
    
    @hybrid_property
    def google_access_token(self) -> Optional[str]:
        """Decrypt Google access token on access."""
        return field_encryption.decrypt(self._google_access_token) if self._google_access_token else None
    
    @google_access_token.setter
    def google_access_token(self, value: Optional[str]):
        """Encrypt Google access token on set."""
        self._google_access_token = field_encryption.encrypt(value) if value else None
    
    @hybrid_property
    def google_refresh_token(self) -> Optional[str]:
        """Decrypt Google refresh token on access."""
        return field_encryption.decrypt(self._google_refresh_token) if self._google_refresh_token else None
    
    @google_refresh_token.setter
    def google_refresh_token(self, value: Optional[str]):
        """Encrypt Google refresh token on set."""
        self._google_refresh_token = field_encryption.encrypt(value) if value else None
    
    google_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    google_scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # --- Auth System 2.0 Fields ---
    auth_provider: Mapped[str] = mapped_column(String(50), default="email")
    google_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_via: Mapped[str] = mapped_column(String(50), default="registration")
    
    # --- Relationships Section (Corrected) ---
    # Each relationship now correctly uses back_populates to create a
    # fully explicit, bi-directional link with the corresponding model.
    
    domains: Mapped[List["Domain"]] = relationship("Domain", back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    project_memberships: Mapped[List["ProjectTeamMember"]] = relationship("ProjectTeamMember", back_populates="user", cascade="all, delete-orphan")

    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    usage_records: Mapped[List["UsageRecord"]] = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")
    billing_events: Mapped[List["BillingEvent"]] = relationship("BillingEvent", back_populates="user", cascade="all, delete-orphan")
    
    organization_memberships: Mapped[List["OrganizationMember"]] = relationship("OrganizationMember", foreign_keys="[OrganizationMember.user_id]", back_populates="user", cascade="all, delete-orphan")
    sent_invitations: Mapped[List["OrganizationInvitation"]] = relationship("OrganizationInvitation", foreign_keys="[OrganizationInvitation.invited_by_user_id]", back_populates="invited_by")
    
    sites: Mapped[List["Site"]] = relationship("Site", back_populates="user", cascade="all, delete-orphan")
    crawls: Mapped[List["Crawl"]] = relationship("Crawl", back_populates="user", cascade="all, delete-orphan")
    
    team_members: Mapped[List["TeamMember"]] = relationship("TeamMember", back_populates="user", cascade="all, delete-orphan")
    integrations: Mapped[List["Integration"]] = relationship("Integration", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_settings: Mapped[List["NotificationSetting"]] = relationship("NotificationSetting", back_populates="user", cascade="all, delete-orphan")
    notification_preferences: Mapped[Optional["UserNotificationPreference"]] = relationship("UserNotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    usage_statistics: Mapped[List["UsageStatistics"]] = relationship("UsageStatistics", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    
    activities: Mapped[List["Activity"]] = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    scenarios: Mapped[List["Scenario"]] = relationship("Scenario", back_populates="user", cascade="all, delete-orphan")
    threat_scenarios: Mapped[List["ThreatScenario"]] = relationship("ThreatScenario", back_populates="user", cascade="all, delete-orphan")
    
    serp_analyses: Mapped[List["SERPAnalysis"]] = relationship("SERPAnalysis", back_populates="user", cascade="all, delete-orphan")
    competitor_tracking: Mapped[List["CompetitorTracking"]] = relationship("CompetitorTracking", back_populates="user", cascade="all, delete-orphan")
    serp_feature_tracking: Mapped[List["SERPFeatureTracking"]] = relationship("SERPFeatureTracking", back_populates="user", cascade="all, delete-orphan")
    
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    
    background_tasks: Mapped[List["BackgroundTask"]] = relationship("BackgroundTask", back_populates="user", cascade="all, delete-orphan")
    
    files: Mapped[List["File"]] = relationship("File", back_populates="user", cascade="all, delete-orphan")
    
    activity_feed_items: Mapped[List["ActivityFeed"]] = relationship("ActivityFeed", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"