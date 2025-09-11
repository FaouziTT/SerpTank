from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project


class SocialMediaCredential(Base):
    __tablename__ = "social_media_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"))
    platform: Mapped[str] = mapped_column(String(50))  # twitter, facebook, linkedin, instagram
    
    # Credential fields (encrypted in production)
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Platform-specific fields
    account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Facebook Page ID, LinkedIn Company ID, etc.
    account_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Connection status
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="social_media_credentials")
    
    def __repr__(self) -> str:
        return f"<SocialMediaCredential(id={self.id}, project_id={self.project_id}, platform={self.platform})>"