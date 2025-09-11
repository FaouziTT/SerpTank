"""
Google Programmable Search Element Control API Service

This service provides functionality to interact with Google's Programmable Search
Element Control API for advanced SERP analysis and SEO insights.
"""
import logging
from typing import Dict, List, Optional, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProgrammableSearchService:
    """Service for Google Programmable Search Element Control API."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_PROGRAMMABLE_SEARCH_API_KEY
        self.search_engine_id = settings.GOOGLE_PROGRAMMABLE_SEARCH_ENGINE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_key and self.search_engine_id)
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "web"
    ) -> Dict[str, Any]:
        """
        Perform a search using Google Programmable Search Engine.
        
        Args:
            query: Search query
            num_results: Number of results to return
            search_type: Type of search (web, image, video)
            
        Returns:
            Search results with metadata
            
        Raises:
            ValueError: If Programmable Search is not configured
            Exception: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google Programmable Search is not configured. Please set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in your environment variables.")
        
        try:
            # Build the search URL
            search_url = f"{self.base_url}?key={self.api_key}&cx={self.search_engine_id}&q={query}&num={num_results}"
            
            if search_type == "image":
                search_url += "&searchType=image"
            elif search_type == "video":
                search_url += "&searchType=video"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url)
                response.raise_for_status()
                
                data = response.json()
                return self._process_search_results(data, query, num_results)
                
        except httpx.HTTPError as e:
            logger.error(f"Programmable Search API HTTP error: {e}")
            raise ValueError(f"Failed to perform search with Google Programmable Search: {e}")
        except Exception as e:
            logger.error(f"Programmable Search error: {e}")
            raise ValueError(f"Unexpected error performing search: {e}")
    
    async def search_with_filters(
        self,
        query: str,
        site_restrict: Optional[str] = None,
        date_restrict: Optional[str] = None,
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform a search with additional filters.
        
        Args:
            query: Search query
            site_restrict: Restrict search to specific site
            date_restrict: Restrict search by date (d, w, m, y)
            num_results: Number of results to return
            
        Returns:
            Filtered search results
            
        Raises:
            ValueError: If Programmable Search is not configured
            Exception: If API request fails
        """
        if not self.is_configured():
            raise ValueError("Google Programmable Search is not configured. Please set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in your environment variables.")
        
        try:
            # Build the search URL with filters
            search_url = f"{self.base_url}?key={self.api_key}&cx={self.search_engine_id}&q={query}&num={num_results}"
            
            if site_restrict:
                search_url += f"&siteSearch={site_restrict}"
            
            if date_restrict:
                search_url += f"&dateRestrict={date_restrict}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(search_url)
                response.raise_for_status()
                
                data = response.json()
                return self._process_search_results(data, query, num_results)
                
        except httpx.HTTPError as e:
            logger.error(f"Programmable Search API HTTP error: {e}")
            raise ValueError(f"Failed to perform filtered search with Google Programmable Search: {e}")
        except Exception as e:
            logger.error(f"Programmable Search filtered search error: {e}")
            raise ValueError(f"Unexpected error performing filtered search: {e}")
    
    async def analyze_serp_features(self, query: str) -> Dict[str, Any]:
        """
        Analyze SERP features for a given query.
        
        Args:
            query: Search query to analyze
            
        Returns:
            Analysis of SERP features present
        """
        search_results = await self.search(query, num_results=10)
        
        return {
            "query": query,
            "total_results": search_results.get("total_results", 0),
            "serp_features": {
                "featured_snippet": self._detect_featured_snippet(search_results),
                "people_also_ask": self._detect_people_also_ask(search_results),
                "local_pack": self._detect_local_pack(search_results),
                "knowledge_panel": self._detect_knowledge_panel(search_results),
                "image_pack": self._detect_image_pack(search_results),
                "video_results": self._detect_video_results(search_results)
            },
            "organic_results": search_results.get("organic_results", []),
            "competition_level": self._assess_competition_level(search_results)
        }
    
    async def track_keyword_positions(
        self,
        keywords: List[str],
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Track keyword positions for a specific domain.
        
        Args:
            keywords: List of keywords to track
            domain: Domain to track positions for
            
        Returns:
            List of keyword position data
        """
        results = []
        
        for keyword in keywords:
            try:
                search_data = await self.search(keyword, num_results=10)
                position = self._find_domain_position(search_data, domain)
                
                results.append({
                    "keyword": keyword,
                    "domain": domain,
                    "position": position,
                    "url": self._get_ranking_url(search_data, domain),
                    "title": self._get_ranking_title(search_data, domain),
                    "total_results": search_data.get("total_results", 0),
                    "competition_level": self._assess_competition_level(search_data)
                })
                
            except Exception as e:
                logger.error(f"Error tracking keyword '{keyword}': {e}")
                results.append({
                    "keyword": keyword,
                    "domain": domain,
                    "position": None,
                    "error": str(e)
                })
        
        return results
    
    def _process_search_results(self, data: Dict[str, Any], query: str, num_results: int) -> Dict[str, Any]:
        """Process raw API response into structured format."""
        items = data.get("items", [])
        
        organic_results = []
        for i, item in enumerate(items, 1):
            organic_results.append({
                "position": i,
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "domain": self._extract_domain(item.get("link", "")),
                "display_url": item.get("displayLink", "")
            })
        
        return {
            "query": query,
            "total_results": int(data.get("searchInformation", {}).get("totalResults", 0)),
            "search_time": float(data.get("searchInformation", {}).get("searchTime", 0)),
            "organic_results": organic_results
        }
    
    def _find_domain_position(self, search_data: Dict[str, Any], domain: str) -> Optional[int]:
        """Find the position of a domain in search results."""
        for result in search_data.get("organic_results", []):
            if domain.lower() in result.get("domain", "").lower():
                return result.get("position")
        return None
    
    def _get_ranking_url(self, search_data: Dict[str, Any], domain: str) -> Optional[str]:
        """Get the ranking URL for a domain."""
        for result in search_data.get("organic_results", []):
            if domain.lower() in result.get("domain", "").lower():
                return result.get("url")
        return None
    
    def _get_ranking_title(self, search_data: Dict[str, Any], domain: str) -> Optional[str]:
        """Get the ranking title for a domain."""
        for result in search_data.get("organic_results", []):
            if domain.lower() in result.get("domain", "").lower():
                return result.get("title")
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""
    
    def _detect_featured_snippet(self, search_data: Dict[str, Any]) -> bool:
        """Detect if featured snippet is present."""
        return len(search_data.get("organic_results", [])) > 0
    
    def _detect_people_also_ask(self, search_data: Dict[str, Any]) -> bool:
        """Detect if People Also Ask is present."""
        return False  # Placeholder
    
    def _detect_local_pack(self, search_data: Dict[str, Any]) -> bool:
        """Detect if local pack is present."""
        return False  # Placeholder
    
    def _detect_knowledge_panel(self, search_data: Dict[str, Any]) -> bool:
        """Detect if knowledge panel is present."""
        return False  # Placeholder
    
    def _detect_image_pack(self, search_data: Dict[str, Any]) -> bool:
        """Detect if image pack is present."""
        return False  # Placeholder
    
    def _detect_video_results(self, search_data: Dict[str, Any]) -> bool:
        """Detect if video results are present."""
        return False  # Placeholder
    
    def _assess_competition_level(self, search_data: Dict[str, Any]) -> str:
        """Assess competition level based on results."""
        total_results = search_data.get("total_results", 0)
        
        if total_results > 10000000:
            return "very_high"
        elif total_results > 1000000:
            return "high"
        elif total_results > 100000:
            return "medium"
        elif total_results > 10000:
            return "low"
        else:
            return "very_low"


# Create singleton instance
programmable_search_service = ProgrammableSearchService()

# Export alias for compatibility
search_client = programmable_search_service
