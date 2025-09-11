"""
Retry utilities for handling transient failures.

This module provides reusable retry functionality with exponential backoff
and configurable retry strategies.
"""
import asyncio
import logging
import random
from typing import TypeVar, Callable, Optional, Type, Tuple, Union, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
            exceptions: Tuple of exceptions to retry on
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.exceptions = exceptions
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        # Add jitter
        if self.jitter:
            delay *= (0.5 + random.random())
        
        return delay


async def retry_async(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    *args,
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        config: Retry configuration
        on_retry: Optional callback called on each retry
        *args, **kwargs: Arguments for the function
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    config = config or RetryConfig()
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.exceptions as e:
            last_exception = e
            
            # Check if this is the last attempt
            if attempt == config.max_attempts - 1:
                logger.error(f"All retry attempts failed for {func.__name__}: {e}")
                raise
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            # Log retry
            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_attempts} for {func.__name__} "
                f"after {delay:.2f}s delay. Error: {e}"
            )
            
            # Call retry callback if provided
            if on_retry:
                try:
                    on_retry(e, attempt)
                except Exception as callback_error:
                    logger.error(f"Error in retry callback: {callback_error}")
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    raise last_exception or Exception("Retry failed with no exception")


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for adding retry functionality to async functions.
    
    Args:
        config: Retry configuration
        on_retry: Optional callback called on each retry
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, config, on_retry, *args, **kwargs)
        return wrapper
    return decorator


class RetryableError(Exception):
    """Base class for retryable errors."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        attempt: Optional[int] = None
    ):
        """
        Initialize retryable error.
        
        Args:
            message: Error message
            retry_after: Suggested retry delay in seconds
            attempt: Current attempt number
        """
        super().__init__(message)
        self.retry_after = retry_after
        self.attempt = attempt


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Original exception: If function fails
        """
        async with self._lock:
            if self.state == "open":
                # Check if we should try recovery
                if self.last_failure_time and \
                   asyncio.get_event_loop().time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                    logger.info(f"Circuit breaker entering half-open state for {func.__name__}")
                else:
                    raise CircuitBreakerOpen(f"Circuit breaker is open for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            async with self._lock:
                if self.state == "half-open":
                    logger.info(f"Circuit breaker closing for {func.__name__}")
                self.failure_count = 0
                self.state = "closed"
            
            return result
            
        except self.expected_exception as e:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = asyncio.get_event_loop().time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(
                        f"Circuit breaker opened for {func.__name__} "
                        f"after {self.failure_count} failures"
                    )
                
                raise
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


def create_retry_config_for_api(
    api_name: str,
    rate_limit_exceptions: Optional[Tuple[Type[Exception], ...]] = None
) -> RetryConfig:
    """
    Create a retry configuration optimized for API calls.
    
    Args:
        api_name: Name of the API for logging
        rate_limit_exceptions: Additional exceptions indicating rate limits
        
    Returns:
        RetryConfig instance
    """
    # Common retryable exceptions for APIs
    retryable_exceptions = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )
    
    # Add rate limit exceptions if provided
    if rate_limit_exceptions:
        retryable_exceptions = retryable_exceptions + rate_limit_exceptions
    
    return RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        exceptions=retryable_exceptions
    )