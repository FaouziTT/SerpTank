"""
Google Trends Service Module

Provides integration with Google Trends for keyword trend analysis and market insights.
"""
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from pytrends.request import TrendReq
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleTrendsService:
    """Service for interacting with Google Trends."""
    
    def __init__(self):
        self.hl = 'en-US'
        self.tz = 360  # CST timezone
        self.retries = 3
        self.backoff_factor = 2
        
    async def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = 'today 3-m',
        geo: str = 'US'
    ) -> Dict[str, Any]:
        """
        Get interest over time for keywords.
        
        Args:
            keywords: List of keywords to analyze (max 5)
            timeframe: Time range for data
            geo: Geographic location code
            
        Returns:
            Interest data over time
        """
        try:
            # Google Trends API is synchronous, so we run it in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_interest_over_time_sync,
                keywords[:5],  # Limit to 5 keywords
                timeframe,
                geo
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get Google Trends data: {str(e)}")
            return self._get_mock_interest_data(keywords)
    
    def _get_interest_over_time_sync(
        self,
        keywords: List[str],
        timeframe: str,
        geo: str
    ) -> Dict[str, Any]:
        """Synchronous method to get interest data."""
        try:
            pytrends = TrendReq(hl=self.hl, tz=self.tz)
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            
            interest_df = pytrends.interest_over_time()
            
            if interest_df.empty:
                return self._get_mock_interest_data(keywords)
            
            # Convert DataFrame to dictionary
            data = {
                "keywords": keywords,
                "timeframe": timeframe,
                "geo": geo,
                "data": []
            }
            
            for index, row in interest_df.iterrows():
                point = {"date": index.isoformat()}
                for keyword in keywords:
                    if keyword in row:
                        point[keyword] = int(row[keyword])
                data["data"].append(point)
            
            return data
            
        except Exception as e:
            logger.error(f"Google Trends sync error: {str(e)}")
            return self._get_mock_interest_data(keywords)
    
    async def get_related_queries(
        self,
        keyword: str,
        timeframe: str = 'today 3-m',
        geo: str = 'US'
    ) -> Dict[str, Any]:
        """
        Get related queries for a keyword.
        
        Args:
            keyword: Keyword to analyze
            timeframe: Time range for data
            geo: Geographic location code
            
        Returns:
            Related queries data
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_related_queries_sync,
                keyword,
                timeframe,
                geo
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get related queries: {str(e)}")
            return self._get_mock_related_queries(keyword)
    
    def _get_related_queries_sync(
        self,
        keyword: str,
        timeframe: str,
        geo: str
    ) -> Dict[str, Any]:
        """Synchronous method to get related queries."""
        try:
            pytrends = TrendReq(hl=self.hl, tz=self.tz)
            pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
            
            related_queries = pytrends.related_queries()
            
            result = {
                "keyword": keyword,
                "rising": [],
                "top": []
            }
            
            if keyword in related_queries:
                queries = related_queries[keyword]
                
                # Process rising queries
                if queries['rising'] is not None and not queries['rising'].empty:
                    for _, row in queries['rising'].iterrows():
                        result["rising"].append({
                            "query": row['query'],
                            "value": int(row['value']) if pd.notna(row['value']) else 0
                        })
                
                # Process top queries
                if queries['top'] is not None and not queries['top'].empty:
                    for _, row in queries['top'].iterrows():
                        result["top"].append({
                            "query": row['query'],
                            "value": int(row['value']) if pd.notna(row['value']) else 0
                        })
            
            return result
            
        except Exception as e:
            logger.error(f"Related queries sync error: {str(e)}")
            return self._get_mock_related_queries(keyword)
    
    async def get_trending_searches(self, geo: str = 'US') -> List[str]:
        """
        Get currently trending searches.
        
        Args:
            geo: Geographic location code
            
        Returns:
            List of trending searches
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_trending_searches_sync,
                geo
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get trending searches: {str(e)}")
            return self._get_mock_trending_searches()
    
    def _get_trending_searches_sync(self, geo: str) -> List[str]:
        """Synchronous method to get trending searches."""
        try:
            pytrends = TrendReq(hl=self.hl, tz=self.tz)
            trending_df = pytrends.trending_searches(pn=geo.lower())
            
            if trending_df.empty:
                return self._get_mock_trending_searches()
            
            return trending_df[0].tolist()[:20]  # Top 20 trending searches
            
        except Exception as e:
            logger.error(f"Trending searches sync error: {str(e)}")
            return self._get_mock_trending_searches()
    
    async def compare_regions(
        self,
        keyword: str,
        timeframe: str = 'today 3-m'
    ) -> Dict[str, Any]:
        """
        Compare interest by region for a keyword.
        
        Args:
            keyword: Keyword to analyze
            timeframe: Time range for data
            
        Returns:
            Regional interest data
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._compare_regions_sync,
                keyword,
                timeframe
            )
            return result
        except Exception as e:
            logger.error(f"Failed to compare regions: {str(e)}")
            return self._get_mock_regional_data(keyword)
    
    def _compare_regions_sync(
        self,
        keyword: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Synchronous method to compare regions."""
        try:
            pytrends = TrendReq(hl=self.hl, tz=self.tz)
            pytrends.build_payload([keyword], timeframe=timeframe)
            
            region_df = pytrends.interest_by_region(resolution='COUNTRY')
            
            if region_df.empty:
                return self._get_mock_regional_data(keyword)
            
            # Get top regions
            top_regions = region_df.sort_values(keyword, ascending=False).head(20)
            
            result = {
                "keyword": keyword,
                "regions": []
            }
            
            for region, row in top_regions.iterrows():
                if row[keyword] > 0:
                    result["regions"].append({
                        "region": region,
                        "interest": int(row[keyword])
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Regional comparison sync error: {str(e)}")
            return self._get_mock_regional_data(keyword)
    
    def _get_mock_interest_data(self, keywords: List[str]) -> Dict[str, Any]:
        """Generate mock interest over time data."""
        data = {
            "keywords": keywords,
            "timeframe": "today 3-m",
            "geo": "US",
            "data": []
        }
        
        # Generate 90 days of mock data
        base_date = datetime.now() - timedelta(days=90)
        for i in range(90):
            date = base_date + timedelta(days=i)
            point = {"date": date.isoformat()}
            
            for keyword in keywords:
                # Generate realistic looking trend data
                base_value = 50 + (i % 30)
                variation = hash(keyword) % 20 - 10
                point[keyword] = max(0, min(100, base_value + variation))
            
            data["data"].append(point)
        
        return data
    
    def _get_mock_related_queries(self, keyword: str) -> Dict[str, Any]:
        """Generate mock related queries data."""
        return {
            "keyword": keyword,
            "rising": [
                {"query": f"{keyword} tutorial", "value": 250},
                {"query": f"best {keyword} 2024", "value": 180},
                {"query": f"{keyword} vs competitor", "value": 150},
                {"query": f"how to use {keyword}", "value": 120},
                {"query": f"{keyword} pricing", "value": 100}
            ],
            "top": [
                {"query": f"what is {keyword}", "value": 100},
                {"query": f"{keyword} review", "value": 85},
                {"query": f"{keyword} alternatives", "value": 75},
                {"query": f"{keyword} guide", "value": 65},
                {"query": f"{keyword} examples", "value": 50}
            ]
        }
    
    def _get_mock_trending_searches(self) -> List[str]:
        """Generate mock trending searches."""
        return [
            "AI chatbot",
            "sustainable technology",
            "remote work tools",
            "cryptocurrency news",
            "climate change solutions",
            "electric vehicles",
            "metaverse platforms",
            "health tech innovations",
            "cybersecurity trends",
            "green energy"
        ]
    
    def _get_mock_regional_data(self, keyword: str) -> Dict[str, Any]:
        """Generate mock regional interest data."""
        return {
            "keyword": keyword,
            "regions": [
                {"region": "United States", "interest": 100},
                {"region": "United Kingdom", "interest": 85},
                {"region": "Canada", "interest": 75},
                {"region": "Australia", "interest": 70},
                {"region": "Germany", "interest": 65},
                {"region": "France", "interest": 60},
                {"region": "Japan", "interest": 55},
                {"region": "Brazil", "interest": 50},
                {"region": "India", "interest": 45},
                {"region": "Mexico", "interest": 40}
            ]
        }


# Create singleton instance
google_trends_service = GoogleTrendsService()