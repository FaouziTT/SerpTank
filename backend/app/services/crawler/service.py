"""
Main crawler service providing the public interface.

This module implements the CrawlerService class that coordinates
all crawler components and provides the main API.
"""
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.schemas.diagnostic import CrawlResponse, CrawlStatus
from app.models.background_task import TaskType
from app.services.background_task_service import background_task_service

from .engine import CrawlerEngine
from .url_utils import normalize_url
from .database_ops import CrawlerDatabase

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for crawling websites and analyzing the crawled data."""
    
    def __init__(self):
        """Initialize the crawler service."""
        self.user_agent = getattr(settings, 'CRAWLER_USER_AGENT', 'VoltexBot/1.0')
        self.concurrency = getattr(settings, 'CRAWLER_CONCURRENCY', 5)
        self.respect_robots_txt = getattr(settings, 'CRAWLER_RESPECT_ROBOTS_TXT', True)
        
        # Initialize the crawler engine
        self.engine = CrawlerEngine(
            user_agent=self.user_agent,
            concurrency=self.concurrency,
            respect_robots_txt=self.respect_robots_txt
        )
        
        # Initialize database operations
        self.db = CrawlerDatabase()
    
    async def start_crawl(
        self,
        url: str,
        user_id: int,
        max_urls: int = 1000,
        respect_robots_txt: bool = True,
        crawl_javascript: bool = True,
        follow_external_links: bool = False,
        site_id: Optional[int] = None,
    ) -> str:
        """
        Start a new crawl of a website.
        
        Args:
            url: The URL to start crawling from
            user_id: ID of the user who initiated the crawl
            max_urls: Maximum number of URLs to crawl
            respect_robots_txt: Whether to respect robots.txt rules
            crawl_javascript: Whether to render JavaScript during crawling
            follow_external_links: Whether to follow links to external domains
            
        Returns:
            The ID of the new crawl
        """
        crawl_id = str(uuid.uuid4())
        normalized_start_url = normalize_url(url)
        
        # Create background task to track crawl progress
        task_id = await background_task_service.create_task(
            user_id=user_id,
            task_type=TaskType.CRAWL,
            task_name=f"Website Crawl: {url}",
            description=f"Crawling up to {max_urls} pages from {url}",
            site_id=site_id,
            parameters={
                "url": url,
                "max_urls": max_urls,
                "respect_robots_txt": respect_robots_txt,
                "crawl_javascript": crawl_javascript,
                "follow_external_links": follow_external_links
            }
        )
        
        # Create a new crawl record in the database
        await self.db.create_crawl(
            crawl_id=crawl_id,
            user_id=user_id,
            start_url=url,
            max_urls=max_urls,
            respect_robots_txt=respect_robots_txt,
            crawl_javascript=crawl_javascript,
            follow_external_links=follow_external_links
        )
        
        # Initialize crawl state
        self.engine.active_crawls[crawl_id] = {
            "user_id": user_id,
            "start_url": url,
            "max_urls": max_urls,
            "respect_robots_txt": respect_robots_txt,
            "crawl_javascript": crawl_javascript,
            "follow_external_links": follow_external_links,
            "status": CrawlStatus.STARTED,
            "start_time": datetime.now(timezone.utc),
            "urls_crawled": 0,
            "urls_found": 1,
            "urls_to_crawl": {normalized_start_url},
            "urls_crawled_set": set(),
            "errors": [],
            "task_id": task_id,  # Track the background task
        }
        
        # Mark task as started
        await background_task_service.start_task(task_id)
        
        # Start the crawl process in the background
        asyncio.create_task(self.engine.run_crawl(crawl_id))
        
        return crawl_id
    
    async def get_crawl_status(self, crawl_id: str, user_id: int) -> CrawlResponse:
        """
        Get the status of a crawl.
        
        Args:
            crawl_id: The ID of the crawl
            user_id: ID of the user requesting the status
            
        Returns:
            The current status of the crawl
        """
        # Check if the crawl is active
        if crawl_id in self.engine.active_crawls:
            crawl_state = self.engine.active_crawls[crawl_id]
            
            # Check if the user has access to this crawl
            if crawl_state["user_id"] != user_id:
                raise ValueError("User does not have access to this crawl")
            
            # Calculate progress
            progress = None
            if crawl_state["max_urls"] > 0:
                progress = min(100.0, (crawl_state["urls_crawled"] / crawl_state["max_urls"]) * 100)
            
            return CrawlResponse(
                crawl_id=crawl_id,
                status=crawl_state["status"],
                message=f"Crawl is {crawl_state['status'].lower()}",
                progress=progress,
                urls_crawled=crawl_state["urls_crawled"],
                urls_found=crawl_state["urls_found"],
                start_time=crawl_state["start_time"],
                end_time=crawl_state.get("end_time"),
                errors=crawl_state.get("errors", []),
            )
        
        # If not active, get from database
        crawl = await self.db.get_crawl(crawl_id)
        
        if not crawl:
            raise ValueError(f"Crawl {crawl_id} not found")
        
        if crawl.user_id != user_id:
            raise ValueError("User does not have access to this crawl")
        
        # Calculate progress
        progress = None
        if crawl.max_urls > 0:
            progress = min(100.0, (crawl.urls_crawled / crawl.max_urls) * 100)
        
        return CrawlResponse(
            crawl_id=crawl_id,
            status=crawl.status,
            message=f"Crawl is {crawl.status.lower()}",
            progress=progress,
            urls_crawled=crawl.urls_crawled,
            urls_found=crawl.urls_found,
            start_time=crawl.start_time,
            end_time=crawl.end_time,
            errors=[],  # Would retrieve from database in full implementation
        )
    
    async def monitor_crawl(self, crawl_id: str, user_id: int) -> None:
        """
        Monitor a crawl and perform actions when it completes.
        
        This method is called as a background task and monitors the crawl
        until it completes or fails.
        
        Args:
            crawl_id: The ID of the crawl
            user_id: ID of the user who initiated the crawl
        """
        try:
            # Wait for the crawl to complete
            while True:
                try:
                    status = await self.get_crawl_status(crawl_id, user_id)
                    
                    # If the crawl is completed or failed, break the loop
                    if status.status in (CrawlStatus.COMPLETED, CrawlStatus.FAILED):
                        break
                    
                    # Wait before checking again
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error monitoring crawl {crawl_id}: {str(e)}")
                    break
            
            # Clean up active crawl state
            if crawl_id in self.engine.active_crawls:
                del self.engine.active_crawls[crawl_id]
                
        except Exception as e:
            logger.error(f"Error in crawl monitor for {crawl_id}: {e}", exc_info=True)
    
    async def get_latest_crawl_summary(self, site_id: int, user_id: int) -> Dict:
        """
        Get a summary of the latest crawl for a site using actual database data.
        
        Args:
            site_id: The ID of the site
            user_id: ID of the user requesting the summary
            
        Returns:
            A summary of the latest crawl with real data
        """
        try:
            # Get the latest completed crawl for this site
            latest_crawl = await self.db.get_latest_crawl_by_site(site_id, user_id)
            
            if not latest_crawl:
                # Return empty state if no crawls found
                return {
                    "crawlability": {
                        "crawl_efficiency": 0,
                        "indexable_pages": 0,
                        "non_indexable_pages": 0,
                        "crawl_depth": {},
                    },
                    "technical_issues": [],
                    "last_crawl_date": None,
                    "crawl_status": "not_found"
                }
            
            # Get crawl analysis data
            crawl_analysis = await self.db.get_crawl_analysis(latest_crawl.id)
            
            # Get all crawled URLs for this crawl
            crawled_urls = await self.db.get_crawled_urls(latest_crawl.id)
            
            # Calculate real metrics from crawled data
            summary = await self._analyze_crawl_results(latest_crawl, crawl_analysis, crawled_urls)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting crawl summary for site {site_id}: {e}", exc_info=True)
            # Return placeholder data as fallback
            return {
                "crawlability": {
                    "crawl_efficiency": 0,
                    "indexable_pages": 0,
                    "non_indexable_pages": 0,
                    "crawl_depth": {},
                },
                "technical_issues": [],
                "last_crawl_date": None,
                "crawl_status": "error"
            }
    
    async def _analyze_crawl_results(self, crawl, crawl_analysis, crawled_urls) -> Dict:
        """
        Analyze crawl results and generate summary data.
        
        Args:
            crawl: The crawl record
            crawl_analysis: The crawl analysis record (may be None)
            crawled_urls: List of crawled URLs
            
        Returns:
            Dictionary with analyzed crawl data
        """
        if not crawled_urls:
            crawled_urls = []
        
        # Count successful vs failed URLs
        successful_urls = [url for url in crawled_urls if 200 <= url.status_code < 300]
        indexable_pages = len([url for url in successful_urls if self._is_indexable(url)])
        non_indexable_pages = len(successful_urls) - indexable_pages
        
        # Calculate crawl efficiency
        total_found = crawl.urls_found or len(crawled_urls)
        total_crawled = crawl.urls_crawled or len(crawled_urls)
        crawl_efficiency = int((total_crawled / max(total_found, 1)) * 100)
        
        # Analyze crawl depth distribution
        crawl_depth = self._calculate_crawl_depth_distribution(crawled_urls, crawl.start_url)
        
        # Generate technical issues from crawled data
        technical_issues = self._generate_technical_issues(crawled_urls)
        
        # Status code distribution
        status_codes = {}
        for url in crawled_urls:
            code_range = f"{url.status_code // 100}xx"
            status_codes[code_range] = status_codes.get(code_range, 0) + 1
        
        # Content type distribution
        content_types = {}
        for url in crawled_urls:
            if url.content_type:
                content_type = url.content_type.split(';')[0].strip()
                content_types[content_type] = content_types.get(content_type, 0) + 1
        
        return {
            "crawlability": {
                "crawl_efficiency": crawl_efficiency,
                "indexable_pages": indexable_pages,
                "non_indexable_pages": non_indexable_pages,
                "crawl_depth": crawl_depth,
                "total_pages": len(crawled_urls),
                "crawlability_score": crawl_analysis.crawlability_score if crawl_analysis else crawl_efficiency
            },
            "technical_issues": technical_issues,
            "last_crawl_date": crawl.start_time.isoformat() if crawl.start_time else None,
            "crawl_status": "completed",
            "status_code_distribution": status_codes,
            "content_type_distribution": content_types,
            "crawl_id": crawl.id,
            "urls_crawled": total_crawled,
            "urls_found": total_found
        }
    
    def _is_indexable(self, crawled_url) -> bool:
        """
        Determine if a crawled URL is indexable based on various factors.
        
        Args:
            crawled_url: CrawlUrl object
            
        Returns:
            Boolean indicating if the URL is likely indexable
        """
        # Basic indexability rules
        if not (200 <= crawled_url.status_code < 300):
            return False
        
        # Check content type
        if crawled_url.content_type and 'text/html' not in crawled_url.content_type.lower():
            return False
        
        # Check for noindex in title (basic check)
        if crawled_url.title and ('noindex' in crawled_url.title.lower()):
            return False
        
        # Check URL patterns that are typically non-indexable
        non_indexable_patterns = [
            '/admin/', '/wp-admin/', '/login', '/register', '/checkout',
            '/cart', '/search', '/404', '/error', '/api/', '/_next/',
            '/static/', '/assets/', '.pdf', '.doc', '.zip', '.exe'
        ]
        
        url_lower = crawled_url.url.lower()
        for pattern in non_indexable_patterns:
            if pattern in url_lower:
                return False
        
        return True
    
    def _calculate_crawl_depth_distribution(self, crawled_urls, start_url) -> Dict[str, int]:
        """
        Calculate distribution of pages by crawl depth.
        
        Args:
            crawled_urls: List of crawled URLs
            start_url: Starting URL of the crawl
            
        Returns:
            Dictionary mapping depth ranges to counts
        """
        from urllib.parse import urlparse
        
        depth_distribution = {"0-1": 0, "2-3": 0, "4-5": 0, "6+": 0}
        
        try:
            start_parsed = urlparse(start_url)
            start_path_depth = len([p for p in start_parsed.path.strip('/').split('/') if p])
            
            for crawled_url in crawled_urls:
                try:
                    parsed = urlparse(crawled_url.url)
                    path_depth = len([p for p in parsed.path.strip('/').split('/') if p])
                    
                    # Calculate relative depth from start URL
                    relative_depth = max(0, path_depth - start_path_depth)
                    
                    if relative_depth <= 1:
                        depth_distribution["0-1"] += 1
                    elif relative_depth <= 3:
                        depth_distribution["2-3"] += 1
                    elif relative_depth <= 5:
                        depth_distribution["4-5"] += 1
                    else:
                        depth_distribution["6+"] += 1
                        
                except Exception:
                    # Default to depth 0-1 if parsing fails
                    depth_distribution["0-1"] += 1
                    
        except Exception as e:
            logger.warning(f"Error calculating crawl depth: {e}")
            # Return even distribution as fallback
            total = len(crawled_urls)
            if total > 0:
                per_bucket = total // 4
                remainder = total % 4
                depth_distribution = {
                    "0-1": per_bucket + (1 if remainder > 0 else 0),
                    "2-3": per_bucket + (1 if remainder > 1 else 0),
                    "4-5": per_bucket + (1 if remainder > 2 else 0),
                    "6+": per_bucket
                }
        
        return depth_distribution
    
    def _generate_technical_issues(self, crawled_urls) -> List[Dict]:
        """
        Generate technical issues based on crawled data analysis.
        
        Args:
            crawled_urls: List of crawled URLs
            
        Returns:
            List of technical issues found
        """
        issues = []
        
        # Find URLs with errors
        error_urls = [url for url in crawled_urls if url.status_code >= 400]
        if error_urls:
            error_count = len(error_urls)
            severity = "High" if error_count > 10 else "Medium" if error_count > 5 else "Low"
            issues.append({
                "category": "Technical SEO",
                "severity": severity,
                "description": f"{error_count} pages returning HTTP error codes",
                "affected_urls": [url.url for url in error_urls[:5]],  # Show first 5
                "recommendation": "Fix broken links and server errors to improve crawlability"
            })
        
        # Find URLs without titles
        no_title_urls = [url for url in crawled_urls if not url.title and 200 <= url.status_code < 300]
        if no_title_urls:
            issues.append({
                "category": "SEO",
                "severity": "High",
                "description": f"{len(no_title_urls)} pages missing title tags",
                "affected_urls": [url.url for url in no_title_urls[:5]],
                "recommendation": "Add unique, descriptive title tags to all pages"
            })
        
        # Find redirects
        redirect_urls = [url for url in crawled_urls if 300 <= url.status_code < 400]
        if redirect_urls:
            redirect_count = len(redirect_urls)
            if redirect_count > len(crawled_urls) * 0.1:  # More than 10% redirects
                issues.append({
                    "category": "Technical SEO",
                    "severity": "Medium",
                    "description": f"High number of redirects ({redirect_count} pages)",
                    "affected_urls": [url.url for url in redirect_urls[:5]],
                    "recommendation": "Review redirect chains and update internal links"
                })
        
        # Find large pages (potential performance issue)
        large_pages = [url for url in crawled_urls if url.content_length > 1000000]  # > 1MB
        if large_pages:
            issues.append({
                "category": "Performance",
                "severity": "Medium",
                "description": f"{len(large_pages)} pages with large content size",
                "affected_urls": [url.url for url in large_pages[:5]],
                "recommendation": "Optimize page content and compress resources"
            })
        
        return issues