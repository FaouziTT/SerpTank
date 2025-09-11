"""
Performance metrics models for storing Core Web Vitals data.

This module defines database models for storing historical performance data
including Core Web Vitals metrics from both lab and field data.
"""
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    JSON, Boolean, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.crawl import Site


class PerformanceMetric(Base):
    """Store Core Web Vitals metrics for a URL."""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)  # Specific URL tested
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False)  # When the data was collected by Google
    
    # Device type
    device_type = Column(String, nullable=False, default="mobile")  # mobile, desktop, tablet, all
    
    # Data source
    data_source = Column(String, nullable=False)  # "lighthouse", "crux", "both"
    
    # Core Web Vitals - Lab Data (Lighthouse)
    lab_lcp = Column(Float)  # Largest Contentful Paint (seconds)
    lab_fid = Column(Float)  # First Input Delay (milliseconds)
    lab_cls = Column(Float)  # Cumulative Layout Shift (score)
    lab_ttfb = Column(Float)  # Time to First Byte (milliseconds)
    lab_fcp = Column(Float)  # First Contentful Paint (seconds)
    lab_si = Column(Float)  # Speed Index (seconds)
    lab_tbt = Column(Float)  # Total Blocking Time (milliseconds)
    lab_tti = Column(Float)  # Time to Interactive (seconds)
    
    # Core Web Vitals - Field Data (CrUX)
    field_lcp = Column(Float)  # p75 value
    field_fid = Column(Float)  # p75 value
    field_cls = Column(Float)  # p75 value
    field_inp = Column(Float)  # Interaction to Next Paint (p75)
    field_ttfb = Column(Float)  # p75 value
    field_fcp = Column(Float)  # p75 value
    
    # Lighthouse Performance Score
    performance_score = Column(Float)  # 0-100
    
    # CrUX Histogram Data (percentage of users)
    lcp_good = Column(Float)  # % of users with good LCP
    lcp_needs_improvement = Column(Float)  # % of users with needs improvement
    lcp_poor = Column(Float)  # % of users with poor LCP
    
    fid_good = Column(Float)
    fid_needs_improvement = Column(Float)
    fid_poor = Column(Float)
    
    cls_good = Column(Float)
    cls_needs_improvement = Column(Float)
    cls_poor = Column(Float)
    
    inp_good = Column(Float)
    inp_needs_improvement = Column(Float)
    inp_poor = Column(Float)
    
    # Additional metadata
    crux_collection_period = Column(JSON)  # {"first_date": {...}, "last_date": {...}}
    lighthouse_version = Column(String)
    
    # Raw data for advanced analysis
    raw_lighthouse_data = Column(JSON)
    raw_crux_data = Column(JSON)
    
    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="performance_metrics")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_performance_site_created", "site_id", "created_at"),
        Index("idx_performance_site_device", "site_id", "device_type"),
        Index("idx_performance_url_created", "url", "created_at"),
    )


class PerformanceBenchmark(Base):
    """Store performance benchmarks for competitive analysis."""
    __tablename__ = "performance_benchmarks"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    competitor_url = Column(String, nullable=False)
    competitor_name = Column(String)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Device type
    device_type = Column(String, nullable=False, default="mobile")
    
    # Competitor Core Web Vitals
    lcp = Column(Float)
    fid = Column(Float)
    cls = Column(Float)
    inp = Column(Float)
    ttfb = Column(Float)
    performance_score = Column(Float)
    
    # Comparison flags
    lcp_better = Column(Boolean)  # True if our site is better
    fid_better = Column(Boolean)
    cls_better = Column(Boolean)
    inp_better = Column(Boolean)
    overall_better = Column(Boolean)
    
    # Raw data
    raw_data = Column(JSON)
    
    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="performance_benchmarks")
    
    # Indexes
    __table_args__ = (
        Index("idx_benchmark_site_created", "site_id", "created_at"),
        UniqueConstraint("site_id", "competitor_url", "device_type", name="uq_site_competitor_device"),
    )


class PerformanceAlert(Base):
    """Store performance alerts and thresholds."""
    __tablename__ = "performance_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    
    # Alert configuration
    metric_name = Column(String, nullable=False)  # lcp, fid, cls, etc.
    threshold_value = Column(Float, nullable=False)
    threshold_type = Column(String, nullable=False)  # "above", "below"
    severity = Column(String, nullable=False, default="warning")  # info, warning, critical
    
    # Alert state
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True))
    trigger_count = Column(Integer, default=0)
    
    # Notification settings
    notify_email = Column(Boolean, default=True)
    notify_dashboard = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="performance_alerts")
    
    # Indexes
    __table_args__ = (
        Index("idx_alert_site_active", "site_id", "is_active"),
        UniqueConstraint("site_id", "metric_name", "threshold_type", name="uq_site_metric_type"),
    )