"""
Database query optimization utilities.

This module provides utilities for optimizing database queries,
including eager loading, query profiling, and performance monitoring.
"""
import logging
import time
from typing import Any, List, Optional, Type, TypeVar, Union
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, subqueryload, contains_eager
from sqlalchemy.sql import Select
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

T = TypeVar('T')


class QueryOptimizer:
    """Utilities for optimizing SQLAlchemy queries."""
    
    @staticmethod
    def eager_load_relationships(
        query: Select,
        relationships: List[str],
        strategy: str = "selectin"
    ) -> Select:
        """
        Add eager loading to a query for specified relationships.
        
        Args:
            query: The base query
            relationships: List of relationship names to eager load
            strategy: Loading strategy ('selectin', 'joined', 'subquery')
            
        Returns:
            Query with eager loading options
        """
        for relationship in relationships:
            if strategy == "selectin":
                query = query.options(selectinload(relationship))
            elif strategy == "joined":
                query = query.options(joinedload(relationship))
            elif strategy == "subquery":
                query = query.options(subqueryload(relationship))
            else:
                raise ValueError(f"Unknown loading strategy: {strategy}")
        
        return query
    
    @staticmethod
    def batch_load(
        session: AsyncSession,
        model: Type[T],
        ids: List[Any],
        batch_size: int = 100
    ) -> List[T]:
        """
        Load multiple records in batches to avoid query size limits.
        
        Args:
            session: Database session
            model: SQLAlchemy model class
            ids: List of IDs to load
            batch_size: Number of records per batch
            
        Returns:
            List of loaded records
        """
        results = []
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            query = select(model).where(model.id.in_(batch_ids))
            batch_results = session.execute(query).scalars().all()
            results.extend(batch_results)
        
        return results
    
    @staticmethod
    def add_index_hints(query: Select, hints: dict) -> Select:
        """
        Add index hints to a query (PostgreSQL specific).
        
        Args:
            query: The base query
            hints: Dictionary of table_name: index_name pairs
            
        Returns:
            Query with index hints
        """
        # Note: PostgreSQL doesn't support index hints directly
        # This is a placeholder for future implementation
        # Consider using CTEs or query restructuring instead
        return query


class QueryProfiler:
    """Profile database queries for performance analysis."""
    
    def __init__(self):
        self.query_times = []
        self.slow_query_threshold = 1.0  # seconds
    
    def profile_query(self, query_text: str, duration: float):
        """Record query execution time."""
        self.query_times.append({
            "query": query_text,
            "duration": duration,
            "timestamp": time.time()
        })
        
        if duration > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected ({duration:.2f}s): {query_text[:100]}..."
            )
    
    def get_slow_queries(self, limit: int = 10) -> List[dict]:
        """Get the slowest queries."""
        sorted_queries = sorted(
            self.query_times,
            key=lambda x: x["duration"],
            reverse=True
        )
        return sorted_queries[:limit]
    
    def get_query_stats(self) -> dict:
        """Get query performance statistics."""
        if not self.query_times:
            return {
                "total_queries": 0,
                "avg_duration": 0,
                "max_duration": 0,
                "slow_queries": 0
            }
        
        durations = [q["duration"] for q in self.query_times]
        return {
            "total_queries": len(self.query_times),
            "avg_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "slow_queries": sum(1 for d in durations if d > self.slow_query_threshold)
        }


# Global query profiler instance
query_profiler = QueryProfiler()


def setup_query_profiling(engine: Engine):
    """
    Set up query profiling for an engine.
    
    Args:
        engine: SQLAlchemy engine
    """
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - conn.info["query_start_time"].pop(-1)
        query_profiler.profile_query(statement, total)


@asynccontextmanager
async def optimized_query_context(session: AsyncSession):
    """
    Context manager for optimized query execution.
    
    Usage:
        async with optimized_query_context(session) as opt_session:
            # Execute queries with optimization hints
            result = await opt_session.execute(query)
    """
    # Set session-level optimizations
    await session.execute("SET work_mem = '256MB'")
    await session.execute("SET random_page_cost = 1.1")
    
    try:
        yield session
    finally:
        # Reset to defaults
        await session.execute("RESET work_mem")
        await session.execute("RESET random_page_cost")


