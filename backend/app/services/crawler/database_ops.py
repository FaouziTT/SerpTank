"""
Database operations for the crawler service.

This module handles all database interactions for the crawler,
including storing crawled URLs and updating crawl status.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.crawl import Crawl, CrawlUrl
from app.schemas.diagnostic import CrawlStatus

if TYPE_CHECKING:
    from app.models.crawl import CrawlAnalysis

logger = logging.getLogger(__name__)


class CrawlerDatabase:
    """Database operations for the crawler service."""
    
    async def create_crawl(
        self,
        crawl_id: str,
        user_id: int,
        start_url: str,
        max_urls: int,
        respect_robots_txt: bool,
        crawl_javascript: bool,
        follow_external_links: bool
    ) -> None:
        """
        Create a new crawl record in the database.
        
        Args:
            crawl_id: The ID of the crawl
            user_id: ID of the user who initiated the crawl
            start_url: The starting URL
            max_urls: Maximum number of URLs to crawl
            respect_robots_txt: Whether to respect robots.txt
            crawl_javascript: Whether to render JavaScript
            follow_external_links: Whether to follow external links
        """
        try:
            async with async_session_factory() as db:
                crawl = Crawl(
                    id=crawl_id,
                    user_id=user_id,
                    start_url=start_url,
                    max_urls=max_urls,
                    respect_robots_txt=respect_robots_txt,
                    crawl_javascript=crawl_javascript,
                    follow_external_links=follow_external_links,
                    status=CrawlStatus.STARTED,
                    start_time=datetime.now(timezone.utc),
                )
                db.add(crawl)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to create crawl record: {e}", exc_info=True)
            raise ValueError(f"Failed to initialize crawl: {str(e)}")
    
    async def store_crawled_url(
        self,
        crawl_id: str,
        url: str,
        normalized_url: str,
        status_code: int,
        content_type: Optional[str],
        title: Optional[str],
        content_length: int,
        error: Optional[str] = None,
    ) -> None:
        """
        Store a crawled URL in the database.
        
        Args:
            crawl_id: The ID of the crawl
            url: The URL that was crawled
            normalized_url: The normalized version of the URL
            status_code: The HTTP status code
            content_type: The content type of the response
            title: The page title
            content_length: The content length in bytes
            error: Error message if the crawl failed
        """
        try:
            async with async_session_factory() as db:
                crawl_url = CrawlUrl(
                    crawl_id=crawl_id,
                    url=url,
                    normalized_url=normalized_url,
                    status_code=status_code,
                    content_type=content_type,
                    title=title,
                    content_length=content_length,
                    error=error,
                    crawl_time=datetime.now(timezone.utc)
                )
                db.add(crawl_url)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to store crawled URL {url}: {e}", exc_info=True)
    
    async def update_crawl_status(
        self,
        crawl_id: str,
        status: CrawlStatus,
        urls_crawled: int,
        urls_found: int,
        end_time: Optional[datetime] = None
    ) -> None:
        """
        Update the crawl status in the database.
        
        Args:
            crawl_id: The ID of the crawl
            status: The new status
            urls_crawled: Number of URLs crawled
            urls_found: Number of URLs found
            end_time: The end time if the crawl is complete
        """
        try:
            async with async_session_factory() as db:
                crawl = await db.get(Crawl, crawl_id)
                if crawl:
                    crawl.status = status
                    crawl.urls_crawled = urls_crawled
                    crawl.urls_found = urls_found
                    
                    if end_time:
                        crawl.end_time = end_time
                    
                    await db.commit()
        except Exception as e:
            logger.error(f"Failed to update crawl status for {crawl_id}: {e}", exc_info=True)
    
    async def get_crawl(self, crawl_id: str) -> Optional[Crawl]:
        """
        Get a crawl record from the database.
        
        Args:
            crawl_id: The ID of the crawl
            
        Returns:
            The crawl record or None if not found
        """
        try:
            async with async_session_factory() as db:
                return await db.get(Crawl, crawl_id)
        except Exception as e:
            logger.error(f"Failed to get crawl {crawl_id}: {e}", exc_info=True)
            return None
    
    async def get_latest_crawl_by_site(self, site_id: int, user_id: int) -> Optional[Crawl]:
        """
        Get the latest completed crawl for a specific site.
        
        Args:
            site_id: The ID of the site
            user_id: The ID of the user (for access control)
            
        Returns:
            The latest crawl record or None if not found
        """
        try:
            from sqlalchemy import select
            from app.models.crawl import Crawl
            from app.schemas.diagnostic import CrawlStatus
            
            async with async_session_factory() as db:
                # Query for the latest completed crawl for this site
                query = (
                    select(Crawl)
                    .where(
                        Crawl.site_id == site_id,
                        Crawl.user_id == user_id,
                        Crawl.status == CrawlStatus.COMPLETED
                    )
                    .order_by(Crawl.start_time.desc())
                    .limit(1)
                )
                
                result = await db.execute(query)
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Failed to get latest crawl for site {site_id}: {e}", exc_info=True)
            return None
    
    async def get_crawl_analysis(self, crawl_id: str) -> Optional["CrawlAnalysis"]:
        """
        Get the analysis record for a crawl.
        
        Args:
            crawl_id: The ID of the crawl
            
        Returns:
            The crawl analysis record or None if not found
        """
        try:
            from sqlalchemy import select
            from app.models.crawl import CrawlAnalysis
            
            async with async_session_factory() as db:
                query = select(CrawlAnalysis).where(CrawlAnalysis.crawl_id == crawl_id)
                result = await db.execute(query)
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Failed to get crawl analysis for {crawl_id}: {e}", exc_info=True)
            return None
    
    async def get_crawled_urls(self, crawl_id: str, limit: Optional[int] = None) -> List["CrawlUrl"]:
        """
        Get all crawled URLs for a specific crawl.
        
        Args:
            crawl_id: The ID of the crawl
            limit: Optional limit on number of URLs to return
            
        Returns:
            List of crawled URL records
        """
        try:
            from sqlalchemy import select
            from app.models.crawl import CrawlUrl
            
            async with async_session_factory() as db:
                query = select(CrawlUrl).where(CrawlUrl.crawl_id == crawl_id)
                
                if limit:
                    query = query.limit(limit)
                    
                result = await db.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Failed to get crawled URLs for {crawl_id}: {e}", exc_info=True)
            return []