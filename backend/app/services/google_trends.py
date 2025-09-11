"""
Google Trends API Integration.

This module provides integration with Google Trends API to fetch
keyword trend data, seasonal patterns, and related queries.
"""
import logging
import asyncio
import time
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)


class GoogleTrendsClient:
    """Client for Google Trends API with 2025-compliant rate limiting."""
    
    def __init__(self):
        # 2025-compliant configuration with proper rate limiting
        self.pytrends = TrendReq(
            hl='en-US', 
            tz=360,
            timeout=(10, 25),
            retries=3,
            backoff_factor=2
        )
        self.last_request_time = 0
        self.min_request_interval = 65  # 65 seconds between requests to avoid 400 errors
    
    async def get_keyword_trends(
        self,
        keywords: List[str],
        timeframe: str = 'today 12-m',
        geo: str = 'US'
    ) -> Dict[str, Any]:
        """
        Get keyword trend data over time.
        
        Args:
            keywords: List of keywords to analyze (max 5)
            timeframe: Time period ('today 5-y', 'today 12-m', 'today 3-m', etc.)
            geo: Geographic location code ('US', 'GB', 'CA', etc.)
            
        Returns:
            Keyword trend data
        """
        try:
            # Limit to 5 keywords as per Google Trends API
            keywords = keywords[:5]
            
            # Run in thread pool since pytrends is synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_trends_data, 
                keywords, 
                timeframe, 
                geo
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting keyword trends: {e}")
            raise Exception(f"Failed to get keyword trends: {e}")
    
    def _get_trends_data(self, keywords: List[str], timeframe: str, geo: str) -> Dict[str, Any]:
        """Synchronous method to get trends data with rate limiting."""
        # Implement rate limiting to avoid 400 errors
        self._wait_for_rate_limit()
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop='')
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                # Wait longer between retries (exponential backoff)
                wait_time = (2 ** attempt) * 30 + random.uniform(10, 30)
                logger.warning(f"Request failed (attempt {attempt + 1}), waiting {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
        
        # Get interest over time with error handling
        try:
            interest_over_time = self.pytrends.interest_over_time()
        except Exception as e:
            logger.error(f"Failed to get interest over time: {e}")
            # Return empty structure on failure
            return {
                'keywords': keywords,
                'timeframe': timeframe,
                'geo': geo,
                'trends': {},
                'fetched_at': datetime.now().isoformat(),
                'error': str(e)
            }
        
        # Convert to dict format
        trends_data = {}
        if not interest_over_time.empty:
            for keyword in keywords:
                if keyword in interest_over_time.columns:
                    trends_data[keyword] = {
                        'data': interest_over_time[keyword].to_list(),
                        'dates': interest_over_time.index.strftime('%Y-%m-%d').to_list(),
                        'max_value': int(interest_over_time[keyword].max()),
                        'avg_value': round(interest_over_time[keyword].mean(), 1),
                        'trend_direction': self._calculate_trend_direction(interest_over_time[keyword])
                    }
        
        return {
            'keywords': keywords,
            'timeframe': timeframe,
            'geo': geo,
            'trends': trends_data,
            'fetched_at': datetime.now().isoformat()
        }
    
    def _calculate_trend_direction(self, series: pd.Series) -> str:
        """Calculate if trend is increasing, decreasing, or stable."""
        if len(series) < 2:
            return 'stable'
        
        # Compare last 30% of data with first 30%
        split_point = max(1, len(series) // 3)
        early_avg = series[:split_point].mean()
        recent_avg = series[-split_point:].mean()
        
        if recent_avg > early_avg * 1.1:
            return 'increasing'
        elif recent_avg < early_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    async def get_related_queries(
        self,
        keyword: str,
        timeframe: str = 'today 12-m',
        geo: str = 'US'
    ) -> Dict[str, Any]:
        """
        Get related queries for a keyword.
        
        Args:
            keyword: Keyword to analyze
            timeframe: Time period
            geo: Geographic location code
            
        Returns:
            Related queries data
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_related_queries_data, 
                keyword, 
                timeframe, 
                geo
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting related queries: {e}")
            raise Exception(f"Failed to get related queries: {e}")
    
    def _get_related_queries_data(self, keyword: str, timeframe: str, geo: str) -> Dict[str, Any]:
        """Synchronous method to get related queries with rate limiting."""
        self._wait_for_rate_limit()
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo, gprop='')
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = (2 ** attempt) * 30 + random.uniform(10, 30)
                logger.warning(f"Request failed (attempt {attempt + 1}), waiting {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
        
        # Get related queries
        related_queries = self.pytrends.related_queries()
        
        result = {
            'keyword': keyword,
            'timeframe': timeframe,
            'geo': geo,
            'related_queries': {
                'top': [],
                'rising': []
            },
            'fetched_at': datetime.now().isoformat()
        }
        
        if keyword in related_queries:
            keyword_data = related_queries[keyword]
            
            # Top related queries
            if keyword_data['top'] is not None:
                result['related_queries']['top'] = [
                    {
                        'query': row['query'],
                        'value': int(row['value'])
                    }
                    for _, row in keyword_data['top'].head(10).iterrows()
                ]
            
            # Rising related queries
            if keyword_data['rising'] is not None:
                result['related_queries']['rising'] = [
                    {
                        'query': row['query'],
                        'value': row['value']  # Can be percentage or 'Breakout'
                    }
                    for _, row in keyword_data['rising'].head(10).iterrows()
                ]
        
        return result
    
    async def get_regional_interest(
        self,
        keyword: str,
        timeframe: str = 'today 12-m'
    ) -> Dict[str, Any]:
        """
        Get regional interest for a keyword.
        
        Args:
            keyword: Keyword to analyze
            timeframe: Time period
            
        Returns:
            Regional interest data
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_regional_interest_data, 
                keyword, 
                timeframe
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting regional interest: {e}")
            raise Exception(f"Failed to get regional interest: {e}")
    
    def _get_regional_interest_data(self, keyword: str, timeframe: str) -> Dict[str, Any]:
        """Synchronous method to get regional interest with rate limiting."""
        self._wait_for_rate_limit()
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo='', gprop='')
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = (2 ** attempt) * 30 + random.uniform(10, 30)
                logger.warning(f"Request failed (attempt {attempt + 1}), waiting {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
        
        # Get interest by region
        interest_by_region = self.pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True, inc_geo_code=False)
        
        regions = []
        if not interest_by_region.empty and keyword in interest_by_region.columns:
            # Get top 20 regions
            sorted_regions = interest_by_region[keyword].sort_values(ascending=False).head(20)
            regions = [
                {
                    'region': region,
                    'interest': int(value)
                }
                for region, value in sorted_regions.items()
                if value > 0
            ]
        
        return {
            'keyword': keyword,
            'timeframe': timeframe,
            'regions': regions,
            'fetched_at': datetime.now().isoformat()
        }
    
    async def get_seasonal_patterns(
        self,
        keyword: str,
        years_back: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze seasonal patterns for a keyword.
        
        Args:
            keyword: Keyword to analyze
            years_back: Number of years of data to analyze
            
        Returns:
            Seasonal pattern analysis
        """
        try:
            timeframe = f'today {years_back}-y'
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._get_seasonal_patterns_data, 
                keyword, 
                timeframe
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting seasonal patterns: {e}")
            raise Exception(f"Failed to get seasonal patterns: {e}")
    
    def _get_seasonal_patterns_data(self, keyword: str, timeframe: str) -> Dict[str, Any]:
        """Synchronous method to analyze seasonal patterns with rate limiting."""
        self._wait_for_rate_limit()
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo='US', gprop='')
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = (2 ** attempt) * 30 + random.uniform(10, 30)
                logger.warning(f"Request failed (attempt {attempt + 1}), waiting {wait_time:.1f}s: {e}")
                time.sleep(wait_time)
        
        # Get interest over time
        interest_over_time = self.pytrends.interest_over_time()
        
        if interest_over_time.empty or keyword not in interest_over_time.columns:
            return {
                'keyword': keyword,
                'seasonal_patterns': [],
                'peak_months': [],
                'low_months': [],
                'fetched_at': datetime.now().isoformat()
            }
        
        # Add month column for analysis
        interest_over_time['month'] = interest_over_time.index.month
        
        # Calculate monthly averages
        monthly_avg = interest_over_time.groupby('month')[keyword].mean()
        
        # Identify peak and low months
        peak_months = monthly_avg.nlargest(3).index.tolist()
        low_months = monthly_avg.nsmallest(3).index.tolist()
        
        # Convert month numbers to names
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        
        seasonal_patterns = [
            {
                'month': month_names[month],
                'month_number': int(month),
                'average_interest': round(avg_interest, 1)
            }
            for month, avg_interest in monthly_avg.items()
        ]
        
        return {
            'keyword': keyword,
            'timeframe': timeframe,
            'seasonal_patterns': seasonal_patterns,
            'peak_months': [month_names[m] for m in peak_months],
            'low_months': [month_names[m] for m in low_months],
            'fetched_at': datetime.now().isoformat()
        }
    
    def _wait_for_rate_limit(self):
        """Wait to respect rate limits (65+ seconds between requests)."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            # Add some jitter to avoid thundering herd
            wait_time += random.uniform(5, 15)
            logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds before next request")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()


# Create singleton instance
google_trends_client = GoogleTrendsClient()

# Export alias for compatibility
trends_client = google_trends_client
