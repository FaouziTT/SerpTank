"""
SerpAPI Service Module

Provides integration with SerpAPI for search engine results and competitor analysis.
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import asyncio
from urllib.parse import urlencode

from app.core.config import settings

logger = logging.getLogger(__name__)


class SerpAPIService:
    """Service for interacting with SerpAPI."""
    
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY", "")
        self.base_url = "https://serpapi.com/search"
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    async def search_google(
        self,
        query: str,
        location: str = "United States",
        num: int = 10,
        device: str = "desktop"
    ) -> Dict[str, Any]:
        """
        Perform a Google search using SerpAPI.
        
        Args:
            query: Search query
            location: Geographic location for search
            num: Number of results to return
            device: Device type (desktop/mobile)
            
        Returns:
            Search results from SerpAPI
        """
        if not self.api_key:
            logger.warning("SerpAPI key not configured, returning mock data")
            return self._get_mock_search_results(query)
            
        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "location": location,
            "num": num,
            "device": device,
            "output": "json"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}?{urlencode(params)}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"SerpAPI request failed with status {response.status}")
                        return self._get_mock_search_results(query)
                        
        except asyncio.TimeoutError:
            logger.error("SerpAPI request timed out")
            return self._get_mock_search_results(query)
        except Exception as e:
            logger.error(f"SerpAPI request failed: {str(e)}")
            return self._get_mock_search_results(query)
    
    async def get_competitor_rankings(
        self,
        keywords: List[str],
        domain: str,
        competitors: List[str]
    ) -> Dict[str, Any]:
        """
        Get ranking data for competitors on specific keywords.
        
        Args:
            keywords: List of keywords to check
            domain: Your domain
            competitors: List of competitor domains
            
        Returns:
            Ranking data for all domains
        """
        rankings = {}
        
        for keyword in keywords[:5]:  # Limit to avoid rate limits
            await asyncio.sleep(1)  # Rate limiting
            
            results = await self.search_google(keyword, num=20)
            
            # Extract rankings from results
            organic_results = results.get("organic_results", [])
            
            for idx, result in enumerate(organic_results, 1):
                link = result.get("link", "")
                
                # Check if it's our domain
                if domain in link:
                    if domain not in rankings:
                        rankings[domain] = {}
                    rankings[domain][keyword] = idx
                    
                # Check competitors
                for competitor in competitors:
                    if competitor in link:
                        if competitor not in rankings:
                            rankings[competitor] = {}
                        rankings[competitor][keyword] = idx
                        
        return rankings
    
    async def analyze_serp_features(self, query: str) -> Dict[str, Any]:
        """
        Analyze SERP features for a query.
        
        Args:
            query: Search query
            
        Returns:
            SERP features analysis
        """
        results = await self.search_google(query)
        
        features = {
            "has_featured_snippet": "answer_box" in results,
            "has_knowledge_panel": "knowledge_graph" in results,
            "has_local_pack": "local_results" in results,
            "has_video_results": "video_results" in results,
            "has_shopping_results": "shopping_results" in results,
            "has_related_questions": "related_questions" in results,
            "total_results": results.get("search_information", {}).get("total_results", 0)
        }
        
        return features
    
    def _get_mock_search_results(self, query: str) -> Dict[str, Any]:
        """Return mock search results for development/testing."""
        return {
            "search_metadata": {
                "id": "mock_search_" + str(hash(query)),
                "status": "Success",
                "created_at": datetime.utcnow().isoformat(),
                "processed_at": datetime.utcnow().isoformat()
            },
            "search_parameters": {
                "engine": "google",
                "q": query,
                "location": "United States",
                "device": "desktop"
            },
            "search_information": {
                "organic_results_state": "Results for exact spelling",
                "query_displayed": query,
                "total_results": 1250000,
                "time_taken_displayed": 0.45
            },
            "organic_results": [
                {
                    "position": i + 1,
                    "title": f"Example Result {i + 1} for {query}",
                    "link": f"https://example{i + 1}.com/page",
                    "displayed_link": f"example{i + 1}.com",
                    "snippet": f"This is a sample snippet for result {i + 1} related to {query}.",
                    "date": "3 days ago"
                }
                for i in range(10)
            ],
            "related_questions": [
                {
                    "question": f"What is {query}?",
                    "snippet": f"A brief explanation about {query}.",
                    "link": "https://example.com/what-is"
                },
                {
                    "question": f"How to use {query}?",
                    "snippet": f"Steps to effectively use {query}.",
                    "link": "https://example.com/how-to"
                }
            ]
        }


# Create singleton instance
serpapi_service = SerpAPIService()