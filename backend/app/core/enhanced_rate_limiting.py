"""
Enhanced Rate Limiting for Security-Critical Endpoints

This module provides specialized rate limiting configurations for high-risk operations
like authentication, account management, and security-sensitive endpoints.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from fastapi import Request, HTTPException, status, Depends
from functools import wraps
from datetime import datetime, timedelta
import redis.asyncio as redis

from app.core.rate_limit_dependencies import (
    check_rate_limit, 
    get_redis_client, 
    get_default_rate_limit_key,
    RateLimitExceeded
)

logger = logging.getLogger(__name__)

class SecurityRateLimitError(HTTPException):
    """Enhanced rate limit error for security-sensitive operations."""
    
    def __init__(self, operation: str, retry_after: int = 300):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "security_rate_limit_exceeded",
                "message": f"Too many {operation} attempts. Account temporarily locked for security.",
                "retry_after": retry_after,
                "security_notice": "Multiple failed attempts detected. If this wasn't you, please contact support."
            },
            headers={
                "Retry-After": str(retry_after),
                "X-Security-Alert": "Rate limit exceeded for security operation"
            }
        )

async def check_progressive_rate_limit(
    request: Request,
    base_key: str,
    limits: Dict[str, tuple],  # {window_name: (limit, window_seconds)}
    operation_name: str = "operation"
) -> bool:
    """
    Check multiple rate limit windows with progressive penalties.
    
    Args:
        request: FastAPI request object
        base_key: Base key for rate limiting
        limits: Dictionary of rate limits with different windows
        operation_name: Human-readable operation name
        
    Returns:
        True if request should proceed
        
    Raises:
        SecurityRateLimitError: If any rate limit is exceeded
    """
    redis_client = get_redis_client()
    if not redis_client:
        logger.warning("Redis not available for progressive rate limiting")
        return True
    
    # Generate client-specific key
    client_key = get_default_rate_limit_key(request)
    
    # Check each window
    for window_name, (limit, window_seconds) in limits.items():
        full_key = f"{base_key}:{client_key}:{window_name}"
        
        try:
            is_limited, metadata = await _check_window_limit(
                redis_client, full_key, limit, window_seconds
            )
            
            if is_limited:
                logger.warning(
                    f"Progressive rate limit exceeded for {operation_name}: "
                    f"{window_name} window ({metadata.get('current', 0)}/{limit})"
                )
                
                # Calculate retry time based on the window
                retry_after = min(window_seconds, 300)  # Max 5 minutes
                raise SecurityRateLimitError(operation_name, retry_after)
                
        except SecurityRateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error checking {window_name} rate limit: {e}")
            # Continue checking other windows
    
    return True

async def _check_window_limit(
    redis_client: redis.Redis,
    key: str, 
    limit: int, 
    window: int
) -> tuple[bool, Dict[str, Any]]:
    """Check rate limit for a specific window."""
    import time
    
    now = time.time()
    window_start = now - window
    
    try:
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window + 60)
        
        results = await pipe.execute()
        current_count = results[1]
        
        return current_count > limit, {
            "limited": current_count > limit,
            "current": current_count,
            "limit": limit,
            "window": window
        }
    except Exception as e:
        logger.error(f"Redis error in rate limiting: {e}")
        return False, {"error": "redis_unavailable"}

# Pre-configured rate limiters for common security operations

async def rate_limit_account_security(request: Request):
    """
    Rate limit for account security operations (password changes, 2FA setup).
    Progressive limits: 5/min, 20/hour, 50/day
    """
    await check_progressive_rate_limit(
        request,
        "account_security",
        {
            "minute": (5, 60),
            "hour": (20, 3600), 
            "day": (50, 86400)
        },
        "account security operations"
    )

async def rate_limit_login_attempts(request: Request):
    """
    Rate limit for login attempts with progressive lockout.
    Very strict limits: 5/min, 15/hour, 30/day
    """
    await check_progressive_rate_limit(
        request,
        "login_attempts",
        {
            "minute": (5, 60),
            "hour": (15, 3600),
            "day": (30, 86400)
        },
        "login attempts"
    )

async def rate_limit_password_operations(request: Request):
    """
    Rate limit for password-related operations.
    Strict limits: 3/5min, 10/hour, 20/day
    """
    await check_progressive_rate_limit(
        request,
        "password_operations",
        {
            "five_minutes": (3, 300),
            "hour": (10, 3600),
            "day": (20, 86400)
        },
        "password operations"
    )

async def rate_limit_data_export(request: Request):
    """
    Rate limit for data export/sensitive data access.
    Conservative limits: 10/hour, 50/day
    """
    await check_progressive_rate_limit(
        request,
        "data_export",
        {
            "hour": (10, 3600),
            "day": (50, 86400)
        },
        "data export operations"
    )

async def rate_limit_api_intensive(request: Request):
    """
    Rate limit for API-intensive operations (analytics, reports).
    Moderate limits: 30/min, 300/hour, 1000/day
    """
    await check_progressive_rate_limit(
        request,
        "api_intensive",
        {
            "minute": (30, 60),
            "hour": (300, 3600),
            "day": (1000, 86400)
        },
        "intensive API operations"
    )

# Enhanced rate limiting decorator
def enhanced_rate_limit(
    limits: Dict[str, tuple], 
    operation_name: str,
    key_prefix: Optional[str] = None
):
    """
    Decorator for enhanced rate limiting with progressive windows.
    
    Args:
        limits: Dictionary of rate limits {window_name: (limit, seconds)}
        operation_name: Human-readable operation name
        key_prefix: Optional prefix for rate limit key
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                key_prefix_final = key_prefix or func.__name__
                await check_progressive_rate_limit(
                    request, 
                    key_prefix_final, 
                    limits, 
                    operation_name
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Suspicious activity tracking
async def track_suspicious_activity(
    request: Request, 
    activity_type: str,
    threshold: int = 10,
    window: int = 3600
):
    """
    Track potentially suspicious activity patterns.
    
    Args:
        request: FastAPI request
        activity_type: Type of suspicious activity
        threshold: Number of events to trigger alert
        window: Time window in seconds
    """
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    client_key = get_default_rate_limit_key(request)
    key = f"suspicious:{activity_type}:{client_key}"
    
    try:
        import time
        now = time.time()
        
        # Add current event
        await redis_client.zadd(key, {str(now): now})
        await redis_client.expire(key, window + 60)
        
        # Clean old entries and count recent ones
        await redis_client.zremrangebyscore(key, 0, now - window)
        count = await redis_client.zcard(key)
        
        if count >= threshold:
            logger.warning(
                f"Suspicious activity detected: {activity_type} "
                f"from {client_key} ({count} events in {window}s)"
            )
            
            # Could trigger additional security measures here
            # like temporary account restrictions or admin alerts
            
    except Exception as e:
        logger.error(f"Error tracking suspicious activity: {e}")

# IP-based rate limiting for public endpoints
async def rate_limit_by_ip_only(request: Request, limit: int = 100, window: int = 3600):
    """
    Rate limit by IP address only (for public endpoints).
    
    Args:
        request: FastAPI request
        limit: Request limit
        window: Time window in seconds
    """
    # Get IP regardless of authentication
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    await check_rate_limit(
        request, 
        limit, 
        window, 
        key_func=lambda req: f"ip_only:{client_ip}"
    )