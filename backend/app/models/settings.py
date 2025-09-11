from datetime import datetime, timezone
from typing import Optional, List # Import Optional and List for modern type hinting

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
)
# Import Mapped and mapped_column for the modern syntax
from sqlalchemy.orm import relationship, Mapped, mapped_column


from app.db.base_class import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Active")
    
    # --- FIX: Make timezone-aware and nullable ---
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Use timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship("User", back_populates="team_members")


class Integration(Base):
    __tablename__ = "integrations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Disconnected")

    # --- FIX: Ensure it's nullable ---
    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    # Use timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship("User", back_populates="integrations")


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(String, default="Real-time")
    channels: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as string
    
    # Use timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship("User", back_populates="notification_settings")


class UsageStatistics(Base):
    __tablename__ = "usage_statistics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    api_requests: Mapped[int] = mapped_column(Integer, default=0)
    api_requests_limit: Mapped[int] = mapped_column(Integer, default=50000)
    data_storage_gb: Mapped[float] = mapped_column(Float, default=0.0)
    data_storage_limit_gb: Mapped[float] = mapped_column(Float, default=25.0)
    team_members: Mapped[int] = mapped_column(Integer, default=1)
    team_members_limit: Mapped[int] = mapped_column(Integer, default=10)
    websites_monitored: Mapped[int] = mapped_column(Integer, default=0)
    websites_limit: Mapped[int] = mapped_column(Integer, default=5)
    
    # Use timezone-aware datetime
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship("User", back_populates="usage_statistics")


class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    key_hash: Mapped[str] = mapped_column(String)
    key_preview: Mapped[str] = mapped_column(String)

    # --- FIX: Ensure it's nullable ---
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Use timezone-aware datetime
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # In class ApiKey:
    user: Mapped["User"] = relationship("User", back_populates="api_keys")