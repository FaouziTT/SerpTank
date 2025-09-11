from datetime import datetime, timezone
# --- Import List and TYPE_CHECKING for modern type hinting ---
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.project_team_member import ProjectTeamMember

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization
    from app.models.domain import Domain # Assuming this is the location of the Domain model
    from app.models.notification import Notification
    from app.models.social_media_credential import SocialMediaCredential
    from app.models.webhook import Webhook
    from app.models.domain_verification import DomainVerification
    from app.models.file import File
    from app.models.activity_feed import ActivityFeed
# --- END: Add this type-checking block ---


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("domains.id"), nullable=True)
    
    # Google Analytics 4 Configuration (per-project)
    ga4_property_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ga4_measurement_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # G-XXXXXXXXXX
    ga4_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Project-specific settings
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    profitability_tracking: Mapped[bool] = mapped_column(Boolean, default=True)
    monthly_seo_budget: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # Monthly SEO investment for ROI calculations
    
    # Setup status tracking
    setup_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON field for tracking initial analysis progress
    
    # Use timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # --- FIX: Update relationships to use modern Mapped syntax ---
    user: Mapped["User"] = relationship("User", back_populates="projects")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="projects")
    domain: Mapped[Optional["Domain"]] = relationship("Domain", back_populates="projects")
    team_members: Mapped[List["ProjectTeamMember"]] = relationship("ProjectTeamMember", back_populates="project", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="project", cascade="all, delete-orphan")
    
    # New relationships for settings features
    social_media_credentials: Mapped[List["SocialMediaCredential"]] = relationship("SocialMediaCredential", back_populates="project", cascade="all, delete-orphan")
    webhooks: Mapped[List["Webhook"]] = relationship("Webhook", back_populates="project", cascade="all, delete-orphan")
    domain_verification: Mapped[Optional["DomainVerification"]] = relationship("DomainVerification", back_populates="project", uselist=False, cascade="all, delete-orphan")
    files: Mapped[List["File"]] = relationship("File", back_populates="project", cascade="all, delete-orphan")
    activity_feed: Mapped[List["ActivityFeed"]] = relationship("ActivityFeed", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, url={self.url}, user_id={self.user_id})>"