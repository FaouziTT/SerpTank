"""
Performance monitoring endpoints.

Provides endpoints for monitoring application performance,
database query statistics, and API response metrics.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.performance_monitoring import query_tracker, performance_metrics
from app.auth.core.dependencies import get_current_superuser
from app.auth.schemas.auth import UserProfile
from app.models.user import User

router = APIRouter()


@router.get("/query-performance", response_model=Dict[str, Any])
async def get_query_performance(
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Get database query performance statistics.
    
    Requires superuser privileges.
    """
    try:
        report = query_tracker.get_performance_report()
        return {
            "status": "success",
            "data": report,
            "message": "Query performance report generated successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance report: {str(e)}"
        )


@router.get("/api-performance", response_model=Dict[str, Any])
async def get_api_performance(
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Get API endpoint performance statistics.
    
    Requires superuser privileges.
    """
    try:
        report = performance_metrics.get_api_performance_report()
        return {
            "status": "success",
            "data": report,
            "message": "API performance report generated successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate API performance report: {str(e)}"
        )


@router.get("/slow-queries", response_model=Dict[str, Any])
async def get_slow_queries(
    limit: int = 50,
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Get recent slow queries.
    
    Args:
        limit: Maximum number of slow queries to return (default: 50)
    
    Requires superuser privileges.
    """
    try:
        slow_queries = query_tracker.slow_queries[-limit:] if limit > 0 else query_tracker.slow_queries
        
        return {
            "status": "success",
            "data": {
                "slow_queries": slow_queries,
                "total_slow_queries": len(query_tracker.slow_queries),
                "threshold_seconds": query_tracker.slow_query_threshold
            },
            "message": f"Retrieved {len(slow_queries)} slow queries"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve slow queries: {str(e)}"
        )


@router.post("/reset-metrics", response_model=Dict[str, Any])
async def reset_performance_metrics(
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Reset all performance metrics.
    
    This clears query statistics, slow query logs, and API performance data.
    Requires superuser privileges.
    """
    try:
        # Reset query tracker
        query_tracker.query_stats.clear()
        query_tracker.slow_queries.clear()
        
        # Reset API metrics
        performance_metrics.endpoint_metrics.clear()
        performance_metrics.api_response_times.clear()
        
        return {
            "status": "success",
            "message": "All performance metrics have been reset"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset performance metrics: {str(e)}"
        )


@router.get("/health-metrics", response_model=Dict[str, Any])
async def get_health_metrics(
    current_user: UserProfile = Depends(get_current_superuser),
) -> Dict[str, Any]:
    """
    Get overall application health metrics.
    
    Requires superuser privileges.
    """
    try:
        # Calculate health indicators
        query_stats = query_tracker.get_performance_report()
        api_stats = performance_metrics.get_api_performance_report()
        
        # Determine health status based on metrics
        health_status = "healthy"
        issues = []
        
        # Check for performance issues
        if query_stats.get("slow_queries_count", 0) > 100:
            health_status = "warning"
            issues.append("High number of slow queries detected")
        
        if isinstance(api_stats, dict) and api_stats.get("error_rate_percent", 0) > 5:
            health_status = "warning"
            issues.append("High API error rate detected")
        
        # Check for critical issues
        if query_stats.get("slow_queries_count", 0) > 500:
            health_status = "critical"
            issues.append("Critical: Very high number of slow queries")
        
        if isinstance(api_stats, dict) and api_stats.get("error_rate_percent", 0) > 20:
            health_status = "critical"
            issues.append("Critical: Very high API error rate")
        
        return {
            "status": "success",
            "data": {
                "health_status": health_status,
                "issues": issues,
                "query_metrics": {
                    "total_queries": query_stats.get("total_queries", 0),
                    "slow_queries": query_stats.get("slow_queries_count", 0),
                    "unique_queries": query_stats.get("unique_queries", 0)
                },
                "api_metrics": {
                    "total_calls": api_stats.get("total_api_calls", 0) if isinstance(api_stats, dict) else 0,
                    "error_rate": api_stats.get("error_rate_percent", 0) if isinstance(api_stats, dict) else 0,
                    "unique_endpoints": api_stats.get("unique_endpoints", 0) if isinstance(api_stats, dict) else 0
                }
            },
            "message": "Health metrics retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve health metrics: {str(e)}"
        )