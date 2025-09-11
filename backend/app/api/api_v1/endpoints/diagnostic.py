"""
API endpoints for the Diagnostic & Monitoring Core (Pillar 1).

This module provides endpoints for crawling websites, analyzing log files,
monitoring Core Web Vitals, and other diagnostic functions.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.models.activity import Activity
from app.core.pagination import PageParams, get_pagination_params
from app.schemas.diagnostic import (
    CrawlRequest,
    CrawlResponse,
    CrawlStatus,
    LogAnalysisRequest,
    LogAnalysisResponse,
    CoreWebVitalsRequest,
    CoreWebVitalsResponse,
    SiteHealthResponse,
    PerformanceTrendsResponse,
    SEOAnalysisRequest,
    SEOAnalysisResponse,
    RecentActivitiesResponse
)
from fastapi_cache.decorator import cache
from app.core.config import cache_config
from app.services.crawler import crawler_service
from app.services.log_analyzer import log_analyzer_service
from app.services.core_web_vitals import cwv_service
from app.services.diagnostic import DiagnosticService
from app.db.session import get_db
from app.core.db_optimization import optimize_for_read

router = APIRouter()
logger = logging.getLogger(__name__)
diagnostic_service = DiagnosticService()


@router.post("/crawl", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Start a new crawl of a website.
    
    This endpoint initiates a crawl of the specified website with the given parameters.
    The crawl runs as a background task and its progress can be monitored using the
    returned crawl ID.
    
    Args:
        request: The crawl request parameters
        background_tasks: FastAPI background tasks
        current_user: The authenticated user
        
    Returns:
        A response containing the crawl ID and initial status
    """
    logger.info(f"Starting crawl for {request.url} requested by user {current_user.email}")
    
    try:
        crawl_id = await crawler_service.start_crawl(
            url=request.url,
            user_id=current_user.id,
            max_urls=request.max_urls,
            respect_robots_txt=request.respect_robots_txt,
            crawl_javascript=request.crawl_javascript,
            follow_external_links=request.follow_external_links,
            site_id=request.site_id,
        )
        
        # Add the crawl monitoring task to background tasks
        background_tasks.add_task(
            crawler_service.monitor_crawl,
            crawl_id=crawl_id,
            user_id=current_user.id,
        )
        
        return CrawlResponse(
            crawl_id=crawl_id,
            status=CrawlStatus.STARTED,
            message="Crawl started successfully",
        )
    
    except Exception as e:
        logger.error(f"Error starting crawl: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start crawl: {str(e)}",
        )


