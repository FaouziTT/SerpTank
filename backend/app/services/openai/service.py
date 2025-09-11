"""
Main OpenAI service providing the public interface.

This module implements the OpenAIService class that coordinates
all OpenAI-related functionality.
"""
import logging
from typing import Dict, List, Optional, Any

from app.core.config import settings

from .client import OpenAIClient
from .content_service import ContentService
from .seo_service import SEOService

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API integration."""
    
    def __init__(self):
        """Initialize the OpenAI service."""
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self.base_url = "https://api.openai.com/v1"
        
        # Initialize client and sub-services if configured
        if self.is_configured():
            self.client = OpenAIClient(self.api_key, self.base_url)
            self.content_service = ContentService(self.client, self.model, self.max_tokens)
            self.seo_service = SEOService(self.client, self.model)
        else:
            self.client = None
            self.content_service = None
            self.seo_service = None
    
    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return bool(self.api_key)
    
    def _validate_response(self, response: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Validate OpenAI service response."""
        if not isinstance(response, dict):
            logger.warning(f"OpenAI {operation} returned non-dict response: {type(response)}")
            return {"error": f"Invalid response format for {operation}"}
        
        if "error" in response:
            logger.error(f"OpenAI {operation} error: {response['error']}")
            return response
        
        return response
    
    async def generate_content(
        self,
        prompt: str,
        content_type: str = "article",
        target_keywords: Optional[List[str]] = None,
        word_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate SEO-optimized content using OpenAI.
        
        Args:
            prompt: Content generation prompt
            content_type: Type of content (article, meta_description, title, etc.)
            target_keywords: Keywords to optimize for
            word_count: Target word count
            
        Returns:
            Generated content with SEO recommendations
            
        Raises:
            ValueError: If OpenAI is not configured
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        try:
            response = await self.content_service.generate_content(
                prompt, content_type, target_keywords, word_count
            )
            return self._validate_response(response, "generate_content")
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return {"error": f"Content generation failed: {str(e)}"}
    
    async def analyze_content_gaps(
        self,
        current_content: str,
        competitor_content: str,
        target_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze content gaps between your content and competitors.
        
        Args:
            current_content: Your current content
            competitor_content: Competitor's content
            target_keywords: Keywords to focus on
            
        Returns:
            Content gap analysis with opportunities
            
        Raises:
            ValueError: If OpenAI is not configured
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.analyze_content_gaps(
            current_content, competitor_content, target_keywords
        )
    
    async def optimize_for_sge(
        self,
        content: str,
        current_url: str,
        target_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Optimize content for Google's Search Generative Experience (SGE).
        
        Args:
            content: Current content
            current_url: URL of the content
            target_keywords: Target keywords
            
        Returns:
            SGE optimization recommendations
            
        Raises:
            ValueError: If OpenAI is not configured
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.optimize_for_sge(
            content, current_url, target_keywords
        )
    
    async def generate_seo_insights(
        self,
        analytics_data: Dict[str, Any],
        serp_data: Dict[str, Any],
        technical_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive SEO insights from various data sources.
        
        Args:
            analytics_data: Google Analytics or similar data
            serp_data: SERP analysis data
            technical_data: Technical SEO audit data
            
        Returns:
            SEO insights and recommendations
            
        Raises:
            ValueError: If OpenAI is not configured
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.generate_seo_insights(
            analytics_data, serp_data, technical_data
        )
    
    async def generate_content_brief(self, brief_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive content brief.
        
        Args:
            brief_data: Data for brief generation including topic, keywords, etc.
            
        Returns:
            Generated content brief with structure and guidelines
            
        Raises:
            ValueError: If OpenAI is not configured
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        try:
            response = await self.content_service.generate_content_brief(brief_data)
            return self._validate_response(response, "generate_content_brief")
        except Exception as e:
            logger.error(f"Content brief generation failed: {e}")
            return {"error": f"Content brief generation failed: {str(e)}"}
    
    async def generate_content_enhancement(
        self,
        enhancement_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate content enhancement suggestions.
        
        Args:
            enhancement_data: Data including content, enhancement type, goals
            
        Returns:
            Enhancement suggestions and recommendations
            
        Raises:
            ValueError: If OpenAI is not configured
        """
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.generate_content_enhancement(enhancement_data)
    
    # Content Brief Methods
    async def generate_seo_recommendations(
        self,
        topic: str,
        keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Generate SEO recommendations for content."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        try:
            response = await self.seo_service.generate_seo_recommendations(topic, keywords, content_type)
            return self._validate_response(response, "generate_seo_recommendations")
        except Exception as e:
            logger.error(f"SEO recommendations generation failed: {e}")
            return {"error": f"SEO recommendations generation failed: {str(e)}"}
    
    async def generate_content_outline(
        self,
        topic: str,
        keywords: List[str],
        content_type: str = "article",
        word_count_range: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Generate detailed content outline."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.generate_content_outline(topic, keywords, content_type, word_count_range)
    
    async def analyze_keywords(
        self,
        keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze keywords for search volume and competition."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.analyze_keywords(keywords, content_type)
    
    async def analyze_competitor_content(
        self,
        competitor_urls: List[str],
        target_keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze competitor content for insights."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.analyze_competitor_content(competitor_urls, target_keywords)
    
    async def predict_content_performance(
        self,
        content_strategy: Dict[str, Any],
        keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Predict content performance based on strategy."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.predict_content_performance(content_strategy, keywords, content_type)
    
    # Content Optimization Methods
    async def analyze_content_quality(
        self,
        content: str,
        target_keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze content quality and provide score."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.analyze_content_quality(content, target_keywords, content_type)
    
    async def optimize_content(
        self,
        content: str,
        target_keywords: List[str],
        optimization_goals: List[str]
    ) -> Dict[str, Any]:
        """Optimize content for specific goals."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.optimize_content(content, target_keywords, optimization_goals)
    
    async def generate_seo_improvements(
        self,
        content: str,
        current_seo_score: float,
        target_keywords: List[str]
    ) -> Dict[str, Any]:
        """Generate SEO improvement suggestions."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.generate_seo_improvements(content, current_seo_score, target_keywords)
    
    async def analyze_readability_improvements(
        self,
        content: str,
        target_audience: str = "general"
    ) -> Dict[str, Any]:
        """Analyze and suggest readability improvements."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.analyze_readability_improvements(content, target_audience)
    
    async def summarize_optimizations(
        self,
        optimization_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize all optimization results."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.summarize_optimizations(optimization_results)
    
    async def predict_optimization_performance(
        self,
        original_content: str,
        optimized_content: str,
        target_keywords: List[str]
    ) -> Dict[str, Any]:
        """Predict performance improvement from optimization."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.predict_optimization_performance(original_content, optimized_content, target_keywords)
    
    async def generate_implementation_checklist(
        self,
        optimization_suggestions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate implementation checklist for optimizations."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.generate_implementation_checklist(optimization_suggestions)
    
    # Gap Analysis Methods
    async def analyze_competitor_content_coverage(
        self,
        competitor_urls: List[str],
        target_keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze competitor content coverage."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.analyze_competitor_content_coverage(competitor_urls, target_keywords, content_type)
    
    async def identify_keyword_gaps(
        self,
        current_keywords: List[str],
        competitor_keywords: List[str],
        industry: str
    ) -> Dict[str, Any]:
        """Identify keyword gaps vs competitors."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.identify_keyword_gaps(current_keywords, competitor_keywords, industry)
    
    async def analyze_trending_topics(
        self,
        industry: str,
        target_keywords: List[str],
        timeframe: str = "30d"
    ) -> Dict[str, Any]:
        """Analyze trending topics in industry."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.analyze_trending_topics(industry, target_keywords, timeframe)
    
    async def generate_content_opportunities(
        self,
        gap_analysis: Dict[str, Any],
        content_strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate content opportunities from gap analysis."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.generate_content_opportunities(gap_analysis, content_strategy)
    
    async def prioritize_content_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        business_goals: List[str]
    ) -> List[Dict[str, Any]]:
        """Prioritize content opportunities based on business goals."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.prioritize_content_opportunities(opportunities, business_goals)
    
    async def generate_content_roadmap(
        self,
        prioritized_opportunities: List[Dict[str, Any]],
        timeline: str = "6m"
    ) -> Dict[str, Any]:
        """Generate content roadmap from opportunities."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.content_service.generate_content_roadmap(prioritized_opportunities, timeline)
    
    # SGE Methods
    async def analyze_sge_potential(
        self,
        content: str,
        target_keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze SGE potential for content."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.analyze_sge_potential(content, target_keywords, content_type)
    
    async def generate_structured_data_recommendations(
        self,
        content: str,
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Generate structured data recommendations."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.generate_structured_data_recommendations(content, content_type)
    
    async def generate_sge_implementation_guide(
        self,
        sge_recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate SGE implementation guide."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured")
        
        return await self.seo_service.generate_sge_implementation_guide(sge_recommendations)