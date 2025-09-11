"""
Caching utilities for services.

This module provides reusable caching functionality for various services,
including in-memory caching and cache key generation.
"""
import hashlib
import json
import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
import asyncio

from aiocache import Cache
from aiocache.serializers import JsonSerializer


class CacheManager:
    """Manages caching operations for services."""
    
    def __init__(
        self,
        ttl: int = 3600,
        namespace: str = "default",
        cache_backend: str = "memory"
    ):
        """
        Initialize the cache manager.
        
        Args:
            ttl: Default time-to-live in seconds
            namespace: Cache namespace
            cache_backend: Cache backend type (memory, redis, etc.)
        """
        self.ttl = ttl
        self.namespace = namespace
        self.cache = Cache(
            cache_backend,
            ttl=ttl,
            namespace=namespace,
            serializer=JsonSerializer()
        )
    
    def generate_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a cache key from prefix and parameters.
        
        Args:
            prefix: Key prefix
            **kwargs: Parameters to include in key
            
        Returns:
            Cache key string
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        
        # Create hash of parameters
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        
        # Construct key
        return f"{self.namespace}:{prefix}:{param_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            return await self.cache.get(key)
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (overrides default)
            
        Returns:
            Success status
        """
        try:
            return await self.cache.set(key, value, ttl=ttl or self.ttl)
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            return await self.cache.delete(key)
        except Exception:
            return False
    
    async def clear_namespace(self) -> bool:
        """Clear all keys in the namespace."""
        try:
            return await self.cache.clear(namespace=self.namespace)
        except Exception:
            return False
    
    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable] = None
    ):
        """
        Decorator for caching function results.
        
        Args:
            key_prefix: Prefix for cache keys
            ttl: Time-to-live for cached results
            key_builder: Custom function to build cache keys
            
        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(key_prefix, *args, **kwargs)
                else:
                    # Default key builder using function arguments
                    cache_key = self.generate_key(
                        key_prefix,
                        args=str(args),
                        kwargs=str(kwargs)
                    )
                
                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl=ttl)
                
                return result
            
            return wrapper
        return decorator


class InMemoryCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the in-memory cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry['expires_at'] > time.time():
                    return entry['value']
                else:
                    # Remove expired entry
                    del self.cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        async with self._lock:
            expires_at = time.time() + (ttl or self.default_ttl)
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
            return True
    
    async def cleanup_expired(self):
        """Remove all expired entries."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry['expires_at'] <= current_time
            ]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = sum(
            1 for entry in self.cache.values()
            if entry['expires_at'] > current_time
        )
        
        return {
            "total_entries": len(self.cache),
            "active_entries": active_entries,
            "expired_entries": len(self.cache) - active_entries
        }


def create_cache_key_builder(include_user: bool = True, include_org: bool = False):
    """
    Create a cache key builder function.
    
    Args:
        include_user: Include user ID in cache key
        include_org: Include organization ID in cache key
        
    Returns:
        Cache key builder function
    """
    def key_builder(prefix: str, *args, **kwargs):
        """Build cache key from function arguments."""
        key_parts = [prefix]
        
        # Extract user/org info if available
        if include_user and 'current_user' in kwargs:
            user = kwargs['current_user']
            key_parts.append(f"user:{user.id}")
        
        if include_org and 'current_user' in kwargs:
            user = kwargs['current_user']
            if hasattr(user, 'organization_id'):
                key_parts.append(f"org:{user.organization_id}")
        
        # Add other relevant kwargs
        relevant_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ['current_user', 'db', 'background_tasks']
        }
        
        if relevant_kwargs:
            param_str = json.dumps(relevant_kwargs, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        
        return ":".join(key_parts)
    
    return key_builder