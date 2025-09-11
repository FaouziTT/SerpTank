"""
Password reset token model.

This module defines the SQLAlchemy model for password reset tokens,
used for secure password recovery functionality.
"""
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
import secrets

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User


class PasswordResetToken(Base):
    """Model for password reset tokens."""
    
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Token details
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Expiration and usage tracking
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")
    
    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_for_user(cls, user_id: int, expiry_hours: int = 1) -> "PasswordResetToken":
        """Create a new password reset token for a user."""
        return cls(
            token=cls.generate_token(),
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        )
    
    def is_valid(self) -> bool:
        """Check if the token is still valid."""
        return (
            not self.used and 
            datetime.now(timezone.utc) < self.expires_at
        )
    
    def mark_as_used(self) -> None:
        """Mark the token as used."""
        self.used = True
        self.used_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"