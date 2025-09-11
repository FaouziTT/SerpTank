"""
Google Search Console API endpoints with OAuth support.

This module provides endpoints for fetching organic search data including
clicks, impressions, CTR, average position, and top performing queries/pages.
Supports both OAuth (user-owned data) and service account authentication.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.core.config import settings
from app.models.user import User
from app.services.google_search_console import get_gsc_client
from app.services.oauth_service import oauth_service
from app.db.session import get_db
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)


def check_gsc_availability(gsc_client) -> None:
    """
    Check if Google Search Console is available and properly configured.
    
    Raises:
        HTTPException: If GSC is not configured or not authenticated
    """
    if not gsc_client.is_authenticated():
        logger.warning("Google Search Console not configured or not authenticated")
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "service_unavailable",
                "message": "Google Search Console is not configured. Please connect your GSC account in settings.",
                "service": "search_console",
                "configured": gsc_client.is_configured(),
                "authenticated": False
            }
        )


class SearchPerformanceResponse(BaseModel):
    """Response model for search performance data."""
    total_clicks: int = Field(..., description="Total clicks in the period")
    total_impressions: int = Field(..., description="Total impressions in the period")
    average_ctr: float = Field(..., description="Average click-through rate as percentage")
    average_position: float = Field(..., description="Average search position")
    date_range: Dict[str, str] = Field(..., description="Date range for the data")
    daily_breakdown: List[Dict[str, Any]] = Field(..., description="Daily performance breakdown")


class PaginationInfo(BaseModel):
    """Pagination information."""
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class QueryPerformanceResponse(BaseModel):
    """Response model for query performance data."""
    queries: List[Dict[str, Any]] = Field(..., description="Top performing queries")
    total_queries: int = Field(..., description="Total number of queries")
    date_range: Dict[str, str] = Field(..., description="Date range for the data")
    pagination: Optional[PaginationInfo] = Field(None, description="Pagination information")


class PagePerformanceResponse(BaseModel):
    """Response model for page performance data."""
    pages: List[Dict[str, Any]] = Field(..., description="Top performing pages")
    total_pages: int = Field(..., description="Total number of pages")
    date_range: Dict[str, str] = Field(..., description="Date range for the data")
    pagination: Optional[PaginationInfo] = Field(None, description="Pagination information")


class UserSitesResponse(BaseModel):
    """Response model for user's Search Console sites."""
    sites: List[Dict[str, Any]] = Field(..., description="List of user's verified sites")
    total_sites: int = Field(..., description="Total number of sites")