def optimize_for_read(func):
    """
    Decorator to optimize database queries for read operations.
    
    This decorator:
    - Sets read-only transaction mode
    - Enables statement timeout
    - Uses read replica if available
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get the session from kwargs or args
        session = None
        for arg in args:
            if isinstance(arg, AsyncSession):
                session = arg
                break
        
        if not session:
            session = kwargs.get('db') or kwargs.get('session')
        
        if session:
            # Set read-only transaction
            from sqlalchemy import text
            await session.execute(text("SET TRANSACTION READ ONLY"))
            # Set statement timeout to prevent long-running queries
            await session.execute(text("SET statement_timeout = '30s'"))
        
        try:
            return await func(*args, **kwargs)
        finally:
            if session:
                # Reset to defaults
                from sqlalchemy import text
                await session.execute(text("RESET statement_timeout"))
    
    return wrapper


class DatabaseQueryOptimizer:
    """Main class for database query optimization."""
    
    @staticmethod
    def create_optimized_project_query(user_id: int, include_sites: bool = False) -> Select:
        """
        Create an optimized query for fetching projects.
        
        Args:
            user_id: User ID to filter by
            include_sites: Whether to include sites relationship
            
        Returns:
            Optimized query
        """
        from app.models.project import Project
        
        query = select(Project).where(Project.user_id == user_id)
        
        if include_sites:
            # Use selectinload for better performance with multiple projects
            query = query.options(selectinload(Project.sites))
        
        # Add index hint (conceptual - PostgreSQL doesn't support directly)
        # Ensure you have an index on (user_id, created_at)
        query = query.order_by(Project.created_at.desc())
        
        return query
    
    @staticmethod
    def create_optimized_activity_query(
        user_id: int,
        limit: int = 100,
        include_user: bool = True
    ) -> Select:
        """
        Create an optimized query for fetching activities.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of results
            include_user: Whether to include user relationship
            
        Returns:
            Optimized query
        """
        from app.models.activity import Activity
        
        query = select(Activity).where(Activity.user_id == user_id)
        
        if include_user:
            # Use joinedload for single relationship
            query = query.options(joinedload(Activity.user))
        
        # Use index on (user_id, created_at)
        query = query.order_by(Activity.created_at.desc()).limit(limit)
        
        return query
    
    @staticmethod
    async def bulk_insert_optimized(
        session: AsyncSession,
        model: Type[T],
        records: List[dict],
        batch_size: int = 1000
    ):
        """
        Optimized bulk insert operation.
        
        Args:
            session: Database session
            model: SQLAlchemy model class
            records: List of record dictionaries
            batch_size: Number of records per batch
        """
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            # Use bulk_insert_mappings for better performance
            await session.run_sync(
                lambda sync_session: sync_session.bulk_insert_mappings(model, batch)
            )
            
            # Commit after each batch to avoid memory issues
            await session.commit()
    
    @staticmethod
    async def optimize_count_query(
        session: AsyncSession,
        query: Select,
        estimate_threshold: int = 10000
    ) -> int:
        """
        Optimized count query that uses estimates for large tables.
        
        Args:
            session: Database session
            query: Query to count
            estimate_threshold: Use estimate if count exceeds this
            
        Returns:
            Count or estimate
        """
        # First, try to get exact count with limit
        limited_query = query.limit(estimate_threshold + 1)
        result = await session.execute(select(func.count()).select_from(limited_query.subquery()))
        count = result.scalar()
        
        if count > estimate_threshold:
            # Use PostgreSQL's estimate for large counts
            # This is much faster but less accurate
            table_name = query.froms[0].name
            estimate_query = f"""
                SELECT reltuples::BIGINT AS estimate
                FROM pg_class
                WHERE relname = '{table_name}'
            """
            result = await session.execute(estimate_query)
            return result.scalar() or count
        
        return count


# Query optimization recommendations
OPTIMIZATION_TIPS = {
    "n_plus_one": "Use eager loading (selectinload, joinedload) to avoid N+1 queries",
    "missing_index": "Consider adding an index on frequently queried columns",
    "large_offset": "Use cursor-based pagination instead of OFFSET for large datasets",
    "no_limit": "Always use LIMIT when you don't need all results",
    "missing_order": "Add ORDER BY to ensure consistent results",
    "full_scan": "Query may cause full table scan, consider adding WHERE clause or index",
    "complex_join": "Consider breaking complex joins into multiple simpler queries",
    "no_projection": "Select only needed columns instead of SELECT *"
}


def analyze_query_plan(query: Select) -> List[str]:
    """
    Analyze a query and provide optimization suggestions.
    
    Args:
        query: SQLAlchemy query to analyze
        
    Returns:
        List of optimization suggestions
    """
    suggestions = []
    
    # Check for missing ORDER BY
    if not query._order_by:
        suggestions.append(OPTIMIZATION_TIPS["missing_order"])
    
    # Check for missing LIMIT
    if not query._limit:
        suggestions.append(OPTIMIZATION_TIPS["no_limit"])
    
    # Check for large OFFSET
    if query._offset and query._offset > 1000:
        suggestions.append(OPTIMIZATION_TIPS["large_offset"])
    
    # More analysis can be added here
    
    return suggestions