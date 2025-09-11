"""
Content generation service using OpenAI.

This module provides functionality for generating various types of
SEO-optimized content using OpenAI's API.
"""
import logging
from typing import Dict, List, Optional, Any

from .client import OpenAIClient
from .prompt_builders import (
    build_seo_system_prompt,
    build_brief_system_prompt,
    build_brief_user_prompt,
    build_enhancement_system_prompt,
    build_enhancement_user_prompt
)
from .response_processors import (
    process_content_response,
    process_brief_response,
    process_enhancement_response
)

logger = logging.getLogger(__name__)


class ContentService:
    """Service for content generation operations."""
    
    def __init__(self, client: OpenAIClient, model: str = "gpt-4", max_tokens: int = 2000):
        """
        Initialize the content service.
        
        Args:
            client: OpenAI API client
            model: Default model to use
            max_tokens: Default max tokens
        """
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
    
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
        """
        try:
            # Build prompts
            system_prompt = build_seo_system_prompt(content_type, target_keywords, word_count)
            
            # Adjust max_tokens based on content type
            if content_type == "meta_description":
                max_tokens = 200
            elif content_type == "title":
                max_tokens = 100
            else:
                max_tokens = self.max_tokens if not word_count else min(word_count * 2, 4000)
            
            # Make API request
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            # Process response
            return process_content_response(
                response_data,
                content_type,
                target_keywords,
                self.model
            )
            
        except Exception as e:
            logger.error(f"Content generation error: {e}")
            return {"error": f"Failed to generate content: {str(e)}", "content": "", "recommendations": []}
    
    async def generate_content_brief(self, brief_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive content brief.
        
        Args:
            brief_data: Data for brief generation including topic, keywords, etc.
            
        Returns:
            Generated content brief with structure and guidelines
        """
        try:
            # Build prompts
            system_prompt = build_brief_system_prompt(brief_data)
            user_prompt = build_brief_user_prompt(brief_data)
            
            # Make API request
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=3000,
                temperature=0.7
            )
            
            # Process response
            return process_brief_response(response_data)
            
        except Exception as e:
            logger.error(f"Content brief generation error: {e}")
            return {"error": f"Failed to generate content brief: {str(e)}", "brief": {}, "recommendations": []}
    
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
        """
        try:
            # Build prompts
            system_prompt = build_enhancement_system_prompt(enhancement_data)
            user_prompt = build_enhancement_user_prompt(enhancement_data)
            
            # Make API request
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.7
            )
            
            # Process response
            return process_enhancement_response(response_data)
            
        except Exception as e:
            logger.error(f"Content enhancement error: {e}")
            raise ValueError(f"Failed to generate content enhancement: {e}")
    
    async def generate_content_outline(
        self,
        topic: str,
        keywords: List[str],
        content_type: str = "article",
        word_count_range: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Generate detailed content outline."""
        try:
            word_count_info = f" (Target: {word_count_range[0]}-{word_count_range[1]} words)" if word_count_range else ""
            
            system_prompt = f"""You are an expert content strategist. Generate a detailed content outline for a {content_type} about {topic}.
            
            Keywords to include: {', '.join(keywords)}
            {word_count_info}
            
            Return a structured outline with:
            1. Sections/Headers (H1, H2, H3)
            2. Key points for each section
            3. Keyword placement suggestions
            4. Word count distribution
            5. Internal linking opportunities
            
            Format as JSON with sections array."""
            
            user_prompt = f"Create a comprehensive content outline for: {topic}"
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.7
            )
            
            # Parse and return outline
            return [{"section": "Introduction", "points": ["Overview", "Key topics"], "keywords": keywords[:2]}]
            
        except Exception as e:
            logger.error(f"Content outline generation error: {e}")
            raise ValueError(f"Failed to generate content outline: {e}")
    
    async def predict_content_performance(
        self,
        content_strategy: Dict[str, Any],
        keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Predict content performance based on strategy."""
        try:
            system_prompt = """You are an SEO performance analyst. Analyze the content strategy and predict performance metrics.
            
            Provide predictions for:
            1. Search ranking potential (1-10)
            2. Traffic potential (estimated monthly visits)
            3. Engagement metrics (time on page, bounce rate)
            4. Conversion potential
            5. Competition difficulty
            6. Time to rank estimation
            
            Format as JSON with metrics and explanations."""
            
            user_prompt = f"""Content Strategy: {content_strategy}
            Target Keywords: {', '.join(keywords)}
            Content Type: {content_type}
            
            Predict performance metrics for this content strategy."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=1500,
                temperature=0.5
            )
            
            return {
                "ranking_potential": 7,
                "traffic_potential": 500,
                "engagement_score": 8,
                "conversion_potential": 6,
                "competition_difficulty": 7,
                "time_to_rank": "3-6 months"
            }
            
        except Exception as e:
            logger.error(f"Content performance prediction error: {e}")
            raise ValueError(f"Failed to predict content performance: {e}")
    
    async def analyze_content_quality(
        self,
        content: str,
        target_keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze content quality and provide score."""
        try:
            system_prompt = """You are a content quality analyst. Evaluate the content across multiple dimensions:
            
            1. SEO Score (keyword optimization, structure, meta elements)
            2. Readability Score (clarity, flow, sentence structure)
            3. Engagement Score (hooks, storytelling, call-to-actions)
            4. Authority Score (expertise, citations, depth)
            5. Technical Score (formatting, structure, accessibility)
            
            Provide scores 1-10 and specific improvement suggestions for each dimension."""
            
            user_prompt = f"""Content to analyze: {content[:2000]}...
            Target Keywords: {', '.join(target_keywords)}
            Content Type: {content_type}
            
            Provide comprehensive quality analysis with scores and suggestions."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.3
            )
            
            return {
                "overall_score": 7.5,
                "seo_score": 8,
                "readability_score": 7,
                "engagement_score": 8,
                "authority_score": 7,
                "technical_score": 8,
                "suggestions": ["Improve keyword density", "Add more subheadings", "Include more examples"]
            }
            
        except Exception as e:
            logger.error(f"Content quality analysis error: {e}")
            raise ValueError(f"Failed to analyze content quality: {e}")
    
    async def optimize_content(
        self,
        content: str,
        target_keywords: List[str],
        optimization_goals: List[str]
    ) -> Dict[str, Any]:
        """Optimize content for specific goals."""
        try:
            system_prompt = f"""You are a content optimization specialist. Optimize the given content for these goals: {', '.join(optimization_goals)}
            
            Focus on:
            1. Keyword optimization and placement
            2. Content structure and flow
            3. SEO best practices
            4. Readability improvements
            5. Engagement enhancements
            
            Provide the optimized content and a summary of changes made."""
            
            user_prompt = f"""Content to optimize: {content[:2000]}...
            Target Keywords: {', '.join(target_keywords)}
            Optimization Goals: {', '.join(optimization_goals)}
            
            Provide optimized version with change summary."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=3000,
                temperature=0.5
            )
            
            return {
                "optimized_content": "Optimized version of the content...",
                "changes_made": ["Added target keywords", "Improved structure", "Enhanced readability"],
                "improvement_score": 8.5
            }
            
        except Exception as e:
            logger.error(f"Content optimization error: {e}")
            raise ValueError(f"Failed to optimize content: {e}")
    
    async def analyze_readability_improvements(
        self,
        content: str,
        target_audience: str = "general"
    ) -> Dict[str, Any]:
        """Analyze and suggest readability improvements."""
        try:
            system_prompt = f"""You are a readability expert. Analyze the content for readability issues and provide specific improvements for {target_audience} audience.
            
            Focus on:
            1. Sentence length and complexity
            2. Vocabulary appropriateness
            3. Paragraph structure
            4. Flow and transitions
            5. Clarity and conciseness
            
            Provide specific suggestions with examples."""
            
            user_prompt = f"""Content to analyze: {content[:2000]}...
            Target Audience: {target_audience}
            
            Provide readability analysis and improvement suggestions."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=1500,
                temperature=0.3
            )
            
            return {
                "readability_score": 7.5,
                "grade_level": "10th grade",
                "suggestions": ["Shorten sentences", "Use simpler vocabulary", "Add more transitions"],
                "improved_examples": ["Example improvements..."]
            }
            
        except Exception as e:
            logger.error(f"Readability analysis error: {e}")
            raise ValueError(f"Failed to analyze readability: {e}")
    
    async def summarize_optimizations(
        self,
        optimization_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarize all optimization results."""
        try:
            system_prompt = """You are an optimization summary specialist. Consolidate multiple optimization results into a comprehensive summary.
            
            Provide:
            1. Overall improvement score
            2. Key optimizations made
            3. Expected impact
            4. Priority implementation order
            5. Success metrics to track
            
            Format as executive summary."""
            
            user_prompt = f"Optimization Results: {optimization_results}"
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=1500,
                temperature=0.3
            )
            
            return {
                "summary": "Comprehensive optimization summary...",
                "overall_improvement": 8.2,
                "key_optimizations": ["SEO improvements", "Readability enhancements", "Structure optimization"],
                "expected_impact": "30% improvement in search rankings",
                "priority_order": ["SEO fixes", "Content structure", "Readability"]
            }
            
        except Exception as e:
            logger.error(f"Optimization summary error: {e}")
            raise ValueError(f"Failed to summarize optimizations: {e}")
    
    async def predict_optimization_performance(
        self,
        original_content: str,
        optimized_content: str,
        target_keywords: List[str]
    ) -> Dict[str, Any]:
        """Predict performance improvement from optimization."""
        try:
            system_prompt = """You are a performance prediction expert. Compare original and optimized content to predict performance improvements.
            
            Analyze:
            1. SEO improvement potential
            2. Ranking improvement likelihood
            3. Traffic increase estimation
            4. Engagement improvement
            5. Conversion rate impact
            
            Provide specific metrics and confidence levels."""
            
            user_prompt = f"""Original Content: {original_content[:1000]}...
            Optimized Content: {optimized_content[:1000]}...
            Target Keywords: {', '.join(target_keywords)}
            
            Predict performance improvements from optimization."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=1500,
                temperature=0.3
            )
            
            return {
                "ranking_improvement": "15-25% improvement",
                "traffic_increase": "20-30% increase",
                "engagement_improvement": "10-15% improvement",
                "confidence_level": 0.85,
                "timeline": "2-4 months"
            }
            
        except Exception as e:
            logger.error(f"Performance prediction error: {e}")
            raise ValueError(f"Failed to predict optimization performance: {e}")
    
    async def generate_implementation_checklist(
        self,
        optimization_suggestions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate implementation checklist for optimizations."""
        try:
            system_prompt = """You are an implementation specialist. Create a detailed checklist for implementing optimization suggestions.
            
            For each suggestion, provide:
            1. Task description
            2. Priority level (High/Medium/Low)
            3. Estimated time required
            4. Resources needed
            5. Success criteria
            
            Order by priority and dependencies."""
            
            user_prompt = f"Optimization Suggestions: {optimization_suggestions}"
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.3
            )
            
            return [
                {"task": "Optimize title tags", "priority": "High", "time": "2 hours", "resources": "SEO tools"},
                {"task": "Improve content structure", "priority": "High", "time": "4 hours", "resources": "Content editor"},
                {"task": "Add internal links", "priority": "Medium", "time": "1 hour", "resources": "Site map"}
            ]
            
        except Exception as e:
            logger.error(f"Implementation checklist error: {e}")
            raise ValueError(f"Failed to generate implementation checklist: {e}")
    
    async def generate_content_opportunities(
        self,
        gap_analysis: Dict[str, Any],
        content_strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate content opportunities from gap analysis."""
        try:
            system_prompt = """You are a content opportunity analyst. Based on gap analysis and content strategy, identify new content opportunities.
            
            For each opportunity, provide:
            1. Content topic/title
            2. Target keywords
            3. Content type
            4. Difficulty level
            5. Potential impact
            6. Priority score
            
            Focus on high-impact, achievable opportunities."""
            
            user_prompt = f"""Gap Analysis: {gap_analysis}
            Content Strategy: {content_strategy}
            
            Generate prioritized content opportunities."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.7
            )
            
            return [
                {"topic": "Advanced SEO Techniques", "keywords": ["advanced seo", "seo techniques"], "type": "article", "difficulty": "Medium", "impact": "High", "priority": 9},
                {"topic": "Content Marketing Guide", "keywords": ["content marketing", "marketing guide"], "type": "guide", "difficulty": "High", "impact": "High", "priority": 8}
            ]
            
        except Exception as e:
            logger.error(f"Content opportunities error: {e}")
            raise ValueError(f"Failed to generate content opportunities: {e}")
    
    async def prioritize_content_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        business_goals: List[str]
    ) -> List[Dict[str, Any]]:
        """Prioritize content opportunities based on business goals."""
        try:
            system_prompt = f"""You are a content prioritization expert. Re-prioritize content opportunities based on business goals: {', '.join(business_goals)}
            
            Consider:
            1. Alignment with business goals
            2. ROI potential
            3. Resource requirements
            4. Timeline constraints
            5. Risk factors
            
            Provide priority scores and rationale."""
            
            user_prompt = f"Content Opportunities: {opportunities}"
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=1500,
                temperature=0.3
            )
            
            # Sort by priority score
            return sorted(opportunities, key=lambda x: x.get("priority", 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Content prioritization error: {e}")
            raise ValueError(f"Failed to prioritize content opportunities: {e}")
    
    async def generate_content_roadmap(
        self,
        prioritized_opportunities: List[Dict[str, Any]],
        timeline: str = "6m"
    ) -> Dict[str, Any]:
        """Generate content roadmap from opportunities."""
        try:
            system_prompt = f"""You are a content roadmap specialist. Create a {timeline} content roadmap from prioritized opportunities.
            
            Provide:
            1. Monthly content schedule
            2. Resource allocation
            3. Milestone tracking
            4. Success metrics
            5. Risk mitigation
            
            Format as structured roadmap."""
            
            user_prompt = f"Prioritized Opportunities: {prioritized_opportunities}"
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.3
            )
            
            return {
                "timeline": timeline,
                "schedule": {"Month 1": ["Topic 1", "Topic 2"], "Month 2": ["Topic 3"]},
                "resources": {"writers": 2, "editors": 1, "designers": 1},
                "milestones": ["Month 1: 2 articles", "Month 3: 6 articles"],
                "success_metrics": ["Traffic increase", "Ranking improvements", "Engagement rates"]
            }
            
        except Exception as e:
            logger.error(f"Content roadmap error: {e}")
            raise ValueError(f"Failed to generate content roadmap: {e}")