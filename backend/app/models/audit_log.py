"""
Audit log model for tracking user actions and system events.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AuditLog(Base):
    """Model for storing audit trail entries."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Action details
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User context
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    
    # Change tracking
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    # Additional context
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # Support IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_logs_user_id_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_logs_resource_type_resource_id', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_action_timestamp', 'action', 'timestamp'),
        Index('idx_audit_logs_timestamp', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type}:{self.resource_id}, user_id={self.user_id})>"