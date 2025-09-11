"""
Browser caching headers middleware for improved performance.

This module provides middleware to add appropriate cache headers
to API responses for browser caching.
"""
import hashlib
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add browser caching headers to responses."""
    
    # Cache configurations for different endpoint patterns
    CACHE_CONFIGS = {
        # Static assets and rarely changing data
        r"^/api/v1/static/": {
            "max_age": 31536000,  # 1 year
            "public": True,
            "immutable": True
        },
        
        # User profile and settings
        r"^/api/v1/users/profile": {
            "max_age": 300,  # 5 minutes
            "private": True,
            "must_revalidate": True
        },
        
        # Organization data
        r"^/api/v1/organizations/": {
            "max_age": 600,  # 10 minutes
            "private": True,
            "must_revalidate": True
        },
        
        # Analytics and reporting data
        r"^/api/v1/(analytics|reports)/": {
            "max_age": 3600,  # 1 hour
            "private": True,
            "stale_while_revalidate": 600
        },
        
        # SERP and diagnostic data
        r"^/api/v1/(serp|diagnostic)/": {
            "max_age": 1800,  # 30 minutes
            "private": True,
            "stale_while_revalidate": 300
        },
        
        # Health check endpoints
        r"^/api/v1/health": {
            "max_age": 0,
            "no_cache": True,
            "no_store": True
        },
        
        # Auth endpoints - never cache
        r"^/api/v1/auth/": {
            "max_age": 0,
            "no_cache": True,
            "no_store": True,
            "must_revalidate": True
        },
        
        # Default for other GET endpoints
        r"^/api/v1/": {
            "max_age": 60,  # 1 minute
            "private": True,
            "must_revalidate": True
        }
    }
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Add cache headers to the response."""
        response = await call_next(request)
        
        # Only add cache headers for successful GET requests
        if request.method == "GET" and 200 <= response.status_code < 300:
            # Find matching cache config
            cache_config = self._get_cache_config(request.url.path)
            
            if cache_config:
                # Build Cache-Control header
                cache_control_parts = []
                
                if cache_config.get("no_cache"):
                    cache_control_parts.append("no-cache")
                if cache_config.get("no_store"):
                    cache_control_parts.append("no-store")
                if cache_config.get("public"):
                    cache_control_parts.append("public")
                if cache_config.get("private"):
                    cache_control_parts.append("private")
                if cache_config.get("immutable"):
                    cache_control_parts.append("immutable")
                if cache_config.get("must_revalidate"):
                    cache_control_parts.append("must-revalidate")
                
                max_age = cache_config.get("max_age", 0)
                cache_control_parts.append(f"max-age={max_age}")
                
                if "stale_while_revalidate" in cache_config:
                    cache_control_parts.append(
                        f"stale-while-revalidate={cache_config['stale_while_revalidate']}"
                    )
                
                # Set Cache-Control header
                response.headers["Cache-Control"] = ", ".join(cache_control_parts)
                
                # Set Expires header for HTTP/1.0 compatibility
                if max_age > 0:
                    expires = datetime.utcnow() + timedelta(seconds=max_age)
                    response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
                
                # Add ETag if response has content
                if hasattr(response, "body"):
                    etag = self._generate_etag(response.body)
                    response.headers["ETag"] = etag
                
                # Add Vary header for proper caching with auth
                if cache_config.get("private"):
                    response.headers["Vary"] = "Authorization, Accept-Encoding"
                else:
                    response.headers["Vary"] = "Accept-Encoding"
        
        # For non-GET or error responses, prevent caching
        elif response.status_code >= 400:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response
    
    def _get_cache_config(self, path: str) -> Optional[Dict]:
        """Get cache configuration for the given path."""
        import re
        
        for pattern, config in self.CACHE_CONFIGS.items():
            if re.match(pattern, path):
                return config
        
        return None
    
    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag for response content."""
        return f'W/"{hashlib.md5(content).hexdigest()}"'


def add_cache_headers(
    response: Response,
    max_age: int = 60,
    private: bool = True,
    must_revalidate: bool = True,
    stale_while_revalidate: Optional[int] = None
):
    """
    Utility function to add cache headers to a specific response.
    
    Args:
        response: FastAPI response object
        max_age: Maximum age in seconds
        private: Whether the response is private
        must_revalidate: Whether the cache must revalidate
        stale_while_revalidate: Time in seconds for stale-while-revalidate
    """
    cache_control_parts = []
    
    if private:
        cache_control_parts.append("private")
    else:
        cache_control_parts.append("public")
    
    cache_control_parts.append(f"max-age={max_age}")
    
    if must_revalidate:
        cache_control_parts.append("must-revalidate")
    
    if stale_while_revalidate:
        cache_control_parts.append(f"stale-while-revalidate={stale_while_revalidate}")
    
    response.headers["Cache-Control"] = ", ".join(cache_control_parts)
    
    # Add Expires header
    if max_age > 0:
        expires = datetime.utcnow() + timedelta(seconds=max_age)
        response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")


def prevent_cache(response: Response):
    """Prevent caching of a response."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


# Decorator for adding cache headers to specific endpoints
def cache_response(
    max_age: int = 60,
    private: bool = True,
    must_revalidate: bool = True,
    stale_while_revalidate: Optional[int] = None
):
    """
    Decorator to add cache headers to endpoint responses.
    
    Usage:
        @router.get("/data")
        @cache_response(max_age=300, private=True)
        async def get_data():
            return {"data": "value"}
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get the response
            result = await func(*args, **kwargs)
            
            # If result is a Response object, add headers
            if isinstance(result, Response):
                add_cache_headers(
                    result,
                    max_age=max_age,
                    private=private,
                    must_revalidate=must_revalidate,
                    stale_while_revalidate=stale_while_revalidate
                )
            
            return result
        
        return wrapper
    return decorator