"""
Domain Model for domain verification and management.
"""
from datetime import datetime, timezone
# --- Import List and TYPE_CHECKING for modern type hinting ---
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project # Assuming a Project can be related to a Domain
# --- END: Add this type-checking block ---


class Domain(Base):
    """Model for a domain being monitored by a user."""
    
    __tablename__ = "domains"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    # Domain information
    domain: Mapped[str] = mapped_column(String(255), index=True)
    subdomain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_domain: Mapped[str] = mapped_column(String(255), index=True)
    
    # Verification information
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    verification_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    verification_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status and monitoring
    status: Mapped[str] = mapped_column(String(50), default="pending")
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Google integrations
    in_search_console: Mapped[bool] = mapped_column(Boolean, default=False)
    in_analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # --- FIX: Update relationship to use modern Mapped syntax ---
    user: Mapped["User"] = relationship("User", back_populates="domains")
    
    # --- ADDED: The back-relationship from your Project model ---
    # This assumes 'backref="projects"' in the Project model's domain relationship
    # If you used 'back_populates', this line should be adjusted accordingly.
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="domain")

    def __repr__(self) -> str:
        return f"<Domain(id={self.id}, domain={self.full_domain}, verified={self.is_verified})>"