@router.get("/crawl/{crawl_id}", response_model=CrawlResponse)
async def get_crawl_status(
    crawl_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Get the status of a crawl.
    
    This endpoint returns the current status of a crawl, including progress,
    errors encountered, and completion status.
    
    Args:
        crawl_id: The ID of the crawl
        current_user: The authenticated user
        
    Returns:
        The current status of the crawl
    """
    logger.info(f"Getting status for crawl {crawl_id} by user {current_user.email}")
    
    try:
        status = await crawler_service.get_crawl_status(
            crawl_id=crawl_id,
            user_id=current_user.id,
        )
        
        return status
    
    except Exception as e:
        logger.error(f"Error getting crawl status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get crawl status: {str(e)}",
        )


@router.get("/crawl/results/{site_id}")
async def get_crawl_results(
    site_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get the latest crawl results for a site.
    
    This endpoint returns the crawl data from the most recent completed crawl
    for the specified site, including all discovered URLs, page analysis, and
    technical SEO insights.
    
    Args:
        site_id: The ID of the site to get crawl results for
        current_user: The authenticated user
        db: Database session
        
    Returns:
        The latest crawl results and analysis
    """
    logger.info(f"Getting crawl results for site {site_id} requested by user {current_user.email}")
    
    try:
        # Get the latest crawl summary for the site
        crawl_summary = await crawler_service.get_latest_crawl_summary(
            site_id=site_id,
            user_id=current_user.id
        )
        
        return {
            "site_id": site_id,
            "crawl_data": crawl_summary,
            "urls_crawled": crawl_summary.get("crawlability", {}).get("indexable_pages", 0),
            "indexable_pages": crawl_summary.get("crawlability", {}).get("indexable_pages", 0),
            "technical_issues": crawl_summary.get("technical_issues", []),
            "recommendations": [
                issue.get("recommendation", "No recommendation available")
                for issue in crawl_summary.get("technical_issues", [])
            ],
            "crawl_efficiency": crawl_summary.get("crawlability", {}).get("crawl_efficiency", 0),
            "last_crawl": "Recently completed"
        }
        
    except Exception as e:
        logger.error(f"Error getting crawl results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get crawl results: {str(e)}",
        )


@router.post("/log-analysis", response_model=LogAnalysisResponse)
async def analyze_logs(
    request: LogAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Analyze server logs or CDN logs.
    
    This endpoint initiates analysis of server logs or CDN logs to extract
    insights about bot behavior, crawl budget, and performance issues.
    
    Args:
        request: The log analysis request parameters
        background_tasks: FastAPI background tasks
        current_user: The authenticated user
        
    Returns:
        A response containing the analysis ID and initial status
    """
    logger.info(f"Starting log analysis requested by user {current_user.email}")
    
    try:
        analysis_id = await log_analyzer_service.start_analysis(
            log_source=request.log_source,
            log_type=request.log_type,
            date_range=request.date_range,
            user_id=current_user.id,
        )
        
        # Add the analysis monitoring task to background tasks
        background_tasks.add_task(
            log_analyzer_service.monitor_analysis,
            analysis_id=analysis_id,
            user_id=current_user.id,
        )
        
        return LogAnalysisResponse(
            analysis_id=analysis_id,
            status="STARTED",
            message="Log analysis started successfully",
        )
    
    except Exception as e:
        logger.error(f"Error starting log analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start log analysis: {str(e)}",
        )


@router.post("/core-web-vitals", response_model=CoreWebVitalsResponse)
async def analyze_core_web_vitals(
    request: CoreWebVitalsRequest,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Analyze Core Web Vitals for a website.
    
    This endpoint retrieves and analyzes Core Web Vitals data for a website,
    using both lab data (Lighthouse) and real user data (CrUX API).
    
    Args:
        request: The Core Web Vitals analysis request parameters
        current_user: The authenticated user
        
    Returns:
        Core Web Vitals analysis results
    """
    logger.info(f"Analyzing Core Web Vitals for {request.url} requested by user {current_user.email}")
    
    try:
        result = await cwv_service.analyze_core_web_vitals(
            url=str(request.url),
            use_crux=request.use_crux,
            use_lighthouse=request.use_lighthouse,
            user_id=current_user.id,
        )
        
        # Save the data for historical tracking if user has a site configured
        if hasattr(request, 'site_id') and request.site_id:
            await cwv_service.save_performance_metrics(
                site_id=request.site_id,
                url=str(request.url),
                lab_data=result.lab_data,
                field_data=result.field_data,
                device_type="mobile"  # Default to mobile for now
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing Core Web Vitals: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze Core Web Vitals: {str(e)}",
        )


@router.get("/performance-trends")
@cache(expire=cache_config.API_RESPONSE_TTL, key_builder=lambda func, *args, **kwargs: f"performance_trends:{kwargs.get('site_id', 'none')}:{kwargs.get('period', '30d')}")
async def get_performance_trends(
    site_id: Optional[int] = Query(None, description="Site ID to get trends for"),
    period: str = Query("30d", description="Time period (7d, 30d, 90d)"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get performance trends for a site.
    
    This endpoint returns performance trends data for a site, including
    Core Web Vitals trends, crawl trends, and overall performance metrics.
    
    Args:
        site_id: The ID of the site (optional, will use user's primary site if not provided)
        period: Time period for analysis (7d, 30d, 90d)
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Performance trends data
    """
    logger.info(f"Getting performance trends for period {period} requested by user {current_user.email}")
    
    try:
        result = await diagnostic_service.get_performance_trends(
            site_id=site_id,
            period=period,
            user_id=current_user.id,
            db=db
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Error getting performance trends: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting performance trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance trends: {str(e)}",
        )


@router.get("/core-web-vitals")
async def get_core_web_vitals(
    site_id: Optional[int] = Query(None, description="Site ID to get core web vitals for"),
    url: Optional[str] = Query(None, description="URL to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Get Core Web Vitals data for a site or URL.
    
    This endpoint returns Core Web Vitals data for a specific site or URL,
    including both lab data (Lighthouse) and field data (CrUX).
    
    Args:
        site_id: The ID of the site (optional if URL is provided)
        url: The URL to analyze (optional if site_id is provided)
        current_user: The authenticated user
        
    Returns:
        Core Web Vitals data
    """
    logger.info(f"Getting Core Web Vitals data requested by user {current_user.email}")
    
    try:
        if url:
            # Analyze specific URL
            result = await cwv_service.analyze_core_web_vitals(
                url=url,
                use_crux=True,
                use_lighthouse=True,
                user_id=current_user.id,
            )
        elif site_id:
            # Get latest data for site
            result = await cwv_service.get_latest_cwv_data(
                site_id=site_id,
                user_id=current_user.id,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either site_id or url must be provided"
            )
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting Core Web Vitals data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Core Web Vitals data: {str(e)}",
        )


@router.get("/site-health/{site_id}")
# @cache(expire=cache_config.API_RESPONSE_TTL, key_builder=lambda func, site_id, **kwargs: f"site_health:{site_id}")
async def get_site_health(
    site_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get the overall health of a monitored site.
    
    This endpoint returns a comprehensive health assessment of a monitored site,
    including crawlability, performance, and technical SEO issues.
    
    Args:
        site_id: The ID of the site
        current_user: The authenticated user
        db: Database session
        
    Returns:
        A comprehensive site health assessment
    """
    logger.info(f"Getting site health for site {site_id} requested by user {current_user.email}")
    
    try:
        result = await diagnostic_service.get_site_health(
            site_id=site_id,
            user_id=current_user.id,
            db=db
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Error getting site health: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting site health: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get site health: {str(e)}",
        )


@router.post("/seo-analysis")
async def analyze_website_seo(
    url: str = Query(..., description="URL to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Perform comprehensive SEO analysis of a website.
    
    This endpoint uses real SEO analysis tools to analyze
    on-page SEO, technical SEO, and content optimization.
    
    Args:
        url: URL to analyze
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Comprehensive SEO analysis results
    """
    logger.info(f"Performing SEO analysis for {url} requested by user {current_user.email}")
    
    try:
        result = await diagnostic_service.analyze_website_seo(
            url=url,
            user_id=current_user.id,
            db=db
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Error analyzing website SEO: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing website SEO: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze website SEO: {str(e)}",
        )


@router.get("/recent-activities", response_model=Dict[str, Any])
async def get_recent_activities(
    pagination: PageParams = Depends(get_pagination_params),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent activities for the current user or organization with pagination.
    
    Args:
        pagination: Pagination parameters (page, page_size)
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Paginated list of recent activities
    """
    try:
        # For now, use the existing service with limit
        # TODO: Update diagnostic_service to support proper pagination
        activities = await diagnostic_service.get_recent_activities(
            user_id=current_user.id,
            limit=pagination.page_size * pagination.page,
            db=db
        )
        
        # Simulate pagination from the full list
        start_idx = pagination.offset
        end_idx = start_idx + pagination.page_size
        paginated_activities = activities[start_idx:end_idx] if start_idx < len(activities) else []
        
        return {
            "items": paginated_activities,
            "total": len(activities),
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total_pages": (len(activities) + pagination.page_size - 1) // pagination.page_size,
            "has_next": end_idx < len(activities),
            "has_previous": pagination.page > 1
        }
    
    except ValueError as e:
        logger.error(f"Error getting recent activities: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting recent activities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recent activities: {str(e)}"
        )


@router.post("/core-web-vitals/benchmark/{site_id}")
async def create_competitive_benchmark(
    site_id: int,
    competitor_url: str = Query(..., description="Competitor URL to analyze"),
    device_type: str = Query("mobile", description="Device type for analysis (mobile/desktop)"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Analyze a competitor's Core Web Vitals and compare with your site.
    
    This endpoint analyzes a competitor's performance metrics and saves the
    benchmark data for competitive tracking.
    
    Args:
        site_id: Your site ID
        competitor_url: The competitor's URL to analyze
        device_type: Device type for analysis (mobile/desktop)
        current_user: The authenticated user
        
    Returns:
        Competitor analysis and comparison data
    """
    logger.info(f"Creating competitive benchmark for site {site_id} vs {competitor_url} by user {current_user.email}")
    
    try:
        result = await cwv_service.analyze_competitor(
            site_id=site_id,
            competitor_url=competitor_url,
            user_id=current_user.id,
            device_type=device_type
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Error creating competitive benchmark: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating competitive benchmark: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create competitive benchmark: {str(e)}"
        )


@router.get("/core-web-vitals/benchmarks/{site_id}")
async def get_competitive_benchmarks(
    site_id: int,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Get all competitive benchmarks for a site.
    
    This endpoint returns all competitor performance benchmarks that have been
    analyzed for your site, along with comparison insights.
    
    Args:
        site_id: Your site ID
        current_user: The authenticated user
        
    Returns:
        List of competitive benchmarks with analysis
    """
    logger.info(f"Getting competitive benchmarks for site {site_id} by user {current_user.email}")
    
    try:
        result = await cwv_service.get_competitive_benchmarks(
            site_id=site_id,
            user_id=current_user.id
        )
        
        return result
    
    except ValueError as e:
        logger.error(f"Error getting competitive benchmarks: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting competitive benchmarks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get competitive benchmarks: {str(e)}"
        )