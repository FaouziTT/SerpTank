"""
Cache management endpoints.

This module provides endpoints for cache management, including
manual cache warming and cache statistics.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.auth.core.dependencies import get_current_superuser
from app.auth.schemas.auth import UserProfile
from app.core.cache import cache_manager
from app.core.cache_warming import cache_warmer, warm_specific_query, warm_site_performance
from app.core.structured_logging import get_logger, log_execution_time
from app.core.audit import audit_action, AuditActions, ResourceTypes

logger = get_logger(__name__)
router = APIRouter()


@router.post("/warm", response_model=Dict[str, Any])
@log_execution_time(logger)
async def trigger_cache_warming(
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Manually trigger cache warming process.
    
    This endpoint is restricted to superusers only.
    """
    # Add to background tasks to avoid blocking
    background_tasks.add_task(cache_warmer.run_warming_cycle)
    
    logger.info(f"Cache warming triggered by user {current_user.email}")
    
    return {
        "status": "started",
        "message": "Cache warming process has been triggered in the background"
    }


@router.post("/warm/query", response_model=Dict[str, Any])
@log_execution_time(logger)
async def warm_query_cache(
    query: str,
    location: str = "United States",
    device: str = "desktop",
    background_tasks: BackgroundTasks = None,
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Warm cache for a specific SERP query.
    
    This endpoint is restricted to superusers only.
    """
    # Validate device type
    if device not in ["desktop", "mobile"]:
        raise HTTPException(status_code=400, detail="Device must be 'desktop' or 'mobile'")
    
    # Add to background tasks
    background_tasks.add_task(warm_specific_query, query, location, device)
    
    logger.info(f"Query cache warming triggered for '{query}' by user {current_user.email}")
    
    return {
        "status": "started",
        "query": query,
        "location": location,
        "device": device,
        "message": "Query cache warming has been triggered"
    }


@router.post("/warm/site/{site_id}", response_model=Dict[str, Any])
@log_execution_time(logger)
async def warm_site_cache(
    site_id: int,
    url: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Warm cache for a specific site's performance metrics.
    
    This endpoint is restricted to superusers only.
    """
    # Add to background tasks
    background_tasks.add_task(warm_site_performance, site_id, url)
    
    logger.info(f"Site cache warming triggered for site {site_id} by user {current_user.email}")
    
    return {
        "status": "started",
        "site_id": site_id,
        "url": url,
        "message": "Site performance cache warming has been triggered"
    }


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_statistics(
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Get cache statistics and information.
    
    This endpoint is restricted to superusers only.
    """
    try:
        stats = await cache_manager.get_stats()
        
        # Add warming status
        warming_status = {
            "is_running": cache_warmer.is_running,
            "last_run": cache_warmer.last_run.isoformat() if cache_warmer.last_run else None
        }
        
        return {
            "cache_stats": stats,
            "warming_status": warming_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")


@router.delete("/clear", response_model=Dict[str, Any])
@audit_action(
    action=AuditActions.DELETE,
    resource_type=ResourceTypes.CACHE
)
async def clear_cache(
    pattern: str = None,
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Clear cache entries.
    
    If pattern is provided, only entries matching the pattern will be cleared.
    This endpoint is restricted to superusers only.
    """
    try:
        if pattern:
            deleted_count = await cache_manager.delete_pattern(pattern)
            message = f"Cleared {deleted_count} cache entries matching pattern '{pattern}'"
        else:
            await cache_manager.clear()
            message = "All cache entries have been cleared"
            
        logger.info(f"Cache cleared by user {current_user.email}", extra={"pattern": pattern})
        
        return {
            "status": "success",
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")