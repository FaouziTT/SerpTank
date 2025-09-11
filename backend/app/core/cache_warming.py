"""
Cache warming utilities for pre-populating frequently accessed data.

This module provides background tasks and scheduled jobs to warm up
the cache with commonly requested data to improve response times.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.cache import cache_manager
from app.core.structured_logging import get_logger
from app.db.session import async_session_factory
from app.models.project import Project
from app.models.serp_cache import SERPAnalysis
from app.models.crawl import Site
from app.models.performance import PerformanceMetric
from app.services.core_web_vitals import cwv_service
from app.services.serpapi import serpapi_service

logger = get_logger(__name__)


class CacheWarmer:
    """Manages cache warming operations."""
    
    def __init__(self):
        self.is_running = False
        self.last_run = None
        
    async def warm_project_cache(self, db: AsyncSession) -> int:
        """
        Warm cache for all active projects.
        
        Returns:
            Number of projects cached
        """
        try:
            # Get all active projects
            result = await db.execute(
                select(Project)
                .order_by(Project.updated_at.desc())
                .limit(100)  # Limit to most recent 100 projects
            )
            projects = result.scalars().all()
            
            cached_count = 0
            for project in projects:
                cache_key = f"project:{project.id}"
                await cache_manager.set(
                    cache_key,
                    {
                        "id": project.id,
                        "name": project.name,
                        "url": project.url,
                        "user_id": project.user_id,
                        "created_at": project.created_at.isoformat(),
                        "updated_at": project.updated_at.isoformat()
                    },
                    ttl=3600  # 1 hour TTL
                )
                cached_count += 1
                
            logger.info(f"Warmed cache for {cached_count} projects")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming project cache: {e}")
            return 0
    
    async def warm_serp_cache(self, db: AsyncSession) -> int:
        """
        Warm cache for recent SERP queries.
        
        Returns:
            Number of SERP results cached
        """
        try:
            # Get most frequently accessed SERP queries from last 7 days
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            result = await db.execute(
                select(
                    SERPAnalysis.query,
                    SERPAnalysis.location,
                    SERPAnalysis.device,
                    func.max(SERPAnalysis.created_at).label('latest')
                )
                .where(SERPAnalysis.created_at > seven_days_ago)
                .group_by(SERPAnalysis.query, SERPAnalysis.location, SERPAnalysis.device)
                .order_by(func.count(SERPAnalysis.id).desc())
                .limit(50)  # Top 50 queries
            )
            
            cached_count = 0
            for row in result:
                # Get the latest result for this query combination
                latest_result = await db.execute(
                    select(SERPAnalysis)
                    .where(
                        SERPAnalysis.query == row.query,
                        SERPAnalysis.location == row.location,
                        SERPAnalysis.device == row.device
                    )
                    .order_by(SERPAnalysis.created_at.desc())
                    .limit(1)
                )
                serp_cache = latest_result.scalar_one_or_none()
                
                if serp_cache and serp_cache.results:
                    cache_key = f"serp:{serp_cache.query}:{serp_cache.location}:{serp_cache.device}"
                    await cache_manager.set(
                        cache_key,
                        serp_cache.results,
                        ttl=3600  # 1 hour TTL
                    )
                    cached_count += 1
                    
            logger.info(f"Warmed cache for {cached_count} SERP queries")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming SERP cache: {e}")
            return 0
    
    async def warm_performance_cache(self, db: AsyncSession) -> int:
        """
        Warm cache for Core Web Vitals performance data.
        
        Returns:
            Number of performance metrics cached
        """
        try:
            # Get all active sites
            # Note: Using created_at as fallback if last_crawled doesn't exist in DB yet
            try:
                result = await db.execute(
                    select(Site)
                    .where(Site.status == "active")
                    .order_by(Site.last_crawled.desc().nullsfirst())
                    .limit(50)  # Top 50 active sites
                )
            except Exception:
                # Fallback if last_crawled column doesn't exist yet
                result = await db.execute(
                    select(Site)
                    .where(Site.status == "active")
                    .order_by(Site.created_at.desc())
                    .limit(50)  # Top 50 active sites
                )
            sites = result.scalars().all()
            
            cached_count = 0
            for site in sites:
                # Get latest performance metrics
                metrics_result = await db.execute(
                    select(PerformanceMetric)
                    .where(PerformanceMetric.site_id == site.id)
                    .order_by(PerformanceMetric.created_at.desc())
                    .limit(1)
                )
                latest_metric = metrics_result.scalar_one_or_none()
                
                if latest_metric:
                    # Cache desktop metrics
                    if latest_metric.desktop_lcp is not None:
                        cache_key = f"cwv:desktop:{site.id}"
                        await cache_manager.set(
                            cache_key,
                            {
                                "lcp": latest_metric.desktop_lcp,
                                "fid": latest_metric.desktop_fid,
                                "cls": latest_metric.desktop_cls,
                                "ttfb": latest_metric.desktop_ttfb,
                                "inp": latest_metric.desktop_inp,
                                "score": latest_metric.desktop_score,
                                "timestamp": latest_metric.created_at.isoformat()
                            },
                            ttl=3600  # 1 hour TTL
                        )
                        cached_count += 1
                    
                    # Cache mobile metrics
                    if latest_metric.mobile_lcp is not None:
                        cache_key = f"cwv:mobile:{site.id}"
                        await cache_manager.set(
                            cache_key,
                            {
                                "lcp": latest_metric.mobile_lcp,
                                "fid": latest_metric.mobile_fid,
                                "cls": latest_metric.mobile_cls,
                                "ttfb": latest_metric.mobile_ttfb,
                                "inp": latest_metric.mobile_inp,
                                "score": latest_metric.mobile_score,
                                "timestamp": latest_metric.created_at.isoformat()
                            },
                            ttl=3600  # 1 hour TTL
                        )
                        cached_count += 1
                        
            logger.info(f"Warmed cache for {cached_count} performance metrics")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming performance cache: {e}")
            return 0
    
    async def warm_dashboard_cache(self, db: AsyncSession) -> int:
        """
        Warm cache for dashboard aggregated data.
        
        Returns:
            Number of dashboard items cached
        """
        try:
            cached_count = 0
            
            # Cache total projects count by user
            result = await db.execute(
                select(
                    Project.user_id,
                    func.count(Project.id).label('count')
                )
                .group_by(Project.user_id)
            )
            
            for row in result:
                cache_key = f"dashboard:projects:count:{row.user_id}"
                await cache_manager.set(cache_key, row.count, ttl=300)  # 5 min TTL
                cached_count += 1
            
            # Cache total sites count by user
            result = await db.execute(
                select(
                    Site.user_id,
                    func.count(Site.id).label('count')
                )
                .where(Site.status == "active")
                .group_by(Site.user_id)
            )
            
            for row in result:
                cache_key = f"dashboard:sites:count:{row.user_id}"
                await cache_manager.set(cache_key, row.count, ttl=300)  # 5 min TTL
                cached_count += 1
                
            logger.info(f"Warmed cache for {cached_count} dashboard items")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error warming dashboard cache: {e}")
            return 0
    
    async def run_warming_cycle(self) -> Dict[str, int]:
        """
        Run a complete cache warming cycle.
        
        Returns:
            Dictionary with counts of cached items by type
        """
        if self.is_running:
            logger.warning("Cache warming already in progress, skipping")
            return {}
            
        self.is_running = True
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info("Starting cache warming cycle")
            
            async with async_session_factory() as db:
                results = {
                    "projects": await self.warm_project_cache(db),
                    "serp": await self.warm_serp_cache(db),
                    "performance": await self.warm_performance_cache(db),
                    "dashboard": await self.warm_dashboard_cache(db)
                }
                
            self.last_run = datetime.now(timezone.utc)
            duration = (self.last_run - start_time).total_seconds()
            
            logger.info(
                f"Cache warming completed in {duration:.2f}s",
                extra={
                    "results": results,
                    "total_cached": sum(results.values())
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Cache warming cycle failed: {e}")
            return {}
            
        finally:
            self.is_running = False


# Global cache warmer instance
cache_warmer = CacheWarmer()


async def start_cache_warming_scheduler():
    """
    Start the cache warming scheduler that runs periodically.
    
    This should be called during application startup.
    """
    logger.info("Starting cache warming scheduler")
    
    while True:
        try:
            # Run cache warming
            await cache_warmer.run_warming_cycle()
            
            # Wait for configured interval (default 30 minutes)
            interval = getattr(settings, 'CACHE_WARMING_INTERVAL', 1800)
            await asyncio.sleep(interval)
            
        except asyncio.CancelledError:
            logger.info("Cache warming scheduler stopped")
            break
        except Exception as e:
            logger.error(f"Cache warming scheduler error: {e}")
            # Wait 5 minutes before retrying
            await asyncio.sleep(300)


async def warm_specific_query(query: str, location: str = "United States", device: str = "desktop") -> bool:
    """
    Warm cache for a specific SERP query.
    
    Args:
        query: Search query
        location: Search location
        device: Device type (desktop/mobile)
        
    Returns:
        True if successfully cached
    """
    try:
        # Fetch fresh SERP data
        results = await serpapi_service.search(
            query=query,
            location=location,
            device=device
        )
        
        if results:
            cache_key = f"serp:{query}:{location}:{device}"
            await cache_manager.set(cache_key, results, ttl=3600)
            logger.info(f"Warmed cache for query: {query}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to warm cache for query '{query}': {e}")
        
    return False


async def warm_site_performance(site_id: int, url: str) -> bool:
    """
    Warm cache for a specific site's performance metrics.
    
    Args:
        site_id: Site ID
        url: Site URL
        
    Returns:
        True if successfully cached
    """
    try:
        # Fetch fresh CWV data
        async with async_session_factory() as db:
            metrics = await cwv_service.get_latest_cwv_data(site_id, url, db)
            
        if metrics:
            # Cache desktop metrics
            if metrics.get("desktop"):
                cache_key = f"cwv:desktop:{site_id}"
                await cache_manager.set(cache_key, metrics["desktop"], ttl=3600)
                
            # Cache mobile metrics
            if metrics.get("mobile"):
                cache_key = f"cwv:mobile:{site_id}"
                await cache_manager.set(cache_key, metrics["mobile"], ttl=3600)
                
            logger.info(f"Warmed performance cache for site: {site_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to warm performance cache for site {site_id}: {e}")
        
    return False