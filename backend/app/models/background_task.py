"""
Background task tracking model for monitoring async operations.

This module defines a database model for tracking the status of background tasks
like crawling, analysis, and performance checks.
"""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, 
    JSON, Enum as SQLEnum, Index, Text
)
from sqlalchemy.orm import relationship, Mapped

from app.db.base import Base


class TaskStatus(str, Enum):
    """Status of a background task."""
    PENDING = "pending"
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Type of background task."""
    CRAWL = "crawl"
    WEBSITE_CRAWL = "website_crawl"
    CORE_WEB_VITALS = "core_web_vitals"
    CORE_WEB_VITALS_ANALYSIS = "core_web_vitals_analysis"
    SEO_ANALYSIS = "seo_analysis"
    LOG_ANALYSIS = "log_analysis"
    PERFORMANCE_CHECK = "performance_check"
    REPORT_GENERATION = "report_generation"
    REVENUE_ANALYSIS = "revenue_analysis"
    OTHER = "other"


class BackgroundTask(Base):
    """Track background task execution and status."""
    __tablename__ = "background_tasks"
    
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    
    # Task metadata
    task_type = Column(SQLEnum(TaskType), nullable=False)
    task_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Celery task info (if applicable)
    celery_task_id = Column(String(255), nullable=True, unique=True)
    
    # Status tracking
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0)  # 0-100
    status_message = Column(Text, nullable=True)
    
    # Task parameters and results
    parameters = Column(JSON, default=dict)  # Input parameters
    result = Column(JSON, nullable=True)  # Task results
    error = Column(Text, nullable=True)  # Error message if failed
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Resource tracking
    resource_id = Column(String(255), nullable=True)  # ID of created resource (e.g., crawl_id)
    resource_type = Column(String(100), nullable=True)  # Type of resource created
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="background_tasks")
    site: Mapped[Optional["Site"]] = relationship("Site", back_populates="background_tasks")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_task_user_created", "user_id", "created_at"),
        Index("idx_task_status_type", "status", "task_type"),
        Index("idx_task_site_type", "site_id", "task_type"),
        Index("idx_task_celery", "celery_task_id"),
    )
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "site_id": self.site_id,
            "task_type": self.task_type.value,
            "task_name": self.task_name,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "status_message": self.status_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "result": self.result,
            "error": self.error,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
        }