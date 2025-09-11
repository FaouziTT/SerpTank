"""
Rate Limiting Dependencies

Provides dependency injection for rate limiting specific endpoints.
This approach allows for more granular control and better error handling.
"""

import time
import logging
from typing import Optional, Dict, Callable
from fastapi import Request, HTTPException, status, Depends
from functools import wraps
import redis.asyncio as redis
import asyncio

logger = logging.getLogger(__name__)

# Global Redis client (will be set during startup)
_redis_client: Optional[redis.Redis] = None

def set_redis_client(client: redis.Redis):
    """Set the global Redis client for rate limiting."""
    global _redis_client
    _redis_client = client

def get_redis_client() -> Optional[redis.Redis]:
    """Get the global Redis client."""
    return _redis_client

class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded."""
    
    def __init__(self, limit: int, window: int, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit of {limit} requests per {window} seconds exceeded.",
                "limit": limit,
                "window": window,
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Window": str(window)
            }
        )

async def check_rate_limit(
    request: Request,
    limit: int,
    window: int = 60,
    key_func: Optional[Callable[[Request], str]] = None
) -> bool:
    """
    Check if request should be rate limited.
    
    Args:
        request: FastAPI request object
        limit: Number of requests allowed in window
        window: Time window in seconds (default: 60)
        key_func: Function to generate unique key for rate limiting
    
    Returns:
        True if request should proceed, raises RateLimitExceeded if not
    """
    redis_client = get_redis_client()
    if not redis_client:
        # If Redis is not available, allow the request (fail-open)
        logger.warning("Redis not available for rate limiting, allowing request")
        return True
    
    # Generate unique key for this client/endpoint
    if key_func:
        rate_key = key_func(request)
    else:
        rate_key = get_default_rate_limit_key(request)
    
    try:
        now = time.time()
        window_start = now - window
        key = f"rate_limit:{rate_key}:{window}"
        
        # Use pipeline for atomic operations
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # Remove expired entries
        pipe.zcard(key)  # Count current entries
        pipe.zadd(key, {str(now): now})  # Add current request
        pipe.expire(key, window + 60)  # Set expiry
        
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count > limit:
            logger.warning(f"Rate limit exceeded for {rate_key}: {current_count}/{limit}")
            # In development, use a shorter retry time
            from app.core.config import settings
            retry_after = 30 if settings.ENVIRONMENT == "development" else window
            raise RateLimitExceeded(limit, window, retry_after)
        
        return True
        
    except RateLimitExceeded:
        raise
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Fail open - allow request if there's an error
        return True

def get_default_rate_limit_key(request: Request) -> str:
    """Generate default rate limiting key from request."""
    # Try to get user ID if authenticated
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return f"user:{user_id}:{request.url.path}"
    
    # Fall back to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"ip:{client_ip}:{request.url.path}"

# Pre-configured rate limiting dependencies for common use cases

async def rate_limit_auth_endpoints(request: Request):
    """Rate limit for authentication endpoints (stricter limits)."""
    # More lenient limits for development
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        await check_rate_limit(request, limit=100, window=60)  # 100 requests per minute in dev
    else:
        await check_rate_limit(request, limit=5, window=60)  # 5 requests per minute in prod

async def rate_limit_general_api(request: Request):
    """Rate limit for general API endpoints."""
    await check_rate_limit(request, limit=60, window=60)  # 60 requests per minute

async def rate_limit_data_intensive(request: Request):
    """Rate limit for data-intensive endpoints."""
    await check_rate_limit(request, limit=10, window=60)  # 10 requests per minute

async def rate_limit_registration(request: Request):
    """Rate limit for user registration (very strict)."""
    # More lenient limits for development
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        await check_rate_limit(request, limit=50, window=60)  # 50 requests per minute in dev
    else:
        await check_rate_limit(request, limit=3, window=300)  # 3 requests per 5 minutes in prod

# Decorator for easy application to route handlers
def rate_limited(limit: int, window: int = 60, key_func: Optional[Callable] = None):
    """
    Decorator to apply rate limiting to route handlers.
    
    Args:
        limit: Number of requests allowed in window
        window: Time window in seconds
        key_func: Optional function to generate rate limit key
    
    Usage:
        @app.post("/api/endpoint")
        @rate_limited(limit=10, window=60)
        async def my_endpoint():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request object in the arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                await check_rate_limit(request, limit, window, key_func)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Dependency factory for custom rate limits
def create_rate_limit_dependency(
    limit: int, 
    window: int = 60,
    key_func: Optional[Callable[[Request], str]] = None
):
    """
    Create a custom rate limiting dependency.
    
    Args:
        limit: Number of requests allowed in window
        window: Time window in seconds
        key_func: Function to generate unique key
    
    Returns:
        Async function that can be used as a FastAPI dependency
    """
    async def rate_limit_dependency(request: Request):
        await check_rate_limit(request, limit, window, key_func)
    
    return rate_limit_dependency

# Helper function to add rate limit headers to responses
def add_rate_limit_headers(response, limit: int, current: int, window: int):
    """Add rate limit headers to response."""
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
    response.headers["X-RateLimit-Window"] = str(window)
    response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))