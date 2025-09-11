from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
import secrets

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"))
    
    # Webhook configuration
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(String(255), default=lambda: secrets.token_urlsafe(32))
    
    # Events to trigger on (stored as JSON array)
    events: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Retry configuration
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="webhooks")
    
    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, project_id={self.project_id}, name={self.name})>"