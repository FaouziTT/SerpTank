"""
Rate Limiting Middleware

Implements rate limiting to protect against brute force attacks and DoS.
Uses Redis for distributed rate limiting with sliding window counters.
"""

import time
import logging
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import redis.asyncio as redis
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Redis-based rate limiter using sliding window counters.
    
    Supports different rate limits for different endpoints and user types.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        window: int,  # window size in seconds
        burst_limit: Optional[int] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if a request should be rate limited.
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP address, user ID)
            limit: Number of requests allowed in the window
            window: Time window in seconds
            burst_limit: Optional burst limit for short-term spikes
        
        Returns:
            Tuple of (is_limited, metadata)
        """
        now = time.time()
        window_start = now - window
        
        # Sliding window key
        window_key = f"rate_limit:{key}:{window}"
        
        try:
            # Pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(window_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(window_key)
            
            # Add current request
            pipe.zadd(window_key, {str(now): now})
            
            # Set expiry for cleanup
            pipe.expire(window_key, window + 60)  # Extra buffer for cleanup
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Check burst limit first (if set)
            if burst_limit and current_count > burst_limit:
                return True, {
                    "limited": True,
                    "reason": "burst_limit_exceeded",
                    "limit": burst_limit,
                    "current": current_count,
                    "window": window,
                    "reset_time": now + window
                }
            
            # Check regular limit
            if current_count > limit:
                return True, {
                    "limited": True,
                    "reason": "rate_limit_exceeded", 
                    "limit": limit,
                    "current": current_count,
                    "window": window,
                    "reset_time": now + window
                }
            
            return False, {
                "limited": False,
                "limit": limit,
                "current": current_count,
                "window": window,
                "remaining": limit - current_count,
                "reset_time": now + window
            }
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open - don't block requests if Redis is down
            return False, {
                "limited": False,
                "error": "rate_limiter_unavailable"
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting requests.
    
    Applies different rate limits based on endpoint patterns and user authentication.
    """
    
    def __init__(
        self,
        app,
        redis_client: redis.Redis,
        default_limits: Dict[str, int] = None,
        endpoint_limits: Dict[str, Dict[str, int]] = None,
        exempt_paths: Optional[set] = None
    ):
        super().__init__(app)
        self.rate_limiter = RateLimiter(redis_client)
        self.default_limits = default_limits or {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "burst_limit": 10
        }
        self.endpoint_limits = endpoint_limits or {
            "/api/v1/auth/login": {
                "requests_per_minute": 5,
                "requests_per_hour": 30,
                "burst_limit": 3
            },
            "/api/v1/auth/register": {
                "requests_per_minute": 3,
                "requests_per_hour": 10,
                "burst_limit": 2
            },
            "/api/v1/auth/refresh": {
                "requests_per_minute": 10,
                "requests_per_hour": 100,
                "burst_limit": 5
            }
        }
        self.exempt_paths = exempt_paths or {
            "/health", "/docs", "/redoc", "/openapi.json"
        }
    
    def get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting (IP + User ID if available)."""
        # Try to get user ID from authentication
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in case of multiple proxies
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def get_limits_for_path(self, path: str) -> Dict[str, int]:
        """Get rate limits for a specific path."""
        # Check exact path matches first
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check prefix matches
        for pattern, limits in self.endpoint_limits.items():
            if path.startswith(pattern):
                return limits
        
        return self.default_limits
    
    def is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Apply rate limiting to requests."""
        
        # Skip rate limiting for exempt paths
        if self.is_exempt_path(request.url.path):
            return await call_next(request)
        
        client_id = self.get_client_identifier(request)
        limits = self.get_limits_for_path(request.url.path)
        
        # Check rate limits
        for limit_type, limit_value in limits.items():
            if limit_type == "burst_limit":
                continue  # Handle separately
            
            window_seconds = 60 if "minute" in limit_type else 3600  # 1 hour
            burst_limit = limits.get("burst_limit")
            
            is_limited, metadata = await self.rate_limiter.is_rate_limited(
                f"{client_id}:{limit_type}",
                limit_value,
                window_seconds,
                burst_limit
            )
            
            if is_limited:
                logger.warning(
                    f"Rate limit exceeded for {client_id} on {request.url.path}: {metadata}"
                )
                
                # Add rate limit headers
                headers = {
                    "X-RateLimit-Limit": str(limit_value),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(metadata.get("reset_time", time.time()))),
                    "X-RateLimit-Window": str(window_seconds),
                    "Retry-After": str(window_seconds)
                }
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Try again in {window_seconds} seconds.",
                        "limit": limit_value,
                        "window": window_seconds,
                        "retry_after": window_seconds
                    },
                    headers=headers
                )
        
        # Request is not rate limited, proceed
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        if hasattr(request.state, 'rate_limit_metadata'):
            metadata = request.state.rate_limit_metadata
            response.headers["X-RateLimit-Limit"] = str(metadata.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(int(metadata.get("reset_time", time.time())))
        
        return response


async def create_redis_rate_limiter() -> redis.Redis:
    """
    Create Redis client for rate limiting.
    
    Returns:
        Redis client configured for rate limiting
    """
    try:
        # Use environment variables for Redis configuration
        import os
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_RATE_LIMIT_DB", "1"))  # Separate DB for rate limiting
        redis_password = os.getenv("REDIS_PASSWORD")
        
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False,  # Keep binary for performance
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Rate limiter Redis connection established")
        return redis_client
        
    except Exception as e:
        logger.error(f"Failed to create Redis rate limiter: {e}")
        # Return a mock client that always allows requests
        return MockRedisClient()


class MockRedisClient:
    """Mock Redis client for when Redis is unavailable (fail-open behavior)."""
    
    async def pipeline(self):
        return MockPipeline()
    
    async def ping(self):
        return True


class MockPipeline:
    """Mock Redis pipeline that simulates no rate limiting."""
    
    def zremrangebyscore(self, *args, **kwargs):
        return self
    
    def zcard(self, *args, **kwargs):
        return self
    
    def zadd(self, *args, **kwargs):
        return self
    
    def expire(self, *args, **kwargs):
        return self
    
    async def execute(self):
        return [None, 0, None, None]  # Simulate empty rate limit data