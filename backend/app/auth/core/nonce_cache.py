"""Nonce cache for preventing replay attacks."""

import time
from typing import Optional, Set
from threading import Lock
import redis
from collections import OrderedDict

from app.auth.core.signing_config import get_signing_settings


class NonceCache:
    """Base class for nonce cache implementations."""
    
    def add(self, nonce: str, ttl: int) -> bool:
        """Add a nonce to the cache. Returns False if already exists."""
        raise NotImplementedError
    
    def contains(self, nonce: str) -> bool:
        """Check if a nonce exists in the cache."""
        raise NotImplementedError
    
    def cleanup(self):
        """Clean up expired entries."""
        raise NotImplementedError


class InMemoryNonceCache(NonceCache):
    """In-memory nonce cache for single-instance deployments."""
    
    def __init__(self):
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Clean up every minute
    
    def add(self, nonce: str, ttl: int) -> bool:
        """Add a nonce to the cache."""
        with self._lock:
            # Clean up if needed
            if time.time() - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired()
            
            # Check if already exists
            if nonce in self._cache:
                return False
            
            # Add with expiration time
            self._cache[nonce] = time.time() + ttl
            return True
    
    def contains(self, nonce: str) -> bool:
        """Check if a nonce exists in the cache."""
        with self._lock:
            if nonce not in self._cache:
                return False
            
            # Check if expired
            if self._cache[nonce] < time.time():
                del self._cache[nonce]
                return False
            
            return True
    
    def cleanup(self):
        """Clean up expired entries."""
        with self._lock:
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_nonces = []
        
        # Find expired entries
        for nonce, expiry in self._cache.items():
            if expiry < current_time:
                expired_nonces.append(nonce)
            else:
                # OrderedDict maintains insertion order, so we can stop
                # when we find the first non-expired entry
                break
        
        # Remove expired entries
        for nonce in expired_nonces:
            del self._cache[nonce]
        
        self._last_cleanup = current_time


class RedisNonceCache(NonceCache):
    """Redis-based nonce cache for distributed deployments."""
    
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
        self._prefix = "nonce:"
    
    def add(self, nonce: str, ttl: int) -> bool:
        """Add a nonce to the cache."""
        key = f"{self._prefix}{nonce}"
        # SET with NX (only if not exists) and EX (expiration)
        result = self._redis.set(key, "1", nx=True, ex=ttl)
        return bool(result)
    
    def contains(self, nonce: str) -> bool:
        """Check if a nonce exists in the cache."""
        key = f"{self._prefix}{nonce}"
        return bool(self._redis.exists(key))
    
    def cleanup(self):
        """Clean up expired entries."""
        # Redis handles expiration automatically
        pass


# Global nonce cache instance
_nonce_cache: Optional[NonceCache] = None


def get_nonce_cache() -> NonceCache:
    """Get or create nonce cache instance."""
    global _nonce_cache
    
    if _nonce_cache is None:
        settings = get_signing_settings()
        
        # Try to use Redis if available
        try:
            import redis
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            # Test connection
            redis_client.ping()
            _nonce_cache = RedisNonceCache(redis_client)
        except Exception:
            # Fall back to in-memory cache
            _nonce_cache = InMemoryNonceCache()
    
    return _nonce_cache


async def validate_nonce(nonce: str) -> bool:
    """Validate and register a nonce."""
    settings = get_signing_settings()
    
    if not settings.enable_nonce_validation:
        return True
    
    cache = get_nonce_cache()
    
    # Try to add the nonce
    # If it already exists, add() returns False
    return cache.add(nonce, settings.nonce_cache_ttl)