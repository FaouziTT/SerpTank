"""
Shared utilities package for services.

This package provides reusable functionality for various services including:
- Rate limiting
- Caching
- Retry logic with exponential backoff
- Validation utilities
"""

from .rate_limiter import RateLimiter, RateLimitConfig, AsyncBatchProcessor
from .caching import CacheManager, InMemoryCache, create_cache_key_builder
from .retry import (
    RetryConfig,
    retry_async,
    with_retry,
    RetryableError,
    CircuitBreaker,
    CircuitBreakerOpen,
    create_retry_config_for_api
)
from .validation import (
    URLValidator,
    EmailValidator,
    TextValidator,
    KeywordValidator,
    validate_api_response
)

__all__ = [
    # Rate limiting
    'RateLimiter',
    'RateLimitConfig',
    'AsyncBatchProcessor',
    
    # Caching
    'CacheManager',
    'InMemoryCache',
    'create_cache_key_builder',
    
    # Retry
    'RetryConfig',
    'retry_async',
    'with_retry',
    'RetryableError',
    'CircuitBreaker',
    'CircuitBreakerOpen',
    'create_retry_config_for_api',
    
    # Validation
    'URLValidator',
    'EmailValidator',
    'TextValidator',
    'KeywordValidator',
    'validate_api_response'
]