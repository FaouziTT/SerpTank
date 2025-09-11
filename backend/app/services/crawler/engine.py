"""
Crawler engine for orchestrating the web crawling process.

This module contains the main crawling logic and coordination
between different crawler components.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Any, Tuple, List

from app.schemas.diagnostic import CrawlStatus
from app.core.performance_monitoring import performance_monitor
from app.services.background_task_service import background_task_service

from .url_utils import normalize_url, extract_domain, should_crawl_url
from .html_parser import extract_links_from_html, extract_title_from_html
from .robots_handler import RobotsHandler
from .http_client import HttpClient
from .database_ops import CrawlerDatabase

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """Engine for orchestrating web crawling operations."""
    
    def __init__(
        self,
        user_agent: str = 'VoltexBot/1.0',
        concurrency: int = 5,
        respect_robots_txt: bool = True
    ):
        """
        Initialize the crawler engine.
        
        Args:
            user_agent: User agent string
            concurrency: Maximum concurrent requests
            respect_robots_txt: Whether to respect robots.txt
        """
        self.user_agent = user_agent
        self.concurrency = concurrency
        self.respect_robots_txt_default = respect_robots_txt
        
        # Initialize components
        self.robots_handler = RobotsHandler(user_agent)
        self.http_client = HttpClient(user_agent)
        self.db = CrawlerDatabase()
        
        # Active crawls tracking
        self.active_crawls: Dict[str, Dict[str, Any]] = {}
    
    @performance_monitor("crawler_url_crawl")
    async def _crawl_url(
        self, crawl_id: str, url: str, semaphore: asyncio.Semaphore
    ) -> Tuple[str, Set[str]]:
        """
        Crawl a single URL and extract links.
        
        Args:
            crawl_id: The ID of the crawl
            url: The URL to crawl
            semaphore: Semaphore to limit concurrency
            
        Returns:
            A tuple of (crawled_url, new_urls)
        """
        crawl_state = self.active_crawls[crawl_id]
        new_urls = set()
        normalized_url = normalize_url(url)
        
        async with semaphore:
            try:
                # Check robots.txt if required
                if crawl_state["respect_robots_txt"]:
                    domain = extract_domain(url)
                    if domain:
                        robots_parser = await self.robots_handler.check_robots_txt(domain)
                        if not self.robots_handler.can_fetch_url(robots_parser, url):
                            logger.info(f"Robots.txt disallows crawling {url}")
                            await self.db.store_crawled_url(
                                crawl_id=crawl_id,
                                url=url,
                                normalized_url=normalized_url,
                                status_code=403,
                                content_type=None,
                                title=None,
                                content_length=0,
                                error="Disallowed by robots.txt"
                            )
                            return url, new_urls
                
                # Fetch the URL
                result = await self.http_client.fetch(
                    url,
                    use_javascript=crawl_state["crawl_javascript"]
                )
                
                # If there was an error, store it and return
                if result.error:
                    await self.db.store_crawled_url(
                        crawl_id=crawl_id,
                        url=url,
                        normalized_url=normalized_url,
                        status_code=result.status_code,
                        content_type=result.content_type,
                        title=None,
                        content_length=0,
                        error=result.error
                    )
                    return url, new_urls
                
                # Only process HTML content
                if result.content_type and 'text/html' in result.content_type.lower():
                    # Extract title if not already provided (from httpx requests)
                    if not result.title:
                        result.title = extract_title_from_html(result.content)
                    
                    # Extract links
                    new_urls = extract_links_from_html(result.content, url)
                    
                    # Filter URLs based on crawl rules
                    filtered_urls = set()
                    for link_url in new_urls:
                        if should_crawl_url(
                            source_url=url,
                            target_url=link_url,
                            urls_crawled_set=crawl_state["urls_crawled_set"],
                            urls_to_crawl=crawl_state["urls_to_crawl"],
                            follow_external_links=crawl_state["follow_external_links"]
                        ):
                            filtered_urls.add(link_url)
                    
                    new_urls = filtered_urls
                
                # Store successful crawl
                await self.db.store_crawled_url(
                    crawl_id=crawl_id,
                    url=url,
                    normalized_url=normalized_url,
                    status_code=result.status_code,
                    content_type=result.content_type,
                    title=result.title,
                    content_length=len(result.content),
                    error=None
                )
                
            except Exception as e:
                logger.error(f"Unexpected error crawling {url}: {e}", exc_info=True)
                crawl_state["errors"].append(f"Error crawling {url}: {str(e)}")
                
                await self.db.store_crawled_url(
                    crawl_id=crawl_id,
                    url=url,
                    normalized_url=normalized_url,
                    status_code=500,
                    content_type=None,
                    title=None,
                    content_length=0,
                    error=f"Unexpected error: {str(e)[:500]}"
                )
        
        return url, new_urls
    
    @performance_monitor("crawler_run_crawl")
    async def run_crawl(self, crawl_id: str) -> None:
        """
        Run the crawl process with robust task management.
        
        Args:
            crawl_id: The ID of the crawl
        """
        crawl_state = self.active_crawls[crawl_id]
        
        # Update crawl status to IN_PROGRESS
        crawl_state["status"] = CrawlStatus.IN_PROGRESS
        await self.db.update_crawl_status(
            crawl_id=crawl_id,
            status=CrawlStatus.IN_PROGRESS,
            urls_crawled=0,
            urls_found=1
        )
        
        try:
            # Initialize crawl queue with normalized URLs
            urls_to_crawl = {normalize_url(url) for url in crawl_state["urls_to_crawl"]}
            urls_crawled_set = set()
            crawl_state["urls_to_crawl"] = urls_to_crawl
            crawl_state["urls_crawled_set"] = urls_crawled_set
            
            # Create a semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.concurrency)
            
            # Use a set to manage active tasks correctly
            active_tasks: Set[asyncio.Task] = set()
            
            # Process URLs until we reach the maximum or run out of URLs
            while (urls_to_crawl or active_tasks) and crawl_state["urls_crawled"] < crawl_state["max_urls"]:
                
                # Start new tasks up to concurrency limit
                while (len(active_tasks) < self.concurrency and 
                       urls_to_crawl and 
                       crawl_state["urls_crawled"] + len(active_tasks) < crawl_state["max_urls"]):
                    
                    url = urls_to_crawl.pop()
                    task = asyncio.create_task(self._crawl_url(crawl_id, url, semaphore))
                    active_tasks.add(task)
                
                # If no active tasks, break to avoid infinite loop
                if not active_tasks:
                    break
                
                # Wait for at least one task to complete
                done_tasks, pending_tasks = await asyncio.wait(
                    active_tasks, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Update active_tasks to only include pending tasks
                active_tasks = pending_tasks
                
                # Process completed tasks
                for task in done_tasks:
                    try:
                        crawled_url, new_urls = await task
                        
                        # Update crawl state
                        normalized_crawled_url = normalize_url(crawled_url)
                        urls_crawled_set.add(normalized_crawled_url)
                        crawl_state["urls_crawled"] += 1
                        
                        # Add new URLs to the queue (if we haven't reached the limit)
                        for new_url in new_urls:
                            normalized_new_url = normalize_url(new_url)
                            if (normalized_new_url not in urls_crawled_set and 
                                normalized_new_url not in urls_to_crawl and
                                len(urls_crawled_set) + len(urls_to_crawl) + len(active_tasks) < crawl_state["max_urls"]):
                                urls_to_crawl.add(normalized_new_url)
                        
                        # Update found URLs count
                        crawl_state["urls_found"] = (
                            len(urls_crawled_set) + len(urls_to_crawl) + len(active_tasks)
                        )
                        
                        # Update database status periodically
                        if crawl_state["urls_crawled"] % 10 == 0:
                            await self.db.update_crawl_status(
                                crawl_id=crawl_id,
                                status=CrawlStatus.IN_PROGRESS,
                                urls_crawled=crawl_state["urls_crawled"],
                                urls_found=crawl_state["urls_found"]
                            )
                            
                            # Update background task progress
                            if "task_id" in crawl_state:
                                progress = min(100, int((crawl_state["urls_crawled"] / crawl_state["max_urls"]) * 100))
                                await background_task_service.update_progress(
                                    crawl_state["task_id"],
                                    progress,
                                    f"Crawled {crawl_state['urls_crawled']} of {crawl_state['max_urls']} URLs"
                                )
                            
                    except Exception as task_error:
                        logger.error(f"Error processing completed task: {task_error}", exc_info=True)
                        crawl_state["errors"].append(f"Task processing error: {str(task_error)}")
            
            # Wait for any remaining tasks to complete
            if active_tasks:
                remaining_done, _ = await asyncio.wait(active_tasks)
                
                for task in remaining_done:
                    try:
                        crawled_url, new_urls = await task
                        normalized_crawled_url = normalize_url(crawled_url)
                        urls_crawled_set.add(normalized_crawled_url)
                        crawl_state["urls_crawled"] += 1
                    except Exception as task_error:
                        logger.error(f"Error processing final task: {task_error}", exc_info=True)
            
            # Update crawl status to COMPLETED
            crawl_state["status"] = CrawlStatus.COMPLETED
            crawl_state["end_time"] = datetime.now(timezone.utc)
            await self.db.update_crawl_status(
                crawl_id=crawl_id,
                status=CrawlStatus.COMPLETED,
                urls_crawled=crawl_state["urls_crawled"],
                urls_found=crawl_state["urls_found"],
                end_time=crawl_state["end_time"]
            )
            
            # Process and analyze the crawled data
            await self._analyze_crawl_data(crawl_id)
            
            # Complete background task
            if "task_id" in crawl_state:
                await background_task_service.complete_task(
                    crawl_state["task_id"],
                    result={
                        "crawl_id": crawl_id,
                        "urls_crawled": crawl_state["urls_crawled"],
                        "urls_found": crawl_state["urls_found"],
                        "duration": (crawl_state["end_time"] - crawl_state["start_time"]).total_seconds(),
                        "errors": crawl_state["errors"][:10]  # First 10 errors
                    },
                    resource_id=crawl_id,
                    resource_type="crawl"
                )
            
        except Exception as e:
            logger.error(f"Critical error during crawl {crawl_id}: {str(e)}", exc_info=True)
            crawl_state["status"] = CrawlStatus.FAILED
            crawl_state["errors"].append(f"Critical crawl error: {str(e)}")
            crawl_state["end_time"] = datetime.now(timezone.utc)
            await self.db.update_crawl_status(
                crawl_id=crawl_id,
                status=CrawlStatus.FAILED,
                urls_crawled=crawl_state["urls_crawled"],
                urls_found=crawl_state["urls_found"],
                end_time=crawl_state["end_time"]
            )
            
            # Fail background task
            if "task_id" in crawl_state:
                await background_task_service.fail_task(
                    crawl_state["task_id"],
                    f"Crawl failed: {str(e)}"
                )
        
        finally:
            # Clean up resources
            logger.info(f"Crawl {crawl_id} completed. URLs crawled: {crawl_state['urls_crawled']}")
    
    async def _analyze_crawl_data(self, crawl_id: str) -> None:
        """
        Analyze the crawled data and generate insights.
        
        Args:
            crawl_id: The ID of the crawl
        """
        try:
            # Get all crawled URLs for analysis
            crawled_urls = await self.db.get_crawled_urls(crawl_id)
            
            if not crawled_urls:
                logger.warning(f"No crawled URLs found for crawl {crawl_id}")
                return
            
            # Calculate metrics from crawled data
            indexable_count = 0
            non_indexable_count = 0
            status_codes = {}
            content_types = {}
            issues = []
            
            for url in crawled_urls:
                # Count status codes
                code_group = url.status_code // 100
                status_codes[f"{code_group}xx"] = status_codes.get(f"{code_group}xx", 0) + 1
                
                # Count content types
                if url.content_type:
                    content_type = url.content_type.split(';')[0].strip()
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                
                # Determine indexability
                if self._is_url_indexable(url):
                    indexable_count += 1
                else:
                    non_indexable_count += 1
            
            # Generate technical issues
            issues = self._analyze_technical_issues(crawled_urls)
            
            # Calculate crawlability score based on success rate and indexability
            total_urls = len(crawled_urls)
            success_rate = len([u for u in crawled_urls if 200 <= u.status_code < 300]) / total_urls if total_urls > 0 else 0
            indexability_rate = indexable_count / max(indexable_count + non_indexable_count, 1)
            crawlability_score = int((success_rate * 0.6 + indexability_rate * 0.4) * 100)
            
            # Create crawl analysis record
            await self._create_crawl_analysis(
                crawl_id=crawl_id,
                crawlability_score=crawlability_score,
                indexable_pages=indexable_count,
                non_indexable_pages=non_indexable_count,
                status_code_distribution=status_codes,
                content_type_distribution=content_types,
                issues=issues
            )
            
            logger.info(f"Analysis completed for crawl {crawl_id}: {total_urls} URLs, score {crawlability_score}")
            
        except Exception as e:
            logger.error(f"Error analyzing crawl data for {crawl_id}: {e}", exc_info=True)
    
    def _is_url_indexable(self, crawled_url) -> bool:
        """
        Determine if a URL is indexable based on various factors.
        
        Args:
            crawled_url: CrawlUrl object
            
        Returns:
            Boolean indicating if the URL is indexable
        """
        # Basic success check
        if not (200 <= crawled_url.status_code < 300):
            return False
        
        # Content type check
        if crawled_url.content_type and 'text/html' not in crawled_url.content_type.lower():
            return False
        
        # URL pattern checks for non-indexable content
        non_indexable_patterns = [
            '/admin/', '/wp-admin/', '/login', '/register', '/checkout',
            '/cart', '/search', '/404', '/error', '/api/', '/_next/',
            '/static/', '/assets/', '.pdf', '.doc', '.zip', '.exe',
            '/thank-you', '/confirmation', '/success'
        ]
        
        url_lower = crawled_url.url.lower()
        for pattern in non_indexable_patterns:
            if pattern in url_lower:
                return False
        
        return True
    
    def _analyze_technical_issues(self, crawled_urls) -> List[Dict]:
        """
        Analyze crawled URLs for technical SEO issues.
        
        Args:
            crawled_urls: List of CrawlUrl objects
            
        Returns:
            List of identified technical issues
        """
        issues = []
        
        # 404 and error pages
        error_urls = [url for url in crawled_urls if url.status_code >= 400]
        if error_urls:
            issues.append({
                "type": "http_errors",
                "severity": "High" if len(error_urls) > 10 else "Medium",
                "count": len(error_urls),
                "description": f"Found {len(error_urls)} URLs returning HTTP error codes",
                "examples": [url.url for url in error_urls[:5]]
            })
        
        # Missing titles
        no_title_urls = [url for url in crawled_urls if not url.title and 200 <= url.status_code < 300]
        if no_title_urls:
            issues.append({
                "type": "missing_titles",
                "severity": "High",
                "count": len(no_title_urls),
                "description": f"Found {len(no_title_urls)} pages without title tags",
                "examples": [url.url for url in no_title_urls[:5]]
            })
        
        # Redirects
        redirect_urls = [url for url in crawled_urls if 300 <= url.status_code < 400]
        if len(redirect_urls) > len(crawled_urls) * 0.1:  # More than 10%
            issues.append({
                "type": "excessive_redirects",
                "severity": "Medium",
                "count": len(redirect_urls),
                "description": f"High percentage of redirects ({len(redirect_urls)} out of {len(crawled_urls)} URLs)",
                "examples": [url.url for url in redirect_urls[:5]]
            })
        
        # Large pages
        large_pages = [url for url in crawled_urls if url.content_length and url.content_length > 1000000]
        if large_pages:
            issues.append({
                "type": "large_pages",
                "severity": "Medium",
                "count": len(large_pages),
                "description": f"Found {len(large_pages)} pages larger than 1MB",
                "examples": [url.url for url in large_pages[:3]]
            })
        
        return issues
    
    async def _create_crawl_analysis(
        self, 
        crawl_id: str,
        crawlability_score: int,
        indexable_pages: int,
        non_indexable_pages: int,
        status_code_distribution: Dict,
        content_type_distribution: Dict,
        issues: List[Dict]
    ) -> None:
        """
        Create a crawl analysis record in the database.
        
        Args:
            crawl_id: The crawl ID
            crawlability_score: Overall crawlability score
            indexable_pages: Number of indexable pages
            non_indexable_pages: Number of non-indexable pages
            status_code_distribution: Distribution of HTTP status codes
            content_type_distribution: Distribution of content types
            issues: List of technical issues found
        """
        try:
            from app.db.session import async_session_factory
            from app.models.crawl import CrawlAnalysis
            from datetime import datetime, timezone
            
            async with async_session_factory() as db:
                analysis = CrawlAnalysis(
                    crawl_id=crawl_id,
                    analysis_time=datetime.now(timezone.utc),
                    crawlability_score=crawlability_score,
                    indexable_pages=indexable_pages,
                    non_indexable_pages=non_indexable_pages,
                    status_code_distribution=status_code_distribution,
                    content_type_distribution=content_type_distribution,
                    issues=issues,
                    recommendations=self._generate_recommendations(issues)
                )
                
                db.add(analysis)
                await db.commit()
                
                logger.info(f"Created crawl analysis for {crawl_id}")
                
        except Exception as e:
            logger.error(f"Failed to create crawl analysis: {e}", exc_info=True)
    
    def _generate_recommendations(self, issues: List[Dict]) -> List[Dict]:
        """
        Generate recommendations based on identified issues.
        
        Args:
            issues: List of technical issues
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "http_errors":
                recommendations.append({
                    "priority": "High",
                    "action": "Fix broken links and server errors",
                    "description": "Review and fix all URLs returning 4xx or 5xx status codes",
                    "impact": "Improves crawlability and user experience"
                })
            elif issue["type"] == "missing_titles":
                recommendations.append({
                    "priority": "High", 
                    "action": "Add title tags to all pages",
                    "description": "Ensure every page has a unique, descriptive title tag",
                    "impact": "Essential for SEO and search result appearance"
                })
            elif issue["type"] == "excessive_redirects":
                recommendations.append({
                    "priority": "Medium",
                    "action": "Optimize redirect chains",
                    "description": "Review redirect patterns and update internal links",
                    "impact": "Reduces crawl budget waste and improves site speed"
                })
            elif issue["type"] == "large_pages":
                recommendations.append({
                    "priority": "Medium",
                    "action": "Optimize page sizes",
                    "description": "Compress images and optimize content for faster loading",
                    "impact": "Improves Core Web Vitals and user experience"
                })
        
        return recommendations