"""
Health and system status endpoints.

Provides comprehensive health checks for all system components
including database, Redis, external APIs, and performance metrics.
"""
import asyncio
import time
import logging
from typing import Any, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.auth.core.dependencies import get_current_superuser
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.db.session import get_db
from app.db.connection_manager import db_manager
from app.core.config import settings
from app.core.performance_monitoring import query_tracker, performance_metrics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    This endpoint provides a quick health status that can be used
    by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "Voltex DSE API",
        "version": "0.1.0"
    }


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Comprehensive health check including all system components.
    
    Checks database connectivity, Redis cache, and performance metrics.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "Voltex DSE API",
        "version": "0.1.0",
        "components": {}
    }
    
    overall_healthy = True
    
    # Database health check with enhanced monitoring
    try:
        # Use connection manager for health check
        db_health = await db_manager.health_check()
        
        if db_health["status"] == "healthy":
            health_status["components"]["database"] = {
                "status": "healthy",
                "response_time_ms": db_health["response_time_ms"],
                "pool_status": db_health["pool_status"],
                "connection_metrics": db_health["metrics"],
                "details": "PostgreSQL connection successful with connection pooling"
            }
        else:
            overall_healthy = False
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": db_health.get("error"),
                "connection_metrics": db_health["metrics"],
                "details": "Database health check failed"
            }
    except Exception as e:
        overall_healthy = False
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "details": "Failed to perform database health check"
        }
    
    # Redis/Cache health check
    try:
        from app.core.cache import cache_manager
        
        start_time = time.time()
        test_key = f"health_check_{int(time.time())}"
        await cache_manager.set(test_key, "test_value", expire=60)
        cached_value = await cache_manager.get(test_key)
        await cache_manager.delete(test_key)
        cache_response_time = time.time() - start_time
        
        if cached_value == "test_value":
            health_status["components"]["cache"] = {
                "status": "healthy",
                "response_time_ms": round(cache_response_time * 1000, 2),
                "details": "Redis cache read/write successful"
            }
        else:
            overall_healthy = False
            health_status["components"]["cache"] = {
                "status": "unhealthy",
                "details": "Redis cache read/write verification failed"
            }
    except Exception as e:
        overall_healthy = False
        health_status["components"]["cache"] = {
            "status": "unhealthy",
            "error": str(e),
            "details": "Failed to connect to Redis cache"
        }
    
    # Performance metrics health
    try:
        query_stats = query_tracker.get_performance_report()
        api_stats = performance_metrics.get_api_performance_report()
        
        # Determine performance health based on metrics
        performance_status = "healthy"
        performance_issues = []
        
        if query_stats.get("slow_queries_count", 0) > 100:
            performance_status = "warning"
            performance_issues.append("High number of slow queries detected")
        
        if isinstance(api_stats, dict) and api_stats.get("error_rate_percent", 0) > 10:
            performance_status = "warning"
            performance_issues.append("High API error rate detected")
        
        health_status["components"]["performance"] = {
            "status": performance_status,
            "total_queries": query_stats.get("total_queries", 0),
            "slow_queries": query_stats.get("slow_queries_count", 0),
            "api_error_rate": api_stats.get("error_rate_percent", 0) if isinstance(api_stats, dict) else 0,
            "issues": performance_issues
        }
        
        if performance_status == "warning":
            overall_healthy = False
    except Exception as e:
        health_status["components"]["performance"] = {
            "status": "unknown",
            "error": str(e),
            "details": "Failed to retrieve performance metrics"
        }
    
    # Configuration health
    config_issues = []
    
    # Check critical environment variables
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        config_issues.append("SECRET_KEY not properly configured")
    
    if not settings.POSTGRES_PASSWORD:
        config_issues.append("Database password not configured")
    
    # Check external API configuration
    api_configs = {
        "Google PageSpeed API": settings.GOOGLE_PAGESPEED_API_KEY,
        "OpenAI API": settings.OPENAI_API_KEY,
        "SERP API": settings.SERPAPI_KEY,
    }
    
    missing_apis = [name for name, key in api_configs.items() if not key]
    if missing_apis:
        config_issues.append(f"Missing API keys: {', '.join(missing_apis)}")
    
    health_status["components"]["configuration"] = {
        "status": "warning" if config_issues else "healthy",
        "missing_api_keys": len(missing_apis),
        "issues": config_issues
    }
    
    # Overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    elif config_issues:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/performance-baseline", response_model=Dict[str, Any])
