"""
Enhanced Database Connection Manager

This module provides advanced database connection management with:
- Connection retry logic
- Connection health monitoring
- Performance metrics
- Automatic reconnection on failure
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Dict, Any
from contextlib import asynccontextmanager
import time

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text, pool, event
from sqlalchemy.exc import DBAPIError, SQLAlchemyError, OperationalError
from sqlalchemy.pool import Pool

from app.db.session import async_session_factory, engine
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionMetrics:
    """Track database connection metrics"""
    def __init__(self):
        self.total_connections = 0
        self.active_connections = 0
        self.failed_connections = 0
        self.connection_wait_time = []
        self.query_execution_time = []
        self.last_error: Optional[Dict[str, Any]] = None
        self.start_time = datetime.now(timezone.utc)
    
    def record_connection(self, wait_time: float):
        """Record a new connection"""
        self.total_connections += 1
        self.active_connections += 1
        self.connection_wait_time.append(wait_time)
        # Keep only last 1000 measurements
        if len(self.connection_wait_time) > 1000:
            self.connection_wait_time.pop(0)
    
    def record_disconnection(self):
        """Record a disconnection"""
        self.active_connections = max(0, self.active_connections - 1)
    
    def record_failure(self, error: Exception):
        """Record a connection failure"""
        self.failed_connections += 1
        self.last_error = {
            "error": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def record_query_time(self, execution_time: float):
        """Record query execution time"""
        self.query_execution_time.append(execution_time)
        # Keep only last 1000 measurements
        if len(self.query_execution_time) > 1000:
            self.query_execution_time.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current connection statistics"""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        avg_wait_time = sum(self.connection_wait_time) / len(self.connection_wait_time) if self.connection_wait_time else 0
        avg_query_time = sum(self.query_execution_time) / len(self.query_execution_time) if self.query_execution_time else 0
        
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "failed_connections": self.failed_connections,
            "failure_rate": self.failed_connections / max(1, self.total_connections),
            "avg_connection_wait_ms": round(avg_wait_time * 1000, 2),
            "avg_query_time_ms": round(avg_query_time * 1000, 2),
            "last_error": self.last_error,
            "uptime_seconds": round(uptime, 2)
        }


class DatabaseConnectionManager:
    """Enhanced database connection manager with retry logic and monitoring"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.metrics = ConnectionMetrics()
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring"""
        # Monitor connection checkout
        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            connection_record.info['checkout_time'] = time.time()
        
        # Monitor connection checkin
        @event.listens_for(Pool, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            if 'checkout_time' in connection_record.info:
                checkout_time = connection_record.info.pop('checkout_time')
                self.metrics.record_query_time(time.time() - checkout_time)
    
    async def get_session_with_retry(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic retry on failure
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            SQLAlchemyError: After all retries are exhausted
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                async with async_session_factory() as session:
                    # Test the connection
                    await session.execute(text("SELECT 1"))
                    
                    wait_time = time.time() - start_time
                    self.metrics.record_connection(wait_time)
                    
                    try:
                        yield session
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
                    finally:
                        self.metrics.record_disconnection()
                
                return  # Success, exit the retry loop
                
            except (OperationalError, DBAPIError) as e:
                last_error = e
                self.metrics.record_failure(e)
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Database connection failed (attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time}s... Error: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All database connection attempts failed. Last error: {str(e)}")
                    raise
            
            except Exception as e:
                # Non-retryable error
                self.metrics.record_failure(e)
                logger.error(f"Non-retryable database error: {str(e)}")
                raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a database health check
        
        Returns:
            Dict containing health status and metrics
        """
        try:
            start_time = time.time()
            async with async_session_factory() as session:
                # Basic connectivity test
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                
                # Check pool status
                pool_status = {
                    "size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
                    "checked_in": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else None,
                    "checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else None,
                    "overflow": engine.pool.overflow() if hasattr(engine.pool, 'overflow') else None,
                    "total": engine.pool.total() if hasattr(engine.pool, 'total') else None,
                }
                
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "pool_status": pool_status,
                "metrics": self.metrics.get_stats(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "metrics": self.metrics.get_stats(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @asynccontextmanager
    async def transaction_with_retry(self):
        """
        Create a transactional context with retry logic
        
        Usage:
            async with db_manager.transaction_with_retry() as session:
                # Your database operations here
                pass
        """
        async with self.get_session_with_retry() as session:
            async with session.begin():
                yield session


# Global instance
db_manager = DatabaseConnectionManager(
    max_retries=getattr(settings, "DB_CONNECTION_RETRIES", 3),
    retry_delay=getattr(settings, "DB_RETRY_DELAY", 1.0)
)


# Enhanced dependency for FastAPI
async def get_db_with_retry() -> AsyncGenerator[AsyncSession, None]:
    """
    Enhanced database session dependency with retry logic
    
    Yields:
        AsyncSession: Database session with automatic retry
    """
    async with db_manager.get_session_with_retry() as session:
        yield session