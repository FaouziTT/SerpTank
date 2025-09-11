from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING
import secrets

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project


class DomainVerification(Base):
    __tablename__ = "domain_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), unique=True)
    
    # Domain info
    domain: Mapped[str] = mapped_column(String(255))
    
    # Verification details
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # dns_txt, html_file, meta_tag
    verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=lambda: secrets.token_urlsafe(32))
    
    # Verification timestamps
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="domain_verification", uselist=False)
    
    def is_expired(self) -> bool:
        """Check if verification has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def set_verified(self):
        """Mark domain as verified and set expiration"""
        self.verified = True
        self.verified_at = datetime.now(timezone.utc)
        # Verification expires after 1 year
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    
    def __repr__(self) -> str:
        return f"<DomainVerification(id={self.id}, domain={self.domain}, verified={self.verified})>"