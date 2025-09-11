"""
Database models for the Content Velocity Workflow.
"""
from datetime import datetime, timezone
# --- Import typing helpers ---
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
# --- Import modern syntax ---
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base_class import Base

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.user import User
# --- END: Add this type-checking block ---


class ContentBrief(Base):
    __tablename__ = "content_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    brief_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    brief: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    user: Mapped["User"] = relationship("User")


class ContentEnhancement(Base):
    __tablename__ = "content_enhancements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    enhancement_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    url: Mapped[str] = mapped_column(String)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    enhancement_package: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")