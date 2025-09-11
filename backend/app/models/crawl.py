"""
Database models for website crawls and related data.

This module defines SQLAlchemy models for storing crawl data,
including crawl metadata, crawled URLs, and analysis results.
"""
import uuid
from datetime import datetime, timezone
# --- Import typing helpers ---
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.schemas.diagnostic import CrawlStatus

# --- START: Add this type-checking block ---
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.performance import PerformanceMetric, PerformanceBenchmark, PerformanceAlert
    from app.models.notification import Notification
    from app.models.background_task import BackgroundTask
    from app.models.activity_feed import ActivityFeed
    # Note: Site is defined in this file, so it doesn't need to be imported here.
# --- END: Add this type-checking block ---


class Crawl(Base):
    """Model for a website crawl."""
    
    __tablename__ = "crawls"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    site_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sites.id"), nullable=True)
    
    start_url: Mapped[str] = mapped_column(String(2048))
    max_urls: Mapped[int] = mapped_column(Integer, default=1000)
    respect_robots_txt: Mapped[bool] = mapped_column(Boolean, default=True)
    crawl_javascript: Mapped[bool] = mapped_column(Boolean, default=True)
    follow_external_links: Mapped[bool] = mapped_column(Boolean, default=False)
    
    status: Mapped[CrawlStatus] = mapped_column(Enum(CrawlStatus), default=CrawlStatus.STARTED)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    urls_crawled: Mapped[int] = mapped_column(Integer, default=0)
    urls_found: Mapped[int] = mapped_column(Integer, default=0)
    
    # --- FIX: Update relationships to use modern Mapped syntax ---
    user: Mapped["User"] = relationship("User", back_populates="crawls")
    site: Mapped[Optional["Site"]] = relationship("Site", back_populates="crawls")
    crawled_urls: Mapped[List["CrawlUrl"]] = relationship("CrawlUrl", back_populates="crawl", cascade="all, delete-orphan")
    crawl_analysis: Mapped[Optional["CrawlAnalysis"]] = relationship("CrawlAnalysis", back_populates="crawl", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Crawl(id={self.id}, status={self.status}, urls_crawled={self.urls_crawled})>"


class CrawlUrl(Base):
    """Model for a URL crawled during a website crawl."""
    
    __tablename__ = "crawl_urls"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[str] = mapped_column(String(36), ForeignKey("crawls.id"))
    
    url: Mapped[str] = mapped_column(String(2048))
    normalized_url: Mapped[str] = mapped_column(String(2048))
    status_code: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    content_length: Mapped[int] = mapped_column(Integer, default=0)
    crawl_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # --- FIX: Update relationship to use modern Mapped syntax ---
    crawl: Mapped["Crawl"] = relationship("Crawl", back_populates="crawled_urls")
    
    def __repr__(self) -> str:
        return f"<CrawlUrl(id={self.id}, url={self.url}, status_code={self.status_code})>"


class CrawlAnalysis(Base):
    """Model for analysis results of a website crawl."""
    
    __tablename__ = "crawl_analyses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_id: Mapped[str] = mapped_column(String(36), ForeignKey("crawls.id"), unique=True)
    
    analysis_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    crawlability_score: Mapped[int] = mapped_column(Integer)
    indexable_pages: Mapped[int] = mapped_column(Integer)
    non_indexable_pages: Mapped[int] = mapped_column(Integer)
    
    crawl_depth_distribution: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    content_type_distribution: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    status_code_distribution: Mapped[dict] = mapped_column(JSONB, default=lambda: {})
    
    issues: Mapped[List[dict]] = mapped_column(JSONB, default=lambda: [])
    recommendations: Mapped[List[dict]] = mapped_column(JSONB, default=lambda: [])
    
    # --- FIX: Update relationship to use modern Mapped syntax ---
    crawl: Mapped["Crawl"] = relationship("Crawl", back_populates="crawl_analysis")
    
    def __repr__(self) -> str:
        return f"<CrawlAnalysis(id={self.id}, crawl_id={self.crawl_id})>"


class Site(Base):
    """Model for a website being monitored."""
    
    __tablename__ = "sites"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    crawl_schedule: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    max_urls_per_crawl: Mapped[int] = mapped_column(Integer, default=1000)
    respect_robots_txt: Mapped[bool] = mapped_column(Boolean, default=True)
    crawl_javascript: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Track last crawl time
    last_crawled: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # --- FIX: Update relationships to use modern Mapped syntax ---
    user: Mapped["User"] = relationship("User", back_populates="sites")
    crawls: Mapped[List["Crawl"]] = relationship("Crawl", back_populates="site")
    performance_metrics: Mapped[List["PerformanceMetric"]] = relationship("PerformanceMetric", back_populates="site")
    performance_benchmarks: Mapped[List["PerformanceBenchmark"]] = relationship("PerformanceBenchmark", back_populates="site")
    performance_alerts: Mapped[List["PerformanceAlert"]] = relationship("PerformanceAlert", back_populates="site")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="site", cascade="all, delete-orphan")
    background_tasks: Mapped[List["BackgroundTask"]] = relationship("BackgroundTask", back_populates="site", cascade="all, delete-orphan")
    activity_feed: Mapped[List["ActivityFeed"]] = relationship("ActivityFeed", back_populates="site", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name={self.name}, url={self.url})>"