async def establish_performance_baseline(
    current_user: UserProfile = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Establish performance baseline metrics.
    
    This endpoint runs a series of benchmark tests to establish
    baseline performance metrics for monitoring purposes.
    Requires superuser privileges.
    """
    try:
        baseline_results = {
            "timestamp": datetime.utcnow(),
            "baseline_metrics": {},
            "recommendations": []
        }
        
        # Database performance baseline
        db_tests = []
        
        # Test 1: Simple SELECT query
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        simple_query_time = time.time() - start_time
        db_tests.append(("simple_select", simple_query_time))
        
        # Test 2: More complex query with table scan
        start_time = time.time()
        await db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        complex_query_time = time.time() - start_time
        db_tests.append(("table_count", complex_query_time))
        
        # Test 3: Connection pool test
        start_time = time.time()
        tasks = []
        for _ in range(5):
            tasks.append(db.execute(text("SELECT pg_sleep(0.1)")))
        await asyncio.gather(*tasks)
        pool_test_time = time.time() - start_time
        db_tests.append(("connection_pool", pool_test_time))
        
        baseline_results["baseline_metrics"]["database"] = {
            "simple_query_ms": round(simple_query_time * 1000, 2),
            "complex_query_ms": round(complex_query_time * 1000, 2),
            "connection_pool_ms": round(pool_test_time * 1000, 2)
        }
        
        # Database performance recommendations
        if simple_query_time > 0.010:  # 10ms
            baseline_results["recommendations"].append(
                "Simple queries taking longer than expected - check database connection"
            )
        
        if complex_query_time > 0.100:  # 100ms
            baseline_results["recommendations"].append(
                "Complex queries slow - consider query optimization or indexing"
            )
        
        if pool_test_time > 1.0:  # 1 second for 5 concurrent connections
            baseline_results["recommendations"].append(
                "Connection pool performance suboptimal - check pool configuration"
            )
        
        # Cache performance baseline
        try:
            from app.core.cache import cache_manager
            
            cache_tests = []
            
            # Test cache set performance
            start_time = time.time()
            await cache_manager.set("baseline_test", "test_value", expire=60)
            cache_set_time = time.time() - start_time
            cache_tests.append(("cache_set", cache_set_time))
            
            # Test cache get performance
            start_time = time.time()
            await cache_manager.get("baseline_test")
            cache_get_time = time.time() - start_time
            cache_tests.append(("cache_get", cache_get_time))
            
            # Test cache delete performance
            start_time = time.time()
            await cache_manager.delete("baseline_test")
            cache_delete_time = time.time() - start_time
            cache_tests.append(("cache_delete", cache_delete_time))
            
            baseline_results["baseline_metrics"]["cache"] = {
                "set_operation_ms": round(cache_set_time * 1000, 2),
                "get_operation_ms": round(cache_get_time * 1000, 2),
                "delete_operation_ms": round(cache_delete_time * 1000, 2)
            }
            
            # Cache performance recommendations
            if cache_set_time > 0.050:  # 50ms
                baseline_results["recommendations"].append(
                    "Cache set operations slow - check Redis connection"
                )
            
            if cache_get_time > 0.010:  # 10ms
                baseline_results["recommendations"].append(
                    "Cache get operations slow - check Redis performance"
                )
        
        except Exception as e:
            baseline_results["baseline_metrics"]["cache"] = {
                "error": str(e),
                "status": "unavailable"
            }
            baseline_results["recommendations"].append(
                "Cache system unavailable - check Redis configuration"
            )
        
        # System resource baseline
        import psutil
        baseline_results["baseline_metrics"]["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        # System resource recommendations
        if psutil.cpu_percent() > 80:
            baseline_results["recommendations"].append(
                "High CPU usage detected - monitor system load"
            )
        
        if psutil.virtual_memory().percent > 80:
            baseline_results["recommendations"].append(
                "High memory usage detected - monitor memory consumption"
            )
        
        # Performance score calculation
        performance_score = 100
        
        # Deduct points for slow operations
        if simple_query_time > 0.010:
            performance_score -= 10
        if complex_query_time > 0.100:
            performance_score -= 15
        if cache_get_time > 0.010:
            performance_score -= 10
        
        # Deduct points for resource usage
        if psutil.cpu_percent() > 80:
            performance_score -= 20
        if psutil.virtual_memory().percent > 80:
            performance_score -= 15
        
        baseline_results["performance_score"] = max(0, performance_score)
        
        if not baseline_results["recommendations"]:
            baseline_results["recommendations"].append(
                "All baseline metrics within acceptable ranges"
            )
        
        return {
            "status": "success",
            "data": baseline_results,
            "message": "Performance baseline established successfully"
        }
        
    except Exception as e:
        logger.error(f"Error establishing performance baseline: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to establish performance baseline: {str(e)}"
        )


@router.get("/database-stats", response_model=Dict[str, Any])
async def get_database_stats(
    current_user: UserProfile = Depends(get_current_superuser)
) -> Dict[str, Any]:
    """
    Get detailed database connection statistics.
    
    Provides real-time metrics about database connection pool usage,
    performance, and errors. Requires superuser privileges.
    """
    try:
        db_health = await db_manager.health_check()
        
        return {
            "status": "success",
            "data": {
                "connection_pool": db_health.get("pool_status", {}),
                "metrics": db_health.get("metrics", {}),
                "health_status": db_health.get("status", "unknown"),
                "response_time_ms": db_health.get("response_time_ms", 0),
                "timestamp": db_health.get("timestamp")
            },
            "message": "Database statistics retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error retrieving database stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve database statistics: {str(e)}"
        )