"""
Rate limiting utilities for API services.

This module provides reusable rate limiting functionality
for various API integrations.
"""
import asyncio
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_window: int
    window_duration: int  # in seconds
    burst_limit: Optional[int] = None
    retry_after_header: str = "Retry-After"
    rate_limit_header: str = "X-RateLimit-Remaining"


class RateLimiter:
    """Generic rate limiter for API requests."""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.request_count = 0
        self.window_start = time.time()
        self.reset_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self._lock:
            await self._wait_if_needed()
            self._increment_counter()
    
    async def _wait_if_needed(self):
        """Wait if rate limit is exceeded."""
        current_time = time.time()
        
        # Check if we need to wait for reset
        if self.reset_time and current_time < self.reset_time:
            wait_time = self.reset_time - current_time
            logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
            await asyncio.sleep(wait_time)
            self.reset_time = None
            self._reset_window()
        
        # Check if window should be reset
        if current_time - self.window_start >= self.config.window_duration:
            self._reset_window()
        
        # Check if we've hit the limit
        if self.request_count >= self.config.requests_per_window:
            # Calculate wait time until window reset
            wait_time = self.config.window_duration - (current_time - self.window_start)
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds for window reset...")
                await asyncio.sleep(wait_time)
                self._reset_window()
    
    def _increment_counter(self):
        """Increment the request counter."""
        self.request_count += 1
    
    def _reset_window(self):
        """Reset the rate limit window."""
        self.request_count = 0
        self.window_start = time.time()
    
    def update_from_headers(self, headers: Dict[str, str]):
        """
        Update rate limit state from response headers.
        
        Args:
            headers: Response headers
        """
        # Check for retry-after header
        if self.config.retry_after_header in headers:
            try:
                retry_after = int(headers[self.config.retry_after_header])
                self.reset_time = time.time() + retry_after
            except ValueError:
                pass
        
        # Check for remaining requests header
        if self.config.rate_limit_header in headers:
            try:
                remaining = int(headers[self.config.rate_limit_header])
                if remaining == 0:
                    # Set reset time to end of current window if not already set
                    if not self.reset_time:
                        self.reset_time = self.window_start + self.config.window_duration
            except ValueError:
                pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        current_time = time.time()
        time_in_window = current_time - self.window_start
        
        return {
            "requests_made": self.request_count,
            "requests_remaining": max(0, self.config.requests_per_window - self.request_count),
            "window_duration": self.config.window_duration,
            "time_until_reset": max(0, self.config.window_duration - time_in_window),
            "is_limited": self.request_count >= self.config.requests_per_window,
            "reset_time": self.reset_time
        }


class AsyncBatchProcessor:
    """Process items in batches with rate limiting."""
    
    def __init__(
        self,
        batch_size: int = 10,
        rate_limiter: Optional[RateLimiter] = None,
        max_concurrent: int = 5
    ):
        """
        Initialize the batch processor.
        
        Args:
            batch_size: Number of items per batch
            rate_limiter: Optional rate limiter
            max_concurrent: Maximum concurrent operations
        """
        self.batch_size = batch_size
        self.rate_limiter = rate_limiter
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_items(self, items: list, process_func, *args, **kwargs) -> list:
        """
        Process items in batches.
        
        Args:
            items: Items to process
            process_func: Async function to process each item
            *args, **kwargs: Additional arguments for process_func
            
        Returns:
            List of results
        """
        results = []
        
        # Process in batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = await self._process_batch(batch, process_func, *args, **kwargs)
            results.extend(batch_results)
        
        return results
    
    async def _process_batch(self, batch: list, process_func, *args, **kwargs) -> list:
        """Process a single batch of items."""
        tasks = []
        
        for item in batch:
            task = self._process_item_with_limit(item, process_func, *args, **kwargs)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_item_with_limit(self, item, process_func, *args, **kwargs):
        """Process a single item with rate limiting and concurrency control."""
        async with self._semaphore:
            if self.rate_limiter:
                await self.rate_limiter.acquire()
            
            try:
                return await process_func(item, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                return {"error": str(e), "item": item}