"""
Multi-tenancy models.

This module defines SQLAlchemy models for managing organizations,
team members, roles, and tenant-based data isolation.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.activity import Activity
    from app.models.activity_feed import ActivityFeed, ActivitySummary
    from app.models.scenario import Scenario, ThreatScenario
    from app.models.notification import Notification
    from app.models.file import File
    from app.models.project import Project
    # --- Add missing import for OrganizationDomain relationship ---
    from app.models.domain import Domain 


class OrganizationStatus(str, Enum):
    """Organization status enum."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class MemberRole(str, Enum):
    """Team member roles enum."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class MemberStatus(str, Enum):
    """Team member status enum."""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class Organization(Base):
    """Model for organizations/tenants."""
    
    __tablename__ = "organizations"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    status: Mapped[OrganizationStatus] = mapped_column(SQLEnum(OrganizationStatus), default=OrganizationStatus.ACTIVE)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    data_region: Mapped[str] = mapped_column(String(50), default="us-east-1")
    settings: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware
    index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware 
    onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    members: Mapped[List["OrganizationMember"]] = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    invitations: Mapped[List["OrganizationInvitation"]] = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    domains: Mapped[List["OrganizationDomain"]] = relationship("OrganizationDomain", back_populates="organization", cascade="all, delete-orphan")
    audit_logs: Mapped[List["OrganizationAuditLog"]] = relationship("OrganizationAuditLog", back_populates="organization", cascade="all, delete-orphan")
    
    activities: Mapped[List["Activity"]] = relationship("Activity", back_populates="organization", cascade="all, delete-orphan")
    scenarios: Mapped[List["Scenario"]] = relationship("Scenario", back_populates="organization", cascade="all, delete-orphan")
    threat_scenarios: Mapped[List["ThreatScenario"]] = relationship("ThreatScenario", back_populates="organization", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="organization", cascade="all, delete-orphan")
    files: Mapped[List["File"]] = relationship("File", back_populates="organization", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    activity_feed: Mapped[List["ActivityFeed"]] = relationship("ActivityFeed", back_populates="organization", cascade="all, delete-orphan")
    activity_summaries: Mapped[List["ActivitySummary"]] = relationship("ActivitySummary", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        try:
            return f"<Organization(id={self.id}, name={self.name}, status={self.status})>"
        except Exception:
            # If attributes are not loaded (detached from session), just show the id
            return f"<Organization(id={getattr(self, 'id', 'unknown')})>"


class OrganizationMember(Base):
    """Model for organization team members."""
    
    __tablename__ = "organization_members"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    role: Mapped[MemberRole] = mapped_column(SQLEnum(MemberRole))
    status: Mapped[MemberStatus] = mapped_column(SQLEnum(MemberStatus), default=MemberStatus.ACTIVE)
    
    invited_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    dashboard_preferences: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware
    index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware 
    onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='unique_org_user'),
    )
      
    organization: Mapped["Organization"] = relationship("Organization", back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="organization_memberships")
    invited_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[invited_by_user_id])
    
    def __repr__(self) -> str:
        return f"<OrganizationMember(id={self.id}, org={self.organization_id}, user={self.user_id}, role={self.role})>"


class OrganizationInvitation(Base):
    """Model for pending organization invitations."""
    
    __tablename__ = "organization_invitations"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    invited_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[MemberRole] = mapped_column(SQLEnum(MemberRole))
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware
    index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware 
    onupdate=lambda: datetime.now(timezone.utc))

    organization: Mapped["Organization"] = relationship("Organization", back_populates="invitations")
    invited_by: Mapped["User"] = relationship("User", foreign_keys=[invited_by_user_id], back_populates="sent_invitations")
    
    def is_valid(self) -> bool:
        """Check if invitation is still valid."""
        return not self.is_accepted and not self.is_expired and self.expires_at > datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<OrganizationInvitation(id={self.id}, email={self.email}, org={self.organization_id})>"


class OrganizationDomain(Base):
    """Model for custom domains owned by organizations."""
    
    __tablename__ = "organization_domains"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ssl_cert_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
      
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware
    index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware 
    onupdate=lambda: datetime.now(timezone.utc))

    organization: Mapped["Organization"] = relationship("Organization", back_populates="domains")
    
    def __repr__(self) -> str:
        return f"<OrganizationDomain(id={self.id}, domain={self.domain}, org={self.organization_id})>"


class OrganizationAuditLog(Base):
    """Model for organization audit logs."""
    
    __tablename__ = "organization_audit_logs"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
      
    details: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # --- FIX: Make datetime default timezone-aware ---
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),  # UTC timezone-aware
    index=True)
    
    organization: Mapped["Organization"] = relationship("Organization", back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self) -> str:
        return f"<OrganizationAuditLog(id={self.id}, action={self.action}, org={self.organization_id})>"