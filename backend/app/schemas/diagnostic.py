"""
Schema definitions for the Diagnostic & Monitoring Core (Pillar 1).

This module defines Pydantic models for request and response objects
used in the diagnostic API endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, validator


class CrawlStatus(str, Enum):
    """Status of a website crawl."""
    
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CrawlRequest(BaseModel):
    """Request model for starting a website crawl."""
    
    url: AnyHttpUrl = Field(..., description="The URL to start crawling from")
    site_id: Optional[int] = Field(None, description="The site ID to associate this crawl with")
    max_urls: int = Field(1000, description="Maximum number of URLs to crawl")
    respect_robots_txt: bool = Field(True, description="Whether to respect robots.txt rules")
    crawl_javascript: bool = Field(True, description="Whether to render JavaScript during crawling")
    follow_external_links: bool = Field(False, description="Whether to follow links to external domains")
    
    @validator("max_urls")
    def validate_max_urls(cls, v):
        """Validate max_urls is within reasonable limits."""
        if v < 1:
            raise ValueError("max_urls must be at least 1")
        if v > 10000:
            raise ValueError("max_urls cannot exceed 10000 for performance reasons")
        return v


class CrawlResponse(BaseModel):
    """Response model for crawl operations."""
    
    crawl_id: str = Field(..., description="Unique identifier for the crawl")
    status: CrawlStatus = Field(..., description="Current status of the crawl")
    message: str = Field(..., description="Human-readable status message")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    urls_crawled: Optional[int] = Field(None, description="Number of URLs crawled so far")
    urls_found: Optional[int] = Field(None, description="Total number of URLs discovered")
    start_time: Optional[datetime] = Field(None, description="When the crawl started")
    end_time: Optional[datetime] = Field(None, description="When the crawl completed or failed")
    errors: Optional[List[str]] = Field(None, description="List of errors encountered during crawling")


class LogSourceType(str, Enum):
    """Type of log source."""
    
    SERVER = "SERVER"
    CDN = "CDN"
    LOAD_BALANCER = "LOAD_BALANCER"


class LogType(str, Enum):
    """Format of the log files."""
    
    APACHE = "APACHE"
    NGINX = "NGINX"
    CLOUDFLARE = "CLOUDFLARE"
    AKAMAI = "AKAMAI"
    FASTLY = "FASTLY"
    CUSTOM = "CUSTOM"


class DateRange(BaseModel):
    """Date range for log analysis."""
    
    start_date: datetime = Field(..., description="Start date for log analysis")
    end_date: datetime = Field(..., description="End date for log analysis")
    
    @validator("end_date")
    def validate_end_date(cls, v, values):
        """Validate end_date is after start_date."""
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class LogAnalysisRequest(BaseModel):
    """Request model for log file analysis."""
    
    log_source: LogSourceType = Field(..., description="Type of log source")
    log_type: LogType = Field(..., description="Format of the log files")
    date_range: DateRange = Field(..., description="Date range for log analysis")
    custom_format: Optional[str] = Field(None, description="Custom log format string (for CUSTOM log type)")


class LogAnalysisResponse(BaseModel):
    """Response model for log analysis operations."""
    
    analysis_id: str = Field(..., description="Unique identifier for the analysis")
    status: str = Field(..., description="Current status of the analysis")
    message: str = Field(..., description="Human-readable status message")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    start_time: Optional[datetime] = Field(None, description="When the analysis started")
    end_time: Optional[datetime] = Field(None, description="When the analysis completed or failed")
    results: Optional[Dict] = Field(None, description="Analysis results (when completed)")
    errors: Optional[List[str]] = Field(None, description="List of errors encountered during analysis")


class CoreWebVitalsRequest(BaseModel):
    """Request model for Core Web Vitals analysis."""
    
    url: AnyHttpUrl = Field(..., description="The URL to analyze")
    use_crux: bool = Field(True, description="Whether to use Chrome User Experience Report (CrUX) data")
    use_lighthouse: bool = Field(True, description="Whether to use Lighthouse for lab data")


class CoreWebVitalsMetric(BaseModel):
    """Model for a single Core Web Vitals metric."""
    
    name: str = Field(..., description="Metric name (e.g., LCP, FID, CLS)")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit (e.g., ms, s, score)")
    category: str = Field(..., description="Performance category (Good, Needs Improvement, Poor)")
    percentile: Optional[float] = Field(None, description="Percentile (for CrUX data)")
    improvement_suggestions: Optional[List[str]] = Field(None, description="Suggestions for improvement")


class CoreWebVitalsData(BaseModel):
    """Model for Core Web Vitals data from a specific source."""
    
    source: str = Field(..., description="Data source (CrUX, Lighthouse)")
    date: datetime = Field(..., description="Date of the data")
    metrics: List[CoreWebVitalsMetric] = Field(..., description="List of Core Web Vitals metrics")
    overall_score: Optional[float] = Field(None, description="Overall performance score (0-100)")


class CoreWebVitalsResponse(BaseModel):
    """Response model for Core Web Vitals analysis."""
    
    url: AnyHttpUrl = Field(..., description="The URL that was analyzed")
    timestamp: datetime = Field(..., description="When the analysis was performed")
    lab_data: Optional[CoreWebVitalsData] = Field(None, description="Laboratory data (Lighthouse)")
    field_data: Optional[CoreWebVitalsData] = Field(None, description="Field data (CrUX)")
    historical_trend: Optional[List[Dict]] = Field(None, description="Historical trend data")
    recommendations: Optional[List[str]] = Field(None, description="Performance improvement recommendations")


class SiteHealthIssue(BaseModel):
    """Model for a site health issue."""
    
    category: str = Field(..., description="Issue category (e.g., Performance, SEO, Accessibility)")
    severity: str = Field(..., description="Issue severity (Critical, High, Medium, Low)")
    description: str = Field(..., description="Description of the issue")
    affected_urls: Optional[List[str]] = Field(None, description="URLs affected by the issue")
    recommendation: str = Field(..., description="Recommendation to fix the issue")


class SiteHealthRecommendation(BaseModel):
    """Model for a site health recommendation."""
    
    priority: str = Field(..., description="Recommendation priority (High, Medium, Low)")
    category: str = Field(..., description="Recommendation category")
    issue: str = Field(..., description="Issue being addressed")
    recommendation: str = Field(..., description="Detailed recommendation")
    impact: str = Field(..., description="Expected impact of implementing the recommendation")


class SiteHealthResponse(BaseModel):
    """Response model for site health assessment."""
    
    site_id: int = Field(..., description="ID of the site")
    crawlability: Dict = Field(..., description="Crawlability assessment")
    performance: Dict = Field(..., description="Performance assessment")
    bot_behavior: Dict = Field(..., description="Bot behavior assessment")
    technical_issues: List[SiteHealthIssue] = Field(..., description="List of technical issues")
    health_score: int = Field(..., description="Overall health score (0-100)")
    recommendations: List[SiteHealthRecommendation] = Field(..., description="List of recommendations")
    last_updated: datetime = Field(default_factory=datetime.now, description="When the assessment was last updated")


class RecentActivitiesResponse(BaseModel):
    """Response model for recent activities."""
    
    id: str = Field(..., description="Activity ID")
    type: str = Field(..., description="Activity type (crawl, content, performance, user, system)")
    description: str = Field(..., description="Activity description")
    timestamp: str = Field(..., description="Human-readable timestamp")


class PerformanceTrendsResponse(BaseModel):
    """Response model for performance trends."""
    
    site_id: int = Field(..., description="ID of the site")
    period: str = Field(..., description="Analysis period")
    trends: Dict = Field(..., description="Performance trends data")
    last_updated: datetime = Field(default_factory=datetime.now, description="When the trends were last updated")


class SEOAnalysisRequest(BaseModel):
    """Request model for SEO analysis."""
    
    url: AnyHttpUrl = Field(..., description="The URL to analyze")


class SEOAnalysisResponse(BaseModel):
    """Response model for SEO analysis."""
    
    url: AnyHttpUrl = Field(..., description="The URL that was analyzed")
    analysis_id: str = Field(..., description="Unique identifier for the analysis")
    status: str = Field(..., description="Current status of the analysis")
    results: Optional[Dict] = Field(None, description="SEO analysis results")
    last_updated: datetime = Field(default_factory=datetime.now, description="When the analysis was last updated")