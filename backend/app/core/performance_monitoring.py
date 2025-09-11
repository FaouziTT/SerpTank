"""
Performance monitoring and query tracking system.

This module provides comprehensive performance monitoring including:
- Database query performance tracking
- Slow query detection and logging
- Response time metrics
- Performance decorators
"""
import time
import logging
import functools
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from app.core.config import settings

# Configure performance logger
perf_logger = logging.getLogger("voltex.performance")


class QueryPerformanceTracker:
    """Tracks database query performance and identifies slow queries."""
    
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_stats: Dict[str, Dict[str, Any]] = {}
        self.slow_queries: list = []
        
    def log_query(self, query: str, duration: float, parameters: Optional[Dict] = None):
        """Log query execution details."""
        # Normalize query for statistics
        normalized_query = self._normalize_query(query)
        
        # Update statistics
        if normalized_query not in self.query_stats:
            self.query_stats[normalized_query] = {
                "count": 0,
                "total_duration": 0.0,
                "max_duration": 0.0,
                "min_duration": float('inf'),
                "avg_duration": 0.0
            }
        
        stats = self.query_stats[normalized_query]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["max_duration"] = max(stats["max_duration"], duration)
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["avg_duration"] = stats["total_duration"] / stats["count"]
        
        # Log slow queries
        if duration > self.slow_query_threshold:
            slow_query_entry = {
                "query": query,
                "duration": duration,
                "parameters": parameters,
                "timestamp": datetime.utcnow(),
                "normalized_query": normalized_query
            }
            self.slow_queries.append(slow_query_entry)
            
            # Keep only recent slow queries (last 1000)
            if len(self.slow_queries) > 1000:
                self.slow_queries = self.slow_queries[-1000:]
            
            perf_logger.warning(
                f"Slow query detected: {duration:.3f}s - {query[:200]}..."
            )
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for statistical grouping."""
        # Remove parameters and normalize whitespace
        normalized = query.strip()
        # Remove line breaks and extra spaces
        normalized = " ".join(normalized.split())
        # Truncate for grouping
        return normalized[:500]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        total_queries = sum(stats["count"] for stats in self.query_stats.values())
        
        # Find top slow queries by average duration
        slow_by_avg = sorted(
            self.query_stats.items(),
            key=lambda x: x[1]["avg_duration"],
            reverse=True
        )[:10]
        
        # Find most frequent queries
        frequent_queries = sorted(
            self.query_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:10]
        
        return {
            "total_queries": total_queries,
            "unique_queries": len(self.query_stats),
            "slow_queries_count": len(self.slow_queries),
            "slowest_by_average": [
                {
                    "query": query[:200] + "..." if len(query) > 200 else query,
                    "stats": stats
                }
                for query, stats in slow_by_avg
            ],
            "most_frequent": [
                {
                    "query": query[:200] + "..." if len(query) > 200 else query,
                    "stats": stats
                }
                for query, stats in frequent_queries
            ],
            "recent_slow_queries": self.slow_queries[-20:]  # Last 20 slow queries
        }


# Global performance tracker instance
query_tracker = QueryPerformanceTracker(slow_query_threshold=0.5)


def performance_monitor(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                perf_logger.info(
                    f"Operation '{operation_name}' completed in {duration:.3f}s"
                )
                
                if duration > 2.0:  # Log slow operations
                    perf_logger.warning(
                        f"Slow operation detected: '{operation_name}' took {duration:.3f}s"
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                perf_logger.error(
                    f"Operation '{operation_name}' failed after {duration:.3f}s: {str(e)}"
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                perf_logger.info(
                    f"Operation '{operation_name}' completed in {duration:.3f}s"
                )
                
                if duration > 2.0:  # Log slow operations
                    perf_logger.warning(
                        f"Slow operation detected: '{operation_name}' took {duration:.3f}s"
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                perf_logger.error(
                    f"Operation '{operation_name}' failed after {duration:.3f}s: {str(e)}"
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query start time."""
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query completion and log performance."""
    if hasattr(context, '_query_start_time'):
        duration = time.time() - context._query_start_time
        query_tracker.log_query(statement, duration, parameters)


@event.listens_for(Pool, "connect")
def set_postgresql_search_path(dbapi_connection, connection_record):
    """Set up connection-level optimizations."""
    try:
        # For async drivers, we need to handle the cursor differently
        cursor = dbapi_connection.cursor()
        try:
            # Set timezone to UTC for consistency
            cursor.execute("SET timezone='UTC'")
            # Enable parallel query execution
            cursor.execute("SET max_parallel_workers_per_gather = 4")
            # Optimize for faster queries
            cursor.execute("SET random_page_cost = 1.1")
        finally:
            cursor.close()
    except Exception as e:
        # Log error but don't fail the connection
        perf_logger.warning(f"Failed to set PostgreSQL optimizations: {e}")
        pass


class PerformanceMetrics:
    """Centralized performance metrics collection."""
    
    def __init__(self):
        self.endpoint_metrics: Dict[str, Dict[str, Any]] = {}
        self.api_response_times: list = []
    
    def record_api_call(self, endpoint: str, method: str, duration: float, status_code: int):
        """Record API endpoint performance."""
        key = f"{method} {endpoint}"
        
        if key not in self.endpoint_metrics:
            self.endpoint_metrics[key] = {
                "count": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "max_duration": 0.0,
                "min_duration": float('inf'),
                "status_codes": {},
                "error_count": 0
            }
        
        metrics = self.endpoint_metrics[key]
        metrics["count"] += 1
        metrics["total_duration"] += duration
        metrics["avg_duration"] = metrics["total_duration"] / metrics["count"]
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        
        # Track status codes
        if status_code not in metrics["status_codes"]:
            metrics["status_codes"][status_code] = 0
        metrics["status_codes"][status_code] += 1
        
        # Track errors
        if status_code >= 400:
            metrics["error_count"] += 1
        
        # Keep recent response times for trend analysis
        self.api_response_times.append({
            "endpoint": key,
            "duration": duration,
            "status_code": status_code,
            "timestamp": datetime.utcnow()
        })
        
        # Keep only recent entries (last 10000)
        if len(self.api_response_times) > 10000:
            self.api_response_times = self.api_response_times[-10000:]
    
    def get_api_performance_report(self) -> Dict[str, Any]:
        """Generate API performance report."""
        if not self.endpoint_metrics:
            return {"message": "No API metrics collected yet"}
        
        # Find slowest endpoints
        slowest_endpoints = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1]["avg_duration"],
            reverse=True
        )[:10]
        
        # Find most called endpoints
        most_called = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:10]
        
        # Calculate overall statistics
        total_calls = sum(metrics["count"] for metrics in self.endpoint_metrics.values())
        total_errors = sum(metrics["error_count"] for metrics in self.endpoint_metrics.values())
        error_rate = (total_errors / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "total_api_calls": total_calls,
            "total_errors": total_errors,
            "error_rate_percent": round(error_rate, 2),
            "unique_endpoints": len(self.endpoint_metrics),
            "slowest_endpoints": [
                {
                    "endpoint": endpoint,
                    "avg_duration": metrics["avg_duration"],
                    "max_duration": metrics["max_duration"],
                    "call_count": metrics["count"],
                    "error_rate": (metrics["error_count"] / metrics["count"] * 100)
                }
                for endpoint, metrics in slowest_endpoints
            ],
            "most_called_endpoints": [
                {
                    "endpoint": endpoint,
                    "call_count": metrics["count"],
                    "avg_duration": metrics["avg_duration"],
                    "error_rate": (metrics["error_count"] / metrics["count"] * 100)
                }
                for endpoint, metrics in most_called
            ]
        }


# Global performance metrics instance
performance_metrics = PerformanceMetrics()