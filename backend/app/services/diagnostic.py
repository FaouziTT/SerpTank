"""
Diagnostic service for the Diagnostic & Monitoring Core (Pillar 1).

This module provides a comprehensive diagnostic service that integrates
with other services to provide site health analysis, performance monitoring,
and diagnostic insights.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import get_db
from app.models.activity import Activity
from app.models.crawl import Site, Crawl, CrawlAnalysis
from app.models.user import User
from app.schemas.diagnostic import (
    SiteHealthResponse,
    SiteHealthIssue,
    SiteHealthRecommendation,
    PerformanceTrendsResponse,
    SEOAnalysisResponse,
    RecentActivitiesResponse,
    CoreWebVitalsResponse
)
from app.services.core_web_vitals import CoreWebVitalsService
from app.services.seo_analysis import SEOAnalysisService
from app.services.crawler import CrawlerService
from app.services.pagespeed_insights import PageSpeedInsightsClient
from app.services.diagnostic_trends import PerformanceTrendsService

logger = logging.getLogger(__name__)


class DiagnosticService:
    """
    Comprehensive diagnostic service for website analysis and monitoring.
    
    This service integrates with other services to provide:
    - Site health assessment
    - Performance trend analysis
    - SEO analysis
    - Recent activities tracking
    - Core Web Vitals monitoring
    """
    
    def __init__(self):
        """Initialize the diagnostic service with required dependencies."""
        self.cwv_service = CoreWebVitalsService()
        self.seo_service = SEOAnalysisService()
        self.crawler_service = CrawlerService()
        self.pagespeed_client = PageSpeedInsightsClient()
        self.trends_service = PerformanceTrendsService()
        
    async def get_site_health(
        self,
        site_id: int,
        user_id: int,
        db: AsyncSession
    ) -> SiteHealthResponse:
        """
        Get comprehensive site health assessment.
        
        Args:
            site_id: The ID of the site to analyze
            user_id: ID of the user requesting the analysis
            db: Database session
            
        Returns:
            Comprehensive site health assessment
            
        Raises:
            ValueError: If site not found or user doesn't have access
        """
        try:
            # Get site information
            result = await db.execute(
                select(Site).where(Site.id == site_id, Site.user_id == user_id)
            )
            site = result.scalar_one_or_none()
            
            if not site:
                raise ValueError(f"Site with ID {site_id} not found for user {user_id}")
            
            # Get latest crawl data
            latest_crawl = await self._get_latest_crawl(site_id, db)
            
            # Get performance data
            performance_data = await self._get_performance_data(site.url, db)
            
            # Get bot behavior data
            bot_behavior = await self._get_bot_behavior_data(site_id, db)
            
            # Analyze technical issues
            technical_issues = await self._analyze_technical_issues(
                site.url, latest_crawl, performance_data
            )
            
            # Calculate health score
            health_score = self._calculate_health_score(
                latest_crawl, performance_data, bot_behavior, technical_issues
            )
            
            # Generate recommendations
            recommendations = self._generate_health_recommendations(
                health_score, performance_data, technical_issues
            )
            
            return SiteHealthResponse(
                site_id=site_id,
                crawlability=self._format_crawlability_data(latest_crawl),
                performance=self._format_performance_data(performance_data),
                bot_behavior=bot_behavior,
                technical_issues=technical_issues,
                health_score=health_score,
                recommendations=recommendations,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting site health for site {site_id}: {e}")
            raise ValueError(f"Failed to get site health: {e}")
    
    async def get_performance_trends(
        self,
        site_id: Optional[int],
        period: str,
        user_id: int,
        db: AsyncSession
    ) -> PerformanceTrendsResponse:
        """
        Get performance trends for a site.
        
        Args:
            site_id: The ID of the site (optional, will use user's primary site if not provided)
            period: Time period for analysis (7d, 30d, 90d)
            user_id: ID of the user requesting the data
            db: Database session
            
        Returns:
            Performance trends data
            
        Raises:
            ValueError: If site not found or invalid period
        """
        try:
            # Determine site to analyze
            if site_id is None:
                # Get user's primary site
                result = await db.execute(
                    select(Site).where(Site.user_id == user_id).order_by(Site.created_at)
                )
                site = result.scalar_one_or_none()
                if not site:
                    raise ValueError(f"No sites found for user {user_id}")
                site_id = site.id
            else:
                # Verify user has access to the site
                result = await db.execute(
                    select(Site).where(Site.id == site_id, Site.user_id == user_id)
                )
                site = result.scalar_one_or_none()
                if not site:
                    raise ValueError(f"Site with ID {site_id} not found for user {user_id}")
            
            # Calculate date range
            end_date = datetime.now()
            if period == "7d":
                start_date = end_date - timedelta(days=7)
            elif period == "30d":
                start_date = end_date - timedelta(days=30)
            elif period == "90d":
                start_date = end_date - timedelta(days=90)
            else:
                raise ValueError("Invalid period. Must be one of: 7d, 30d, 90d")
            
            # Get crawl trends
            crawl_trends = await self._get_crawl_trends(site_id, start_date, end_date, db)
            
            # Get performance trends
            performance_trends = await self._get_performance_trends_data(
                site.url, start_date, end_date
            )
            
            # Get Core Web Vitals trends
            cwv_trends = await self._get_cwv_trends(site_id, start_date, end_date, db)
            
            trends_data = {
                "crawl_trends": crawl_trends,
                "performance_trends": performance_trends,
                "core_web_vitals_trends": cwv_trends,
                "period": period,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
            
            return PerformanceTrendsResponse(
                site_id=site_id,
                period=period,
                trends=trends_data,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting performance trends: {e}")
            raise ValueError(f"Failed to get performance trends: {e}")
    
    async def analyze_website_seo(
        self,
        url: str,
        user_id: int,
        db: AsyncSession
    ) -> SEOAnalysisResponse:
        """
        Analyze SEO for a website.
        
        Args:
            url: The URL to analyze
            user_id: ID of the user requesting the analysis
            db: Database session
            
        Returns:
            SEO analysis results
            
        Raises:
            ValueError: If analysis fails
        """
        try:
            # Generate analysis ID
            analysis_id = f"seo_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
            
            # Perform SEO analysis
            seo_results = await self.seo_service.analyze_page(url)
            
            # Get Core Web Vitals data
            cwv_data = await self.cwv_service.analyze_core_web_vitals(
                url=url,
                use_crux=True,
                use_lighthouse=True,
                user_id=user_id
            )
            
            # Get PageSpeed Insights data
            pagespeed_data = await self.pagespeed_client.analyze_url(url)
            
            # Combine results
            combined_results = {
                "seo_analysis": seo_results,
                "core_web_vitals": cwv_data.dict() if cwv_data else None,
                "pagespeed_insights": pagespeed_data,
                "analysis_summary": self._generate_seo_summary(seo_results, cwv_data, pagespeed_data)
            }
            
            # Log activity
            await self._log_activity(
                db=db,
                user_id=user_id,
                activity_type="seo_analysis",
                title=f"SEO Analysis: {urlparse(url).netloc}",
                description=f"Performed comprehensive SEO analysis for {url}",
                metadata={
                    "url": url,
                    "analysis_id": analysis_id,
                    "seo_score": seo_results.get("seo_score", 0),
                    "performance_score": pagespeed_data.get("performance_score", 0) if pagespeed_data else 0
                }
            )
            
            return SEOAnalysisResponse(
                url=url,
                analysis_id=analysis_id,
                status="completed",
                results=combined_results,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing website SEO for {url}: {e}")
            raise ValueError(f"Failed to analyze website SEO: {e}")
    
    async def get_recent_activities(
        self,
        user_id: int,
        limit: int,
        db: AsyncSession
    ) -> List[RecentActivitiesResponse]:
        """
        Get recent activities for a user using the modern ActivityFeed system.

        Args:
            user_id: ID of the user
            limit: Maximum number of activities to return
            db: Database session

        Returns:
            List of recent activities

        Raises:
            ValueError: If query fails
        """
        try:
            from app.services.activity_service import activity_service
            from app.models.activity_feed import ActivityType

            # Use the existing ActivityFeed system for relevant diagnostic activities
            activities = await activity_service.get_activity_feed(
                user_id=user_id,
                activity_types=[
                    ActivityType.SITE_CRAWLED,
                    ActivityType.PERFORMANCE_ANALYZED,
                    ActivityType.SERP_ANALYZED,
                    ActivityType.PERFORMANCE_ALERT,
                    ActivityType.PERFORMANCE_IMPROVED,
                    ActivityType.PERFORMANCE_DEGRADED
                ],
                limit=limit,
                include_system=True
            )

            # If no activities exist, return static defaults for demo
            if not activities:
                return self._get_static_default_activities(user_id, limit)

            return [
                RecentActivitiesResponse(
                    id=str(activity.id),
                    type=activity.type.value,  # Convert enum to string
                    description=activity.description or activity.title,
                    timestamp=activity.created_at
                )
                for activity in activities
            ]

        except Exception as e:
            logger.error(f"Error getting recent activities for user {user_id}: {e}")
            raise ValueError(f"Failed to get recent activities: {e}")
    
    async def _create_default_activities(self, user_id: int, db: AsyncSession) -> None:
        """Create default activities for demo purposes."""
        default_activities = [
            Activity(
                user_id=user_id,
                activity_type="system",
                title="Welcome to Voltex DSE",
                description="Your SEO Command Center is now active and monitoring your digital assets",
                status="completed"
            ),
            Activity(
                user_id=user_id,
                activity_type="crawl",
                title="Site Analysis Initiated",
                description="Comprehensive crawl analysis started for your primary domain",
                status="completed"
            ),
            Activity(
                user_id=user_id,
                activity_type="performance",
                title="Core Web Vitals Baseline",
                description="Initial performance metrics captured for optimization tracking",
                status="completed"
            ),
            Activity(
                user_id=user_id,
                activity_type="content",
                title="Content Opportunities Identified",
                description="47 high-potential keywords discovered for content expansion",
                status="completed"
            ),
            Activity(
                user_id=user_id,
                activity_type="user",
                title="Project Configuration Complete",
                description="Team settings and project parameters successfully configured",
                status="completed"
            )
        ]
        
        for activity in default_activities:
            db.add(activity)
        
        await db.commit()
    
    def _get_static_default_activities(self, user_id: int, limit: int) -> List[RecentActivitiesResponse]:
        """Return static default activities when database insertion fails."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        default_activities_data = [
            {
                "id": "default-1",
                "type": "system",
                "description": "Welcome to Voltex DSE - Your SEO Command Center is now active",
                "timestamp": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "default-2",
                "type": "site_crawled",
                "description": "Site Analysis Initiated - Comprehensive crawl analysis available",
                "timestamp": (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "default-3",
                "type": "performance_analyzed",
                "description": "Core Web Vitals Baseline - Initial performance metrics captured",
                "timestamp": (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "default-4",
                "type": "content",
                "description": "Content Opportunities - High-potential keywords discovered",
                "timestamp": (now - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "default-5",
                "type": "user",
                "description": "Project Configuration - Team settings successfully configured",
                "timestamp": (now - timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        # Return only the requested number of activities
        return [
            RecentActivitiesResponse(
                id=activity["id"],
                type=activity["type"],
                description=activity["description"],
                timestamp=activity["timestamp"]
            )
            for activity in default_activities_data[:limit]
        ]
    
    async def _get_latest_crawl(self, site_id: int, db: AsyncSession) -> Optional[Dict]:
        """Get the latest crawl data for a site."""
        try:
            result = await db.execute(
                select(Crawl)
                .where(Crawl.site_id == site_id)
                .order_by(desc(Crawl.start_time))
                .limit(1)
                .options(selectinload(Crawl.crawl_analysis))
            )
            
            crawl = result.scalar_one_or_none()
            if not crawl:
                return None
            
            return {
                "crawl_id": crawl.id,
                "status": crawl.status.value,
                "start_time": crawl.start_time,
                "end_time": crawl.end_time,
                "urls_crawled": crawl.urls_crawled,
                "urls_found": crawl.urls_found,
                "analysis": {
                    "crawlability_score": crawl.crawl_analysis.crawlability_score,
                    "indexable_pages": crawl.crawl_analysis.indexable_pages,
                    "non_indexable_pages": crawl.crawl_analysis.non_indexable_pages,
                    "crawl_depth_distribution": crawl.crawl_analysis.crawl_depth_distribution,
                    "content_type_distribution": crawl.crawl_analysis.content_type_distribution,
                    "status_code_distribution": crawl.crawl_analysis.status_code_distribution,
                    "issues": crawl.crawl_analysis.issues,
                    "recommendations": crawl.crawl_analysis.recommendations,
                    "analysis_time": crawl.crawl_analysis.analysis_time.isoformat() if crawl.crawl_analysis.analysis_time else None
                } if crawl.crawl_analysis else None
            }
            
        except Exception as e:
            logger.error(f"Error getting latest crawl for site {site_id}: {e}")
            return None
    
    async def _get_performance_data(self, url: str, db: AsyncSession) -> Dict:
        """Get performance data for a URL with device-specific metrics."""
        try:
            # Get Core Web Vitals data for all devices
            all_devices_cwv = await self.cwv_service.get_crux_data_all_devices(url)
            
            # Get PageSpeed Insights data for mobile and desktop
            mobile_pagespeed = await self.pagespeed_client.analyze_url(url, strategy='mobile')
            desktop_pagespeed = await self.pagespeed_client.analyze_url(url, strategy='desktop')
            
            # Get single CWV for backward compatibility
            cwv_data = await self.cwv_service.analyze_core_web_vitals(url=url)
            
            return {
                "core_web_vitals": cwv_data.dict() if cwv_data else {},
                "all_devices_cwv": all_devices_cwv,
                "mobile_pagespeed": mobile_pagespeed,
                "desktop_pagespeed": desktop_pagespeed,
                "pagespeed_insights": mobile_pagespeed,  # Default to mobile for backward compatibility
                "performance_score": self._calculate_performance_score(cwv_data, mobile_pagespeed)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance data for {url}: {e}")
            return {"error": str(e)}
    
    async def _get_bot_behavior_data(self, site_id: int, db: AsyncSession) -> Dict:
        """Get bot behavior analysis data."""
        try:
            # Get recent crawls to analyze bot behavior
            result = await db.execute(
                select(Crawl)
                .where(Crawl.site_id == site_id)
                .order_by(desc(Crawl.start_time))
                .limit(10)
            )
            
            crawls = result.scalars().all()
            
            if not crawls:
                return {"status": "no_data", "message": "No crawl data available"}
            
            # Analyze bot behavior patterns
            total_crawls = len(crawls)
            successful_crawls = sum(1 for crawl in crawls if crawl.status.value == "COMPLETED")
            failed_crawls = sum(1 for crawl in crawls if crawl.status.value == "FAILED")
            
            avg_urls_per_crawl = sum(crawl.urls_crawled for crawl in crawls) / total_crawls if total_crawls > 0 else 0
            avg_crawl_duration = sum(
                (crawl.end_time - crawl.start_time).total_seconds() 
                for crawl in crawls 
                if crawl.end_time and crawl.start_time
            ) / total_crawls if total_crawls > 0 else 0
            
            return {
                "total_crawls": total_crawls,
                "successful_crawls": successful_crawls,
                "failed_crawls": failed_crawls,
                "success_rate": (successful_crawls / total_crawls * 100) if total_crawls > 0 else 0,
                "avg_urls_per_crawl": round(avg_urls_per_crawl, 2),
                "avg_crawl_duration_seconds": round(avg_crawl_duration, 2),
                "last_crawl": crawls[0].start_time.isoformat() if crawls else None,
                "status": "healthy" if successful_crawls / total_crawls > 0.8 else "needs_attention"
            }
            
        except Exception as e:
            logger.error(f"Error getting bot behavior data for site {site_id}: {e}")
            return {"error": str(e)}
    
    async def _analyze_technical_issues(
        self,
        url: str,
        latest_crawl: Optional[Dict],
        performance_data: Dict
    ) -> List[SiteHealthIssue]:
        """Analyze technical issues based on crawl and performance data."""
        issues = []
        
        try:
            # Analyze crawl issues
            if latest_crawl:
                if latest_crawl["status"] == "FAILED":
                    issues.append(SiteHealthIssue(
                        category="Crawlability",
                        severity="Critical",
                        description="Latest crawl failed",
                        affected_urls=[url],
                        recommendation="Check website accessibility and server configuration"
                    ))
                
                if latest_crawl.get("urls_crawled", 0) == 0:
                    issues.append(SiteHealthIssue(
                        category="Crawlability",
                        severity="High",
                        description="No URLs were crawled successfully",
                        affected_urls=[url],
                        recommendation="Verify robots.txt configuration and site accessibility"
                    ))
            
            # Analyze performance issues
            if "core_web_vitals" in performance_data:
                cwv = performance_data["core_web_vitals"]
                if "lab_data" in cwv and cwv["lab_data"]:
                    lab_data = cwv["lab_data"]
                    
                    # Extract metrics from CoreWebVitalsData object
                    lcp_value = 0
                    cls_value = 0
                    
                    if hasattr(lab_data, 'metrics'):
                        for metric in lab_data.metrics:
                            if metric.name.upper() == "LCP":
                                lcp_value = metric.value / 1000 if metric.unit == "ms" else metric.value
                            elif metric.name.upper() == "CLS":
                                cls_value = metric.value
                    
                    if lcp_value > 2.5:
                        issues.append(SiteHealthIssue(
                            category="Performance",
                            severity="High",
                            description="Largest Contentful Paint (LCP) is too slow",
                            affected_urls=[url],
                            recommendation="Optimize image loading, implement lazy loading, and improve server response times"
                        ))
                    
                    if cls_value > 0.1:
                        issues.append(SiteHealthIssue(
                            category="Performance",
                            severity="Medium",
                            description="Cumulative Layout Shift (CLS) is too high",
                            affected_urls=[url],
                            recommendation="Fix layout shifts by setting explicit dimensions for images and other elements"
                        ))
            
            # Analyze PageSpeed Insights issues
            if "pagespeed_insights" in performance_data:
                psi_data = performance_data["pagespeed_insights"]
                if "opportunities" in psi_data:
                    for opportunity in psi_data["opportunities"][:5]:  # Top 5 opportunities
                        issues.append(SiteHealthIssue(
                            category="Performance",
                            severity="Medium",
                            description=opportunity.get("title", "Performance optimization opportunity"),
                            affected_urls=[url],
                            recommendation=opportunity.get("description", "Review and implement suggested optimizations")
                        ))
            
        except Exception as e:
            logger.error(f"Error analyzing technical issues: {e}")
            issues.append(SiteHealthIssue(
                category="System",
                severity="Medium",
                description="Error analyzing technical issues",
                affected_urls=[url],
                recommendation="Check system logs and try again"
            ))
        
        return issues
    
    def _calculate_health_score(
        self,
        latest_crawl: Optional[Dict],
        performance_data: Dict,
        bot_behavior: Dict,
        technical_issues: List[SiteHealthIssue]
    ) -> int:
        """Calculate overall site health score (0-100)."""
        score = 100
        
        # Deduct points for crawl issues
        if latest_crawl:
            if latest_crawl["status"] == "FAILED":
                score -= 30
            elif latest_crawl.get("urls_crawled", 0) == 0:
                score -= 20
            elif latest_crawl.get("urls_crawled", 0) < 10:
                score -= 10
        
        # Deduct points for performance issues
        if "performance_score" in performance_data:
            performance_score = performance_data["performance_score"]
            score -= (100 - performance_score) * 0.3  # Performance is 30% of total score
        
        # Deduct points for bot behavior issues
        if "success_rate" in bot_behavior:
            success_rate = bot_behavior["success_rate"]
            if success_rate < 80:
                score -= (80 - success_rate) * 0.5
        
        # Deduct points for technical issues
        critical_issues = sum(1 for issue in technical_issues if issue.severity == "Critical")
        high_issues = sum(1 for issue in technical_issues if issue.severity == "High")
        medium_issues = sum(1 for issue in technical_issues if issue.severity == "Medium")
        
        score -= critical_issues * 15
        score -= high_issues * 10
        score -= medium_issues * 5
        
        return max(0, min(100, int(score)))
    
    def _generate_health_recommendations(
        self,
        health_score: int,
        performance_data: Dict,
        technical_issues: List[SiteHealthIssue]
    ) -> List[SiteHealthRecommendation]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        # Add recommendations based on health score
        if health_score < 50:
            recommendations.append(SiteHealthRecommendation(
                priority="High",
                category="Overall Health",
                issue="Low overall site health score",
                recommendation="Address critical and high-priority issues immediately to improve site health",
                impact="Significant improvement in site performance and crawlability"
            ))
        elif health_score < 80:
            recommendations.append(SiteHealthRecommendation(
                priority="Medium",
                category="Overall Health",
                issue="Moderate site health score",
                recommendation="Focus on performance optimizations and technical improvements",
                impact="Improved user experience and search engine rankings"
            ))
        
        # Add recommendations based on technical issues
        for issue in technical_issues[:5]:  # Top 5 issues
            recommendations.append(SiteHealthRecommendation(
                priority="High" if issue.severity in ["Critical", "High"] else "Medium",
                category=issue.category,
                issue=issue.description,
                recommendation=issue.recommendation,
                impact="Improved site performance and user experience"
            ))
        
        # Add performance-specific recommendations
        if "performance_score" in performance_data:
            perf_score = performance_data["performance_score"]
            if perf_score < 70:
                recommendations.append(SiteHealthRecommendation(
                    priority="High",
                    category="Performance",
                    issue="Low performance score",
                    recommendation="Implement Core Web Vitals optimizations and reduce page load times",
                    impact="Better user experience and improved search rankings"
                ))
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _format_crawlability_data(self, latest_crawl: Optional[Dict]) -> Dict:
        """Format crawlability data for response."""
        if not latest_crawl:
            return {
                "status": "no_data",
                "message": "No crawl data available",
                "last_crawl": None,
                "crawlability_score": 0,
                "indexable_pages": 0,
                "non_indexable_pages": 0,
                "crawl_depth_distribution": {},
                "content_type_distribution": {},
                "status_code_distribution": {},
                "total_pages": 0
            }
        
        # Check if we have rich analysis data
        analysis = latest_crawl.get("analysis")
        if analysis:
            # Use the rich analysis data from CrawlAnalysis
            return {
                "status": latest_crawl["status"],
                "last_crawl": latest_crawl["start_time"].isoformat() if latest_crawl["start_time"] else None,
                "urls_crawled": latest_crawl.get("urls_crawled", 0),
                "urls_found": latest_crawl.get("urls_found", 0),
                "crawlability_score": analysis.get("crawlability_score", 0),
                "indexable_pages": analysis.get("indexable_pages", 0),
                "non_indexable_pages": analysis.get("non_indexable_pages", 0),
                "crawl_depth_distribution": analysis.get("crawl_depth_distribution", {}),
                "content_type_distribution": analysis.get("content_type_distribution", {}),
                "status_code_distribution": analysis.get("status_code_distribution", {}),
                "total_pages": analysis.get("indexable_pages", 0) + analysis.get("non_indexable_pages", 0),
                "issues": analysis.get("issues", []),
                "recommendations": analysis.get("recommendations", []),
                "analysis_time": analysis.get("analysis_time")
            }
        else:
            # Fallback to basic crawl data for crawls without analysis
            score = 100
            if latest_crawl["status"] == "FAILED":
                score = 0
            elif latest_crawl.get("urls_crawled", 0) == 0:
                score = 20
            elif latest_crawl.get("urls_crawled", 0) < 10:
                score = 60
            
            return {
                "status": latest_crawl["status"],
                "last_crawl": latest_crawl["start_time"].isoformat() if latest_crawl["start_time"] else None,
                "urls_crawled": latest_crawl.get("urls_crawled", 0),
                "urls_found": latest_crawl.get("urls_found", 0),
                "crawlability_score": score,
                "indexable_pages": 0,
                "non_indexable_pages": latest_crawl.get("urls_crawled", 0),
                "crawl_depth_distribution": {},
                "content_type_distribution": {},
                "status_code_distribution": {},
                "total_pages": latest_crawl.get("urls_crawled", 0)
            }
    
    def _format_performance_data(self, performance_data: Dict) -> Dict:
        """Format performance data for response with device-specific metrics."""
        if "error" in performance_data:
            return {
                "status": "error",
                "message": performance_data["error"],
                "performance_score": 0
            }
        
        # Extract device-specific data from all_devices_cwv
        all_devices = performance_data.get("all_devices_cwv", {})
        mobile_pagespeed = performance_data.get("mobile_pagespeed", {})
        desktop_pagespeed = performance_data.get("desktop_pagespeed", {})
        
        # Helper function to extract metrics from CrUX data
        def extract_device_metrics(device_data, pagespeed_data):
            if not device_data:
                return None
                
            metrics = {}
            
            # Extract Core Web Vitals from CrUX data
            for metric_name, metric_data in device_data.items():
                if isinstance(metric_data, dict) and "p75" in metric_data:
                    if metric_name.upper() == "LCP":
                        metrics["largest_contentful_paint"] = metric_data["p75"] / 1000  # Convert to seconds
                    elif metric_name.upper() == "FID":
                        metrics["first_input_delay"] = metric_data["p75"]
                    elif metric_name.upper() == "CLS":
                        metrics["cumulative_layout_shift"] = metric_data["p75"]
                    elif metric_name.upper() == "INP":
                        metrics["interaction_to_next_paint"] = metric_data["p75"]
                    elif metric_name.upper() == "TTFB":
                        metrics["time_to_first_byte"] = metric_data["p75"]
                    elif metric_name.upper() == "FCP":
                        metrics["first_contentful_paint"] = metric_data["p75"] / 1000
                        
            # Add PageSpeed score if available
            if pagespeed_data and "lighthouseResult" in pagespeed_data:
                lighthouse_score = pagespeed_data["lighthouseResult"].get("categories", {}).get("performance", {}).get("score", 0)
                metrics["page_speed_score"] = lighthouse_score * 100
                
                # Extract additional metrics from Lighthouse
                audits = pagespeed_data["lighthouseResult"].get("audits", {})
                if "speed-index" in audits:
                    metrics["speed_index"] = audits["speed-index"].get("numericValue", 0) / 1000
                if "total-blocking-time" in audits:
                    metrics["total_blocking_time"] = audits["total-blocking-time"].get("numericValue", 0)
                if "interactive" in audits:
                    metrics["time_to_interactive"] = audits["interactive"].get("numericValue", 0) / 1000
                    
            return metrics if metrics else None
        
        # Extract field data metrics (from CrUX)
        def extract_field_metrics(device_data):
            if not device_data:
                return None
                
            field_metrics = {}
            for metric_name, metric_data in device_data.items():
                if isinstance(metric_data, dict) and "p75" in metric_data:
                    if metric_name.upper() == "LCP":
                        field_metrics["largest_contentful_paint"] = metric_data["p75"] / 1000
                    elif metric_name.upper() == "FID":
                        field_metrics["first_input_delay"] = metric_data["p75"]
                    elif metric_name.upper() == "CLS":
                        field_metrics["cumulative_layout_shift"] = metric_data["p75"]
                    elif metric_name.upper() == "INP":
                        field_metrics["inp"] = metric_data["p75"]
                    elif metric_name.upper() == "TTFB":
                        field_metrics["ttfb"] = metric_data["p75"]
                    elif metric_name.upper() == "FCP":
                        field_metrics["first_contentful_paint"] = metric_data["p75"] / 1000
                        
            return field_metrics if field_metrics else None
        
        # Structure device-specific response
        formatted_response = {
            "status": "available",
            "performance_score": performance_data.get("performance_score", 0),
            "core_web_vitals": performance_data.get("core_web_vitals", {}),
            "pagespeed_insights": performance_data.get("pagespeed_insights", {})
        }
        
        # Add device-specific metrics that frontend expects
        if "mobile" in all_devices:
            formatted_response["mobile_metrics"] = extract_device_metrics(all_devices["mobile"], mobile_pagespeed)
            formatted_response["mobile_field_data"] = extract_field_metrics(all_devices["mobile"])
            
        if "desktop" in all_devices:
            formatted_response["desktop_metrics"] = extract_device_metrics(all_devices["desktop"], desktop_pagespeed)
            formatted_response["desktop_field_data"] = extract_field_metrics(all_devices["desktop"])
            
        if "tablet" in all_devices:
            formatted_response["tablet_metrics"] = extract_device_metrics(all_devices["tablet"], None)
            formatted_response["tablet_field_data"] = extract_field_metrics(all_devices["tablet"])
        
        return formatted_response
    
    def _calculate_performance_score(
        self,
        cwv_data: Optional[CoreWebVitalsResponse],
        pagespeed_data: Dict
    ) -> int:
        """Calculate overall performance score (0-100)."""
        score = 0
        
        # Add PageSpeed Insights score
        if pagespeed_data and "lighthouseResult" in pagespeed_data:
            lighthouse_score = pagespeed_data["lighthouseResult"].get("categories", {}).get("performance", {}).get("score", 0)
            score += lighthouse_score * 50  # 50% weight
        
        # Add Core Web Vitals score
        if cwv_data and cwv_data.lab_data:
            cwv_score = 0
            lab_data = cwv_data.lab_data
            
            # Extract metrics from CoreWebVitalsData object
            lcp_value = 0
            cls_value = 0
            
            if hasattr(lab_data, 'metrics'):
                for metric in lab_data.metrics:
                    if metric.name.upper() == "LCP":
                        lcp_value = metric.value / 1000 if metric.unit == "ms" else metric.value
                    elif metric.name.upper() == "CLS":
                        cls_value = metric.value
            
            # Score based on LCP
            if lcp_value <= 2.5:
                cwv_score += 25
            elif lcp_value <= 4.0:
                cwv_score += 15
            
            # Score based on CLS
            if cls_value <= 0.1:
                cwv_score += 25
            elif cls_value <= 0.25:
                cwv_score += 15
            
            score += cwv_score  # 50% weight
        
        return min(100, int(score))
    
    async def _get_crawl_trends(
        self,
        site_id: int,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict:
        """Get crawl trends for a site."""
        try:
            result = await db.execute(
                select(Crawl)
                .where(
                    Crawl.site_id == site_id,
                    Crawl.start_time >= start_date,
                    Crawl.start_time <= end_date
                )
                .order_by(Crawl.start_time)
            )
            
            crawls = result.scalars().all()
            
            return {
                "total_crawls": len(crawls),
                "successful_crawls": sum(1 for crawl in crawls if crawl.status.value == "COMPLETED"),
                "failed_crawls": sum(1 for crawl in crawls if crawl.status.value == "FAILED"),
                "avg_urls_per_crawl": sum(crawl.urls_crawled for crawl in crawls) / len(crawls) if crawls else 0,
                "crawl_frequency": len(crawls) / max(1, (end_date - start_date).days)
            }
            
        except Exception as e:
            logger.error(f"Error getting crawl trends: {e}")
            return {"error": str(e)}
    
    async def _get_performance_trends_data(
        self,
        url: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get performance trends data."""
        try:
            # In a real implementation, this would query historical performance data
            # For now, return current performance data
            current_data = await self._get_performance_data(url, None)
            
            return {
                "current_performance": current_data.get("performance_score", 0),
                "trend": "stable",  # Would be calculated from historical data
                "improvement_needed": current_data.get("performance_score", 0) < 80
            }
            
        except Exception as e:
            logger.error(f"Error getting performance trends data: {e}")
            return {"error": str(e)}
    
    async def _get_cwv_trends(
        self,
        site_id: int,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> List[Dict]:
        """Get Core Web Vitals trends."""
        try:
            # Get historical Core Web Vitals data
            trends_data = await self.trends_service.get_core_web_vitals_trends(
                site_id=site_id,
                start_date=start_date,
                end_date=end_date,
                db=db,
                device_type="mobile"  # Default to mobile
            )
            
            return trends_data
            
        except Exception as e:
            logger.error(f"Error getting CWV trends: {e}")
            return []
    
    def _generate_seo_summary(
        self,
        seo_results: Dict,
        cwv_data: Optional[CoreWebVitalsResponse],
        pagespeed_data: Dict
    ) -> Dict:
        """Generate SEO analysis summary."""
        summary = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        # Calculate overall score
        seo_score = seo_results.get("seo_score", 0)
        performance_score = pagespeed_data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0) * 100 if pagespeed_data else 0
        
        summary["overall_score"] = int((seo_score + performance_score) / 2)
        
        # Identify strengths and weaknesses
        if seo_score >= 80:
            summary["strengths"].append("Strong SEO fundamentals")
        elif seo_score < 60:
            summary["weaknesses"].append("SEO needs significant improvement")
        
        if performance_score >= 80:
            summary["strengths"].append("Good page performance")
        elif performance_score < 60:
            summary["weaknesses"].append("Page performance needs optimization")
        
        # Add recommendations
        if seo_score < 80:
            summary["recommendations"].append("Improve on-page SEO elements")
        if performance_score < 80:
            summary["recommendations"].append("Optimize page loading speed")
        
        return summary
    
    async def _log_activity(
        self,
        db: AsyncSession,
        user_id: int,
        activity_type: str,
        title: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Log an activity to the database."""
        try:
            activity = Activity(
                activity_type=activity_type,
                title=title,
                description=description,
                user_id=user_id,
                status="completed",
                activity_metadata=metadata or {},
                completed_at=datetime.now()
            )
            
            db.add(activity)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            # Don't raise the error as this is not critical for the main functionality 