@router.get("/performance")
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"search_console:performance:{kwargs.get('current_user').id}:{kwargs.get('site_url', 'all')}:{kwargs.get('days', 30)}")
async def get_search_performance(
    request: Request,
    days: int = Query(30, description="Number of days to look back"),
    site_url: Optional[str] = Query(None, description="Specific site URL to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> SearchPerformanceResponse:
    """
    Get overall search performance data from Google Search Console.
    
    Returns clicks, impressions, CTR, and average position data.
    Uses OAuth token if available, otherwise falls back to service account.
    """
    try:
        # Get OAuth access token if available
        access_token = None
        if current_user:
            access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        # Get GSC client (OAuth or service account)
        gsc_client = get_gsc_client(access_token=access_token, site_url=site_url)
        
        # Check if GSC is available
        check_gsc_availability(gsc_client)
        
        # Calculate date range
        start_date = f"{days}daysAgo"
        end_date = "today"
        
        # Get search performance data
        performance_data = await gsc_client.get_search_performance(
            start_date=start_date,
            end_date=end_date,
            dimensions=['date']
        )
        
        return SearchPerformanceResponse(**performance_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like our 503 above)
        raise
    except Exception as e:
        logger.error(f"Error getting search performance: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error", 
                "message": f"Failed to get search performance data: {str(e)}",
                "service": "search_console"
            }
        )


@router.get("/queries")
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"search_console:queries:{kwargs.get('current_user').id}:{kwargs.get('site_url', 'all')}:{kwargs.get('days', 30)}:{kwargs.get('page', 1)}:{kwargs.get('page_size', 20)}:{kwargs.get('sort_by', 'clicks')}:{kwargs.get('sort_order', 'desc')}:{kwargs.get('search', '')}")
async def get_top_queries(
    request: Request,
    days: int = Query(30, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("clicks", description="Field to sort by (clicks, impressions, ctr, position)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    search: Optional[str] = Query(None, description="Search filter for queries"),
    site_url: Optional[str] = Query(None, description="Specific site URL to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> QueryPerformanceResponse:
    """
    Get top performing search queries from Google Search Console with server-side pagination.
    
    Returns the top queries with performance metrics, supporting pagination, sorting, and filtering.
    """
    try:
        # Get OAuth access token if available
        access_token = None
        if current_user:
            access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        # Get GSC client (OAuth or service account)
        gsc_client = get_gsc_client(access_token=access_token, site_url=site_url)
        
        # Check if GSC is available
        check_gsc_availability(gsc_client)
        
        # Calculate date range
        start_date = f"{days}daysAgo"
        end_date = "today"
        
        # Get all queries data (we'll paginate server-side)
        query_data = await gsc_client.get_top_queries(
            start_date=start_date,
            end_date=end_date,
            limit=1000  # Get more data for proper pagination
        )
        
        # Extract queries list
        all_queries = query_data.get("queries", [])
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            all_queries = [q for q in all_queries if search_lower in q.get("query", "").lower()]
        
        # Sort the queries
        reverse_order = sort_order == "desc"
        if sort_by in ["clicks", "impressions", "position"]:
            all_queries.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse_order)
        elif sort_by == "ctr":
            all_queries.sort(key=lambda x: x.get("ctr", 0), reverse=reverse_order)
        
        # Calculate pagination
        total_items = len(all_queries)
        total_pages = (total_items + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get paginated results
        paginated_queries = all_queries[start_idx:end_idx]
        
        # Update response with pagination info
        query_data["queries"] = paginated_queries
        query_data["pagination"] = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
        return QueryPerformanceResponse(**query_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like our 503 above)
        raise
    except Exception as e:
        logger.error(f"Error getting top queries: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error", 
                "message": f"Failed to get top queries data: {str(e)}",
                "service": "search_console"
            }
        )


@router.get("/pages")
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"search_console:pages:{kwargs.get('current_user').id}:{kwargs.get('site_url', 'all')}:{kwargs.get('days', 30)}:{kwargs.get('page', 1)}:{kwargs.get('page_size', 20)}:{kwargs.get('sort_by', 'clicks')}:{kwargs.get('sort_order', 'desc')}:{kwargs.get('search', '')}")
async def get_top_pages(
    request: Request,
    days: int = Query(30, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("clicks", description="Field to sort by (clicks, impressions, ctr, position)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    search: Optional[str] = Query(None, description="Search filter for page URLs"),
    site_url: Optional[str] = Query(None, description="Specific site URL to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> PagePerformanceResponse:
    """
    Get top performing pages from Google Search Console with server-side pagination.
    
    Returns the top pages with performance metrics, supporting pagination, sorting, and filtering.
    """
    try:
        # Get OAuth access token if available
        access_token = None
        if current_user:
            access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        # Get GSC client (OAuth or service account)
        gsc_client = get_gsc_client(access_token=access_token, site_url=site_url)
        
        # Check if GSC is available
        check_gsc_availability(gsc_client)
        
        # Calculate date range
        start_date = f"{days}daysAgo"
        end_date = "today"
        
        # Get all pages data (we'll paginate server-side)
        page_data = await gsc_client.get_top_pages(
            start_date=start_date,
            end_date=end_date,
            limit=1000  # Get more data for proper pagination
        )
        
        # Extract pages list
        all_pages = page_data.get("pages", [])
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            all_pages = [p for p in all_pages if search_lower in p.get("page", "").lower()]
        
        # Sort the pages
        reverse_order = sort_order == "desc"
        if sort_by in ["clicks", "impressions", "position"]:
            all_pages.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse_order)
        elif sort_by == "ctr":
            all_pages.sort(key=lambda x: x.get("ctr", 0), reverse=reverse_order)
        
        # Calculate pagination
        total_items = len(all_pages)
        total_pages_count = (total_items + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get paginated results
        paginated_pages = all_pages[start_idx:end_idx]
        
        # Create response with pagination info
        return PagePerformanceResponse(
            pages=paginated_pages,
            total_pages=total_items,
            date_range=page_data.get("date_range", {}),
            pagination=PaginationInfo(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages_count,
                has_next=page < total_pages_count,
                has_previous=page > 1
            )
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like our 503 above)
        raise
    except Exception as e:
        logger.error(f"Error getting top pages: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error", 
                "message": f"Failed to get top pages data: {str(e)}",
                "service": "search_console"
            }
        )


@router.get("/sites")
async def get_user_sites(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserSitesResponse:
    """
    Get list of sites that the user has access to in Search Console.
    Requires OAuth authentication.
    """
    try:
        # Get OAuth access token
        access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        if not access_token:
            raise HTTPException(
                status_code=400, 
                detail="OAuth authentication required. Please connect your Google account first."
            )
        
        # Get GSC client with OAuth
        gsc_client = get_gsc_client(access_token=access_token)
        
        # Get user sites
        sites = await gsc_client.get_user_sites()
        
        return UserSitesResponse(
            sites=sites,
            total_sites=len(sites)
        )
        
    except HTTPException:
        raise
    except HTTPException:
        # Re-raise HTTP exceptions (like our 503 above)
        raise
    except Exception as e:
        logger.error(f"Error getting user sites: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error", 
                "message": f"Failed to get user sites: {str(e)}",
                "service": "search_console"
            }
        )


@router.get("/dashboard")
async def get_search_console_dashboard(
    request: Request,
    days: int = Query(30, description="Number of days to look back"),
    site_url: Optional[str] = Query(None, description="Specific site URL to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive Search Console dashboard data.
    
    Returns both performance metrics and top queries in a single request.
    """
    try:
        # Get OAuth access token if available
        access_token = None
        if current_user:
            access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        # Get GSC client (OAuth or service account)
        gsc_client = get_gsc_client(access_token=access_token, site_url=site_url)
        
        # Check if GSC is available
        check_gsc_availability(gsc_client)
        
        # Calculate date range
        start_date = f"{days}daysAgo"
        end_date = "today"
        
        # Get both performance and query data
        performance_data = await gsc_client.get_search_performance(
            start_date=start_date,
            end_date=end_date,
            dimensions=['date']
        )
        
        query_data = await gsc_client.get_top_queries(
            start_date=start_date,
            end_date=end_date,
            limit=20
        )
        
        # Get authentication status
        auth_status = {
            "has_oauth": access_token is not None,
            "is_configured": gsc_client.is_configured(),
            "is_authenticated": gsc_client.is_authenticated(),
            "site_url": gsc_client.site_url,
            "property_url": gsc_client.property_url
        }
        
        return {
            "performance": performance_data,
            "top_queries": query_data["queries"][:10],  # Top 10 for dashboard
            "auth_status": auth_status,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like our 503 above)
        raise
    except Exception as e:
        logger.error(f"Error getting Search Console dashboard data: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error", 
                "message": f"Failed to get dashboard data: {str(e)}",
                "service": "search_console"
            }
        )


@router.get("/debug-url")
async def debug_url_format(
    request: Request,
    site_url: str = Query(..., description="Site URL to debug and test format variations"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Debug URL format issues by showing all possible variations and checking which ones
    are available in the user's Google Search Console account.
    """
    try:
        # Get OAuth access token
        access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        if not access_token:
            return {
                "error": "OAuth authentication required. Please connect your Google account first.",
                "oauth_required": True
            }
        
        # Create GSC client
        gsc_client = get_gsc_client(access_token=access_token, site_url=site_url)
        
        # Get normalized URL and variations
        normalized_url = gsc_client._normalize_property_url(site_url)
        possible_urls = gsc_client._get_possible_property_urls(site_url)
        
        # Get user's actual sites
        try:
            user_sites = await gsc_client.get_user_sites()
            available_sites = [site['site_url'] for site in user_sites]
        except Exception as e:
            available_sites = []
            logger.error(f"Error getting user sites for debugging: {e}")
        
        # Find matches
        matches = []
        for url in possible_urls:
            if url in available_sites:
                matches.append(url)
        
        return {
            "input_url": site_url,
            "normalized_url": normalized_url,
            "possible_variations": possible_urls,
            "available_sites": available_sites,
            "matching_sites": matches,
            "recommendation": matches[0] if matches else "No matching sites found. Please verify the domain is added to your Google Search Console account.",
            "debug_info": {
                "has_oauth": True,
                "sites_found": len(available_sites),
                "variations_generated": len(possible_urls),
                "matches_found": len(matches)
            }
        }
        
    except Exception as e:
        logger.error(f"Error debugging URL format: {e}")
        return {
            "error": f"Failed to debug URL format: {str(e)}",
            "input_url": site_url
        }


@router.get("/status")
async def get_search_console_status(
    request: Request,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Search Console integration status and configuration.
    """
    try:
        # Get OAuth access token if available
        access_token = None
        if current_user:
            access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        
        # Get default GSC client for status check
        gsc_client = get_gsc_client()
        
        return {
            "oauth_connected": access_token is not None,
            "service_account_configured": gsc_client.is_configured(),
            "service_account_authenticated": gsc_client.is_authenticated(),
            "configuration": {
                "site_url": gsc_client.site_url,
                "property_url": gsc_client.property_url,
                "has_service_account": bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
                "scopes_available": [
                    "https://www.googleapis.com/auth/webmasters.readonly"
                ]
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like our 503 above)
        raise
    except Exception as e:
        logger.error(f"Error getting Search Console status: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error", 
                "message": f"Failed to get status: {str(e)}",
                "service": "search_console"
            }
        )
