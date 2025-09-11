"""
Redis Caching Strategy

Implements a comprehensive caching layer for API responses, database queries,
and computed values to improve application performance.
"""

import json
import logging
import pickle
import hashlib
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import redis.asyncio as redis
import asyncio
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Redis-based cache manager with advanced features:
    - Automatic serialization/deserialization
    - TTL management
    - Cache invalidation strategies
    - Performance monitoring
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hour
        self.key_prefix = "voltex:"
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "total_requests": 0
        }
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            # Build Redis URL
            if settings.REDIS_PASSWORD:
                redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB or 0}"
            else:
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB or 0}"
            
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=False,  # We handle encoding ourselves
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=20
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            self.redis_client = None  # Fail gracefully
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self.redis_client is not None
    
    def _make_key(self, key: str) -> str:
        """Create a properly prefixed cache key."""
        return f"{self.key_prefix}{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage."""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode('utf-8')
        else:
            # Use pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis."""
        try:
            # Try JSON first (faster)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_available():
            return None
        
        self.stats["total_requests"] += 1
        
        try:
            cache_key = self._make_key(key)
            data = await self.redis_client.get(cache_key)
            
            if data is None:
                self.stats["misses"] += 1
                return None
            
            self.stats["hits"] += 1
            return self._deserialize_value(data)
            
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            self.stats["errors"] += 1
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache with optional TTL and tags."""
        if not self.is_available():
            return False
        
        try:
            cache_key = self._make_key(key)
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.default_ttl
            
            # Set the main cache entry
            await self.redis_client.setex(cache_key, ttl, serialized_value)
            
            # Set tags for cache invalidation
            if tags:
                await self._set_tags(key, tags, ttl)
            
            # Store metadata
            metadata = {
                "created_at": datetime.utcnow().isoformat(),
                "ttl": ttl,
                "tags": tags or []
            }
            metadata_key = f"{cache_key}:meta"
            await self.redis_client.setex(
                metadata_key, 
                ttl, 
                json.dumps(metadata).encode('utf-8')
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.is_available():
            return False
        
        try:
            cache_key = self._make_key(key)
            result = await self.redis_client.delete(cache_key, f"{cache_key}:meta")
            return result > 0
            
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_by_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not self.is_available():
            return 0
        
        try:
            cache_pattern = self._make_key(pattern)
            keys = await self.redis_client.keys(cache_pattern)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Deleted {deleted} cache keys matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.warning(f"Cache pattern delete error for {pattern}: {e}")
            return 0
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """Delete all cache entries with specified tags."""
        if not self.is_available():
            return 0
        
        deleted_count = 0
        
        try:
            for tag in tags:
                tag_key = self._make_key(f"tag:{tag}")
                tagged_keys = await self.redis_client.smembers(tag_key)
                
                if tagged_keys:
                    # Delete the actual cache entries
                    keys_to_delete = []
                    for tagged_key in tagged_keys:
                        keys_to_delete.append(tagged_key)
                        keys_to_delete.append(f"{tagged_key}:meta")
                    
                    if keys_to_delete:
                        deleted = await self.redis_client.delete(*keys_to_delete)
                        deleted_count += deleted
                    
                    # Clean up the tag set
                    await self.redis_client.delete(tag_key)
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} cache entries with tags: {tags}")
            
            return deleted_count
            
        except Exception as e:
            logger.warning(f"Cache tag delete error for {tags}: {e}")
            return 0
    
    async def _set_tags(self, key: str, tags: List[str], ttl: int):
        """Associate cache key with tags for invalidation."""
        cache_key = self._make_key(key)
        
        for tag in tags:
            tag_key = self._make_key(f"tag:{tag}")
            await self.redis_client.sadd(tag_key, cache_key)
            await self.redis_client.expire(tag_key, ttl)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        hit_rate = 0
        if self.stats["total_requests"] > 0:
            hit_rate = (self.stats["hits"] / self.stats["total_requests"]) * 100
        
        info = {}
        if self.is_available():
            try:
                info = await self.redis_client.info("memory")
            except Exception:
                pass
        
        return {
            "hit_rate": round(hit_rate, 2),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "total_requests": self.stats["total_requests"],
            "redis_memory_used": info.get("used_memory_human", "unknown"),
            "available": self.is_available()
        }
    
    async def clear_all(self) -> bool:
        """Clear all cache entries (use with caution)."""
        if not self.is_available():
            return False
        
        try:
            pattern = self._make_key("*")
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()


# Cache decorators for easy use
def cached(
    ttl: Optional[int] = None,
    key_func: Optional[callable] = None,
    tags: Optional[List[str]] = None,
    condition: Optional[callable] = None
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from arguments
        tags: Tags for cache invalidation
        condition: Function to determine if result should be cached
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                func_name = f"{func.__module__}.{func.__qualname__}"
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"func:{func_name}:{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result if condition is met
            if condition is None or condition(result):
                await cache_manager.set(cache_key, result, ttl, tags)
            
            return result
        
        return wrapper
    return decorator


def cache_key_for_user(user_id: int, suffix: str = "") -> str:
    """Generate cache key for user-specific data."""
    return f"user:{user_id}:{suffix}" if suffix else f"user:{user_id}"


def cache_key_for_org(org_id: str, suffix: str = "") -> str:
    """Generate cache key for organization-specific data."""
    return f"org:{org_id}:{suffix}" if suffix else f"org:{org_id}"


def cache_key_for_project(project_id: int, suffix: str = "") -> str:
    """Generate cache key for project-specific data."""
    return f"project:{project_id}:{suffix}" if suffix else f"project:{project_id}"


# Predefined cache configurations
class CacheConfig:
    """Predefined cache configurations for different data types."""
    
    # API response caching
    API_RESPONSE_TTL = 300  # 5 minutes
    API_RESPONSE_TAGS = ["api_responses"]
    
    # Database query caching
    DB_QUERY_TTL = 1800  # 30 minutes
    DB_QUERY_TAGS = ["db_queries"]
    
    # User data caching
    USER_DATA_TTL = 3600  # 1 hour
    USER_DATA_TAGS = ["user_data"]
    
    # Organization data caching
    ORG_DATA_TTL = 7200  # 2 hours
    ORG_DATA_TAGS = ["org_data"]
    
    # External API responses
    EXTERNAL_API_TTL = 1800  # 30 minutes
    EXTERNAL_API_TAGS = ["external_apis"]
    
    # Analytics data
    ANALYTICS_TTL = 3600  # 1 hour
    ANALYTICS_TAGS = ["analytics"]
    
    # Static data (rarely changes)
    STATIC_DATA_TTL = 86400  # 24 hours
    STATIC_DATA_TAGS = ["static_data"]


# Context manager for cache transactions
@asynccontextmanager
async def cache_transaction():
    """Context manager for cache operations with automatic cleanup on error."""
    keys_to_cleanup = []
    
    try:
        yield keys_to_cleanup
    except Exception as e:
        # Clean up any keys that were set during the failed transaction
        for key in keys_to_cleanup:
            await cache_manager.delete(key)
        raise


# Cache warming functions
async def warm_cache_for_user(user_id: int):
    """Pre-populate cache with frequently accessed user data."""
    logger.info(f"Warming cache for user {user_id}")
    
    # This would be implemented to pre-load common user data
    # Example: user profile, recent projects, etc.
    pass


async def warm_cache_for_org(org_id: str):
    """Pre-populate cache with frequently accessed organization data."""
    logger.info(f"Warming cache for organization {org_id}")
    
    # This would be implemented to pre-load common org data
    # Example: org members, recent activities, etc.
    pass