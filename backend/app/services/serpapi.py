"""
SerpAPI Service for Advanced SERP Analysis

This service provides enhanced SERP analysis using SerpAPI,
including advanced features like PAA, local packs, featured snippets, etc.
"""
import logging
from typing import Dict, List, Optional, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class SerpAPIService:
    """Service for SerpAPI advanced SERP analysis."""
    
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search"
        
    def is_configured(self) -> bool:
        """Check if SerpAPI is properly configured."""
        return bool(self.api_key)
    
    async def advanced_serp_analysis(
        self,
        query: str,
        location: str = "United States",
        device: str = "desktop",
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform advanced SERP analysis with rich features detection.
        
        Args:
            query: Search query
            location: Geographic location for search
            device: Device type (desktop/mobile)
            num_results: Number of results to analyze
            
        Returns:
            Advanced SERP analysis with all features
        """
        if not self.is_configured():
            logger.warning("SerpAPI not configured, using basic analysis")
            return self._get_basic_analysis(query)
        
        try:
            params = {
                "api_key": self.api_key,
                "engine": "google",
                "q": query,
                "location": location,
                "device": device,
                "num": min(num_results, 100),
                "no_cache": "false"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return self._process_serp_data(data, query)
                
        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
            return self._get_basic_analysis(query)
    
    async def local_seo_analysis(
        self,
        query: str,
        location: str,
        radius: int = 25
    ) -> Dict[str, Any]:
        """
        Analyze local SEO results including Google My Business listings.
        
        Args:
            query: Search query (e.g., "dentist near me")
            location: City, state or coordinates
            radius: Search radius in miles
            
        Returns:
            Local SEO analysis with map pack results
        """
        if not self.is_configured():
            return {"error": "SerpAPI not configured for local analysis"}
        
        try:
            params = {
                "api_key": self.api_key,
                "engine": "google",
                "q": query,
                "location": location,
                "ludocid": "true",  # Include local business data
                "num": 20
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return self._process_local_data(data, query, location)
                
        except Exception as e:
            logger.error(f"Local SEO analysis error: {e}")
            return {"error": str(e)}
    
    async def competitor_serp_comparison(
        self,
        queries: List[str],
        competitors: List[str],
        location: str = "United States"
    ) -> Dict[str, Any]:
        """
        Compare competitor visibility across multiple keywords.
        
        Args:
            queries: List of keywords to analyze
            competitors: List of competitor domains
            location: Geographic location
            
        Returns:
            Competitor visibility analysis
        """
        results = {}
        
        for query in queries[:5]:  # Limit to 5 queries to manage API usage
            try:
                serp_data = await self.advanced_serp_analysis(
                    query=query,
                    location=location,
                    num_results=20
                )
                
                results[query] = self._analyze_competitor_positions(
                    serp_data, competitors
                )
                
            except Exception as e:
                logger.error(f"Error analyzing query '{query}': {e}")
                results[query] = {"error": str(e)}
        
        return {
            "competitor_analysis": results,
            "summary": self._generate_competitor_summary(results, competitors)
        }
    
    def _process_serp_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Process SerpAPI response into structured analysis."""
        
        # Extract organic results
        organic_results = []
        for i, result in enumerate(data.get("organic_results", []), 1):
            organic_results.append({
                "position": i,
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "domain": self._extract_domain(result.get("link", "")),
                "rich_snippet": result.get("rich_snippet", {}),
                "sitelinks": result.get("sitelinks", [])
            })
        
        # Analyze SERP features
        serp_features = {
            "featured_snippet": self._extract_featured_snippet(data),
            "people_also_ask": self._extract_people_also_ask(data),
            "local_pack": self._extract_local_pack(data),
            "knowledge_panel": self._extract_knowledge_panel(data),
            "shopping_results": self._extract_shopping_results(data),
            "news_results": self._extract_news_results(data),
            "video_results": self._extract_video_results(data),
            "image_results": self._extract_image_results(data),
            "related_searches": self._extract_related_searches(data)
        }
        
        return {
            "query": query,
            "search_metadata": data.get("search_metadata", {}),
            "organic_results": organic_results,
            "serp_features": serp_features,
            "serp_features_count": sum(1 for v in serp_features.values() if v),
            "total_organic_results": len(organic_results),
            "search_information": data.get("search_information", {}),
            "powered_by": "SerpAPI"
        }
    
    def _process_local_data(self, data: Dict[str, Any], query: str, location: str) -> Dict[str, Any]:
        """Process local search results."""
        
        local_results = data.get("local_results", [])
        map_results = []
        
        for result in local_results:
            map_results.append({
                "title": result.get("title", ""),
                "address": result.get("address", ""),
                "phone": result.get("phone", ""),
                "rating": result.get("rating", 0),
                "reviews": result.get("reviews", 0),
                "hours": result.get("hours", ""),
                "website": result.get("website", ""),
                "place_id": result.get("place_id", ""),
                "coordinates": {
                    "lat": result.get("gps_coordinates", {}).get("latitude"),
                    "lng": result.get("gps_coordinates", {}).get("longitude")
                }
            })
        
        return {
            "query": query,
            "location": location,
            "local_pack_count": len(map_results),
            "local_results": map_results,
            "organic_results": self._process_serp_data(data, query)["organic_results"]
        }
    
    def _extract_featured_snippet(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract featured snippet information."""
        answer_box = data.get("answer_box")
        if answer_box:
            return {
                "type": answer_box.get("type", ""),
                "snippet": answer_box.get("snippet", ""),
                "title": answer_box.get("title", ""),
                "link": answer_box.get("link", ""),
                "displayed_link": answer_box.get("displayed_link", "")
            }
        return None
    
    def _extract_people_also_ask(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract People Also Ask questions."""
        paa = data.get("related_questions", [])
        return [
            {
                "question": q.get("question", ""),
                "snippet": q.get("snippet", ""),
                "title": q.get("title", ""),
                "link": q.get("link", "")
            }
            for q in paa
        ]
    
    def _extract_local_pack(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract local pack/map results."""
        local_results = data.get("local_results", [])
        if local_results:
            return {
                "count": len(local_results),
                "businesses": [
                    {
                        "title": lr.get("title", ""),
                        "rating": lr.get("rating", 0),
                        "address": lr.get("address", "")
                    }
                    for lr in local_results[:3]  # Top 3 local results
                ]
            }
        return None
    
    def _extract_knowledge_panel(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract knowledge panel information."""
        knowledge_graph = data.get("knowledge_graph")
        if knowledge_graph:
            return {
                "title": knowledge_graph.get("title", ""),
                "type": knowledge_graph.get("type", ""),
                "description": knowledge_graph.get("description", ""),
                "source": knowledge_graph.get("source", {}).get("name", "")
            }
        return None
    
    def _extract_shopping_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract shopping/product results."""
        shopping = data.get("shopping_results", [])
        return [
            {
                "title": s.get("title", ""),
                "price": s.get("price", ""),
                "source": s.get("source", ""),
                "link": s.get("link", "")
            }
            for s in shopping
        ]
    
    def _extract_news_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract news results."""
        news = data.get("news_results", [])
        return [
            {
                "title": n.get("title", ""),
                "source": n.get("source", ""),
                "date": n.get("date", ""),
                "link": n.get("link", "")
            }
            for n in news
        ]
    
    def _extract_video_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract video results."""
        videos = data.get("video_results", [])
        return [
            {
                "title": v.get("title", ""),
                "duration": v.get("duration", ""),
                "source": v.get("source", ""),
                "link": v.get("link", "")
            }
            for v in videos
        ]
    
    def _extract_image_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract image results."""
        images = data.get("images_results", [])
        return [
            {
                "title": img.get("title", ""),
                "source": img.get("source", ""),
                "thumbnail": img.get("thumbnail", ""),
                "original": img.get("original", "")
            }
            for img in images
        ]
    
    def _extract_related_searches(self, data: Dict[str, Any]) -> List[str]:
        """Extract related search suggestions."""
        related = data.get("related_searches", [])
        return [r.get("query", "") for r in related if r.get("query")]
    
    def _analyze_competitor_positions(self, serp_data: Dict[str, Any], competitors: List[str]) -> Dict[str, Any]:
        """Analyze competitor positions in SERP data."""
        positions = {}
        
        for result in serp_data.get("organic_results", []):
            domain = result.get("domain", "")
            for competitor in competitors:
                if competitor.lower() in domain.lower():
                    positions[competitor] = {
                        "position": result.get("position"),
                        "title": result.get("title"),
                        "url": result.get("url")
                    }
        
        return positions
    
    def _generate_competitor_summary(self, results: Dict[str, Any], competitors: List[str]) -> Dict[str, Any]:
        """Generate summary of competitor performance."""
        summary = {comp: {"total_rankings": 0, "avg_position": 0, "best_position": None} for comp in competitors}
        
        for query, data in results.items():
            if "error" in data:
                continue
            
            for competitor in competitors:
                if competitor in data and "position" in data[competitor]:
                    pos = data[competitor]["position"]
                    summary[competitor]["total_rankings"] += 1
                    if summary[competitor]["best_position"] is None or pos < summary[competitor]["best_position"]:
                        summary[competitor]["best_position"] = pos
        
        return summary
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""
    
    def _get_basic_analysis(self, query: str) -> Dict[str, Any]:
        """Return basic analysis when SerpAPI is not configured."""
        return {
            "query": query,
            "error": "SerpAPI not configured",
            "organic_results": [],
            "serp_features": {},
            "powered_by": "Basic Analysis (SerpAPI not configured)"
        }


# Create singleton instance
serpapi_service = SerpAPIService()

# Export alias for compatibility
serp_client = serpapi_service
