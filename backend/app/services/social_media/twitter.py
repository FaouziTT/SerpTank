"""
Twitter/X API Client with rate limiting and error handling.

This module provides integration with Twitter API v2 for fetching
brand mentions, hashtag analytics, and social signals.
"""
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    import tweepy
except ImportError:
    tweepy = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class TwitterClient:
    """Client for Twitter/X API v2 with rate limiting."""
    
    def __init__(self):
        self.bearer_token = getattr(settings, 'TWITTER_BEARER_TOKEN', None)
        self.api_key = getattr(settings, 'TWITTER_API_KEY', None)
        self.api_secret = getattr(settings, 'TWITTER_API_SECRET', None)
        self.access_token = getattr(settings, 'TWITTER_ACCESS_TOKEN', None)
        self.access_token_secret = getattr(settings, 'TWITTER_ACCESS_TOKEN_SECRET', None)
        
        self.client = None
        # Rate limiting variables
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window_start = time.time()
        self.rate_limit_reset_time = None
        self.consecutive_errors = 0
        
        # Rate limiting configuration
        self.requests_per_window = getattr(settings, 'TWITTER_REQUESTS_PER_WINDOW', 75)
        self.window_duration = getattr(settings, 'TWITTER_WINDOW_DURATION', 900)  # 15 minutes
        self.min_request_interval = getattr(settings, 'TWITTER_MIN_REQUEST_INTERVAL', 2)
        self.max_backoff_time = getattr(settings, 'TWITTER_MAX_BACKOFF_TIME', 900)  # 15 minutes
        self.enable_smart_retry = getattr(settings, 'TWITTER_ENABLE_SMART_RETRY', True)
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twitter API client."""
        if not tweepy:
            logger.warning("Tweepy not installed")
            return
        
        try:
            if self.bearer_token:
                self.client = tweepy.Client(bearer_token=self.bearer_token)
                logger.info("Twitter API client initialized successfully")
            else:
                logger.warning("Twitter Bearer Token not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API client: {e}")
    
    def _reset_rate_limit_window(self):
        """Reset the rate limiting window."""
        current_time = time.time()
        if current_time - self.rate_limit_window_start >= self.window_duration:
            self.rate_limit_window_start = current_time
            self.request_count = 0
            logger.info("Twitter rate limit window reset")
    
    def _calculate_backoff_time(self) -> float:
        """Calculate exponential backoff time based on consecutive errors."""
        if self.consecutive_errors == 0:
            return 0
        
        # Exponential backoff: 2^errors seconds, capped at max_backoff_time
        backoff = min(2 ** self.consecutive_errors, self.max_backoff_time)
        return backoff
    
    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        
        # If we have a specific rate limit reset time, wait until then
        if self.rate_limit_reset_time and current_time < self.rate_limit_reset_time:
            wait_time = self.rate_limit_reset_time - current_time
            logger.warning(f"Twitter rate limit active. Waiting {wait_time:.1f} seconds until reset...")
            await asyncio.sleep(wait_time)
            self.rate_limit_reset_time = None
            self._reset_rate_limit_window()
            return
        
        # Reset window if needed
        self._reset_rate_limit_window()
        
        # Check if we're at the request limit
        if self.request_count >= self.requests_per_window:
            wait_time = self.window_duration - (current_time - self.rate_limit_window_start)
            if wait_time > 0:
                logger.warning(f"Twitter rate limit reached. Waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                self._reset_rate_limit_window()
        
        # Ensure minimum interval between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        # Apply exponential backoff if there were recent errors
        backoff_time = self._calculate_backoff_time()
        if backoff_time > 0:
            logger.warning(f"Applying backoff: waiting {backoff_time} seconds due to {self.consecutive_errors} consecutive errors")
            await asyncio.sleep(backoff_time)
    
    async def _make_rate_limited_request(self, request_func, *args, **kwargs):
        """Make a request with rate limiting and error handling."""
        max_retries = 3 if self.enable_smart_retry else 0
        retry_count = 0
        
        while retry_count <= max_retries:
            await self._wait_for_rate_limit()
            
            try:
                # Update request tracking
                self.last_request_time = time.time()
                self.request_count += 1
                
                # Make the request
                result = request_func(*args, **kwargs)
                
                # Reset error count on success
                self.consecutive_errors = 0
                
                return result
                
            except Exception as e:
                self.consecutive_errors += 1
                error_str = str(e)
                
                # Handle specific rate limit errors
                if "429" in error_str or "Too Many Requests" in error_str:
                    logger.warning(f"Twitter rate limit hit (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                    
                    # Try to extract rate limit reset time from error
                    reset_time = None
                    try:
                        # Check if it's a tweepy TooManyRequests exception
                        if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                            reset_header = e.response.headers.get('x-rate-limit-reset')
                            if reset_header:
                                reset_time = int(reset_header)
                                self.rate_limit_reset_time = reset_time
                                logger.info(f"Rate limit resets at timestamp: {reset_time}")
                        
                        # If no reset time found, assume we need to wait the full window
                        if not reset_time:
                            self.rate_limit_reset_time = time.time() + self.window_duration
                            logger.info("No reset time found, waiting full window duration")
                            
                    except Exception as parse_error:
                        logger.warning(f"Could not parse rate limit reset time: {parse_error}")
                        self.rate_limit_reset_time = time.time() + self.window_duration
                    
                    # If smart retry is enabled and we have retries left, continue the loop
                    if self.enable_smart_retry and retry_count < max_retries:
                        retry_count += 1
                        backoff_time = min(30 * (2 ** retry_count), 300)  # Exponential backoff up to 5 min
                        logger.info(f"Retrying in {backoff_time} seconds... (attempt {retry_count + 1}/{max_retries + 1})")
                        await asyncio.sleep(backoff_time)
                        continue
                    
                    # Return a rate-limited response
                    return {
                        'error': 'Rate limit exceeded',
                        'message': f'Twitter API rate limit reached after {retry_count + 1} attempts. The system will automatically retry after the reset time.',
                        'retry_after': int(self.rate_limit_reset_time - time.time()) if self.rate_limit_reset_time else self.window_duration,
                        'rate_limited': True,
                        'reset_time': self.rate_limit_reset_time,
                        'attempts_made': retry_count + 1
                    }
                
                # Handle authentication errors (don't retry)
                elif "401" in error_str or "Unauthorized" in error_str:
                    logger.error(f"Twitter authentication error: {e}")
                    return {
                        'error': 'Authentication failed',
                        'message': 'Twitter API authentication failed. Please check credentials.',
                        'auth_error': True
                    }
                
                # Handle other errors
                else:
                    logger.error(f"Twitter API error (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                    
                    # If smart retry is enabled and we have retries left, continue the loop
                    if self.enable_smart_retry and retry_count < max_retries:
                        retry_count += 1
                        backoff_time = min(5 * (2 ** retry_count), 60)  # Shorter backoff for non-rate-limit errors
                        logger.info(f"Retrying in {backoff_time} seconds... (attempt {retry_count + 1}/{max_retries + 1})")
                        await asyncio.sleep(backoff_time)
                        continue
                    
                    return {
                        'error': 'API error',
                        'message': f'Twitter API error after {retry_count + 1} attempts: {error_str}',
                        'api_error': True,
                        'attempts_made': retry_count + 1
                    }
        
        # This should never be reached, but just in case
        return {
            'error': 'Unknown error',
            'message': 'Request failed for unknown reasons',
            'attempts_made': retry_count + 1
        }
    
    async def search_mentions(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for mentions of a brand or keyword on Twitter with rate limiting.
        
        Args:
            query: Search query (brand name, keyword, hashtag)
            max_results: Maximum number of results (10-100)
            
        Returns:
            Twitter mentions data
        """
        if not self.client:
            return {
                'error': 'Twitter API not configured',
                'mentions': [],
                'total_mentions': 0,
                'message': 'Twitter Bearer Token not provided'
            }
        
        try:
            # Ensure max_results is between 10 and 100
            max_results = max(10, min(max_results, 100))
            
            # Make rate-limited request
            result = await self._make_rate_limited_request(
                self._search_mentions_sync, 
                query, 
                max_results
            )
            
            # Check if result contains an error (rate limit, auth, etc.)
            if isinstance(result, dict) and 'error' in result:
                return {
                    'query': query,
                    'mentions': [],
                    'total_mentions': 0,
                    'fetched_at': datetime.now().isoformat(),
                    **result  # Include error details
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching Twitter mentions: {e}")
            return {
                'error': str(e),
                'mentions': [],
                'total_mentions': 0,
                'query': query,
                'fetched_at': datetime.now().isoformat()
            }
    
    def _search_mentions_sync(self, query: str, max_results: int) -> Dict[str, Any]:
        """Synchronous method to search mentions."""
        tweets = self.client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 100),
            tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations']
        )
        
        mentions = []
        if tweets.data:
            for tweet in tweets.data:
                mentions.append({
                    'tweet_id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'author_id': tweet.author_id,
                    'metrics': {
                        'retweet_count': tweet.public_metrics['retweet_count'],
                        'like_count': tweet.public_metrics['like_count'],
                        'reply_count': tweet.public_metrics['reply_count'],
                        'quote_count': tweet.public_metrics['quote_count']
                    },
                    'url': f'https://twitter.com/twitter/status/{tweet.id}'
                })
        
        return {
            'query': query,
            'mentions': mentions,
            'total_mentions': len(mentions),
            'fetched_at': datetime.now().isoformat()
        }
    
    async def get_hashtag_analytics(
        self,
        hashtag: str,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific hashtag with rate limiting.
        
        Args:
            hashtag: Hashtag to analyze (without #)
            max_results: Maximum number of results
            
        Returns:
            Hashtag analytics data
        """
        if not self.client:
            return {
                'error': 'Twitter API not configured',
                'analytics': {},
                'message': 'Twitter Bearer Token not provided'
            }
        
        try:
            # Add # if not present
            if not hashtag.startswith('#'):
                hashtag = f'#{hashtag}'
            
            # Ensure max_results is between 10 and 100
            max_results = max(10, min(max_results, 100))
            
            # Make rate-limited request
            result = await self._make_rate_limited_request(
                self._get_hashtag_analytics_sync, 
                hashtag, 
                max_results
            )
            
            # Check if result contains an error
            if isinstance(result, dict) and 'error' in result:
                return {
                    'hashtag': hashtag,
                    'analytics': {},
                    'fetched_at': datetime.now().isoformat(),
                    **result  # Include error details
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting hashtag analytics: {e}")
            return {
                'error': str(e),
                'analytics': {},
                'hashtag': hashtag,
                'fetched_at': datetime.now().isoformat()
            }
    
    def _get_hashtag_analytics_sync(self, hashtag: str, max_results: int) -> Dict[str, Any]:
        """Synchronous method to get hashtag analytics."""
        tweets = self.client.search_recent_tweets(
            query=hashtag,
            max_results=min(max_results, 100),
            tweet_fields=['created_at', 'public_metrics']
        )
        
        total_engagement = 0
        total_reach = 0
        tweet_count = 0
        
        if tweets.data:
            for tweet in tweets.data:
                metrics = tweet.public_metrics
                total_engagement += (
                    metrics['like_count'] + 
                    metrics['retweet_count'] + 
                    metrics['reply_count'] + 
                    metrics['quote_count']
                )
                total_reach += metrics['impression_count'] if 'impression_count' in metrics else 0
                tweet_count += 1
        
        avg_engagement = total_engagement / tweet_count if tweet_count > 0 else 0
        
        return {
            'hashtag': hashtag,
            'analytics': {
                'total_tweets': tweet_count,
                'total_engagement': total_engagement,
                'average_engagement': round(avg_engagement, 2),
                'total_reach': total_reach
            },
            'fetched_at': datetime.now().isoformat()
        }