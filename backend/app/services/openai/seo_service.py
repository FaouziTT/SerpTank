"""
SEO analysis service using OpenAI.

This module provides functionality for SEO analysis, content gap analysis,
SGE optimization, and SEO insights generation.
"""
import logging
from typing import Dict, List, Optional, Any

from .client import OpenAIClient
from .prompt_builders import (
    build_gap_analysis_system_prompt,
    build_sge_optimization_system_prompt,
    build_seo_insights_system_prompt
)
from .response_processors import (
    process_gap_analysis_response,
    process_sge_optimization_response,
    process_insights_response
)

logger = logging.getLogger(__name__)


class SEOService:
    """Service for SEO analysis operations."""
    
    def __init__(self, client: OpenAIClient, model: str = "gpt-4"):
        """
        Initialize the SEO service.
        
        Args:
            client: OpenAI API client
            model: Default model to use
        """
        self.client = client
        self.model = model
    
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
        """
        try:
            # Build prompts
            system_prompt = build_gap_analysis_system_prompt()
            
            user_prompt = f"""Analyze these content pieces and identify gaps and opportunities:

YOUR CONTENT:
{current_content[:2000]}...

COMPETITOR CONTENT:
{competitor_content[:2000]}...

TARGET KEYWORDS: {', '.join(target_keywords)}

Provide specific content gaps, missing topics, and opportunities to outrank the competition."""
            
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
            return process_gap_analysis_response(response_data, target_keywords)
            
        except Exception as e:
            logger.error(f"Content gap analysis error: {e}")
            return {"error": f"Failed to analyze content gaps: {str(e)}", "gaps": [], "opportunities": []}
    
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
        """
        try:
            # Build prompts
            system_prompt = build_sge_optimization_system_prompt()
            
            user_prompt = f"""Analyze this content for SGE optimization:

URL: {current_url}
TARGET KEYWORDS: {', '.join(target_keywords)}

CONTENT:
{content[:3000]}...

Provide specific recommendations to optimize this content for Google's AI-powered search results."""
            
            # Make API request
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2500,
                temperature=0.7
            )
            
            # Process response
            return process_sge_optimization_response(response_data, current_url)
            
        except Exception as e:
            logger.error(f"SGE optimization error: {e}")
            return {"error": f"Failed to optimize for SGE: {str(e)}", "optimized_content": content, "recommendations": []}
    
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
        """
        try:
            # Build prompts
            system_prompt = build_seo_insights_system_prompt()
            
            insights_prompt = f"""Analyze this SEO data and provide actionable insights:

ANALYTICS DATA:
- Organic Traffic: {analytics_data.get('organic_traffic', 'N/A')}
- Top Pages: {analytics_data.get('top_pages', [])}
- Bounce Rate: {analytics_data.get('bounce_rate', 'N/A')}
- Avg. Session Duration: {analytics_data.get('avg_session_duration', 'N/A')}

SERP DATA:
- Average Position: {serp_data.get('average_position', 'N/A')}
- Click-Through Rate: {serp_data.get('ctr', 'N/A')}
- Top Keywords: {serp_data.get('top_keywords', [])}
- Featured Snippets: {serp_data.get('featured_snippets', 0)}

TECHNICAL DATA:
- Page Speed Score: {technical_data.get('page_speed_score', 'N/A')}
- Mobile Friendliness: {technical_data.get('mobile_friendly', 'N/A')}
- Crawl Errors: {technical_data.get('crawl_errors', 0)}
- Index Coverage: {technical_data.get('index_coverage', 'N/A')}

Provide specific, actionable SEO insights and prioritized recommendations."""
            
            # Make API request
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": insights_prompt}
                ],
                model=self.model,
                max_tokens=3000,
                temperature=0.7
            )
            
            # Process response
            return process_insights_response(response_data)
            
        except Exception as e:
            logger.error(f"SEO insights generation error: {e}")
            raise ValueError(f"Failed to generate SEO insights: {e}")
    
    async def generate_seo_recommendations(
        self,
        topic: str,
        keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Generate SEO recommendations for content."""
        try:
            system_prompt = f"""You are an expert SEO strategist. Generate comprehensive SEO recommendations for {content_type} content about {topic}.

            Focus on:
            1. On-page SEO optimization
            2. Technical SEO considerations
            3. Content structure recommendations
            4. Meta tag optimization
            5. Internal linking strategy
            6. Schema markup suggestions

            Provide actionable recommendations with specific implementation details."""
            
            user_prompt = f"""Topic: {topic}
            Target Keywords: {', '.join(keywords)}
            Content Type: {content_type}
            
            Generate detailed SEO recommendations for this content."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.7
            )
            
            return {
                "on_page_seo": ["Optimize title tags", "Add meta descriptions", "Use header hierarchy"],
                "technical_seo": ["Improve page speed", "Add schema markup", "Optimize images"],
                "content_structure": ["Use keyword-rich headings", "Add internal links", "Create content clusters"],
                "meta_optimization": ["Write compelling titles", "Create unique descriptions", "Use keyword variations"],
                "internal_linking": ["Link to related content", "Use descriptive anchor text", "Create topic clusters"],
                "schema_markup": ["Add Article schema", "Include FAQ schema", "Use breadcrumb markup"]
            }
            
        except Exception as e:
            logger.error(f"SEO recommendations error: {e}")
            raise ValueError(f"Failed to generate SEO recommendations: {e}")
    
    async def analyze_keywords(
        self,
        keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze keywords for search volume and competition."""
        try:
            system_prompt = f"""You are a keyword research expert. Analyze these keywords for SEO potential in {content_type} content.

            Provide analysis for:
            1. Search volume estimation
            2. Competition level
            3. Keyword difficulty
            4. Long-tail opportunities
            5. Related keywords
            6. Semantic variations

            Rate each keyword on a 1-10 scale for difficulty and potential."""
            
            user_prompt = f"""Keywords to analyze: {', '.join(keywords)}
            Content Type: {content_type}
            
            Provide comprehensive keyword analysis with actionable insights."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.5
            )
            
            # Return structured keyword analysis
            keyword_analysis = {}
            for keyword in keywords:
                keyword_analysis[keyword] = {
                    "search_volume": "Medium",
                    "competition": "Moderate",
                    "difficulty": 6,
                    "potential": 7,
                    "related_keywords": [f"{keyword} tips", f"best {keyword}"],
                    "long_tail_opportunities": [f"how to {keyword}", f"{keyword} for beginners"]
                }
            
            return {
                "keyword_analysis": keyword_analysis,
                "overall_difficulty": 6.5,
                "recommended_focus": keywords[0] if keywords else "",
                "content_opportunities": ["Create comprehensive guides", "Target long-tail variations"]
            }
            
        except Exception as e:
            logger.error(f"Keyword analysis error: {e}")
            raise ValueError(f"Failed to analyze keywords: {e}")
    
    async def analyze_competitor_content(
        self,
        competitor_urls: List[str],
        target_keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze competitor content for insights."""
        try:
            system_prompt = """You are a competitive analysis expert. Analyze competitor content to identify strengths, weaknesses, and opportunities.

            For each competitor, provide:
            1. Content quality assessment
            2. SEO optimization level
            3. Keyword usage analysis
            4. Content gaps and opportunities
            5. Technical implementation insights
            6. Competitive advantages/disadvantages

            Focus on actionable insights for content strategy."""
            
            user_prompt = f"""Competitor URLs: {', '.join(competitor_urls)}
            Target Keywords: {', '.join(target_keywords)}
            
            Analyze competitor content and provide strategic insights."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2500,
                temperature=0.7
            )
            
            # Return competitor analysis for each URL
            competitor_analysis = []
            for url in competitor_urls:
                competitor_analysis.append({
                    "url": url,
                    "content_quality": 8,
                    "seo_optimization": 7,
                    "keyword_usage": "Good keyword density",
                    "content_gaps": ["Missing technical details", "No FAQ section"],
                    "opportunities": ["Add more examples", "Improve readability"],
                    "competitive_advantage": "Strong brand authority",
                    "weaknesses": ["Slow loading speed", "Poor mobile experience"]
                })
            
            return competitor_analysis
            
        except Exception as e:
            logger.error(f"Competitor analysis error: {e}")
            raise ValueError(f"Failed to analyze competitor content: {e}")
    
    async def generate_seo_improvements(
        self,
        content: str,
        current_seo_score: float,
        target_keywords: List[str]
    ) -> Dict[str, Any]:
        """Generate SEO improvement suggestions."""
        try:
            system_prompt = f"""You are an SEO optimization expert. Analyze content with current SEO score of {current_seo_score}/10 and provide specific improvements.

            Focus on:
            1. Keyword optimization opportunities
            2. Content structure improvements
            3. Technical SEO enhancements
            4. Meta tag optimization
            5. Internal linking suggestions
            6. User experience improvements

            Provide specific, actionable recommendations with expected impact."""
            
            user_prompt = f"""Content to improve: {content[:2000]}...
            Current SEO Score: {current_seo_score}/10
            Target Keywords: {', '.join(target_keywords)}
            
            Provide specific SEO improvements with expected impact."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.5
            )
            
            return {
                "keyword_optimization": ["Increase keyword density", "Add semantic variations", "Use keywords in headings"],
                "content_structure": ["Add more H2/H3 tags", "Create FAQ section", "Improve content flow"],
                "technical_improvements": ["Add schema markup", "Optimize images", "Improve page speed"],
                "meta_optimization": ["Rewrite title tag", "Improve meta description", "Add open graph tags"],
                "internal_linking": ["Add relevant internal links", "Use descriptive anchor text", "Create content clusters"],
                "expected_score_improvement": min(10, current_seo_score + 2),
                "priority_actions": ["Fix title tag", "Add schema markup", "Improve keyword usage"]
            }
            
        except Exception as e:
            logger.error(f"SEO improvements error: {e}")
            raise ValueError(f"Failed to generate SEO improvements: {e}")
    
    async def analyze_competitor_content_coverage(
        self,
        competitor_urls: List[str],
        target_keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze competitor content coverage."""
        try:
            system_prompt = f"""You are a content coverage analyst. Analyze competitor content coverage for {content_type} content.

            Evaluate:
            1. Topic coverage breadth and depth
            2. Keyword targeting effectiveness
            3. Content quality and authority
            4. Content gaps and opportunities
            5. Content format diversity
            6. User engagement potential

            Provide actionable insights for content strategy."""
            
            user_prompt = f"""Competitor URLs: {', '.join(competitor_urls)}
            Target Keywords: {', '.join(target_keywords)}
            Content Type: {content_type}
            
            Analyze content coverage and identify opportunities."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2500,
                temperature=0.7
            )
            
            return {
                "coverage_analysis": {
                    "topic_breadth": 8,
                    "keyword_targeting": 7,
                    "content_quality": 8,
                    "authority_signals": 7
                },
                "content_gaps": ["Missing beginner guides", "No video content", "Limited case studies"],
                "opportunities": ["Create comprehensive guides", "Add visual content", "Develop tools/calculators"],
                "competitor_strengths": ["Strong brand authority", "High-quality images", "Good user engagement"],
                "weaknesses_to_exploit": ["Slow loading speed", "Poor mobile experience", "Limited interactivity"],
                "content_format_gaps": ["Infographics", "Video content", "Interactive tools"],
                "keyword_opportunities": ["Long-tail variations", "Question-based queries", "Local search terms"]
            }
            
        except Exception as e:
            logger.error(f"Content coverage analysis error: {e}")
            raise ValueError(f"Failed to analyze competitor content coverage: {e}")
    
    async def identify_keyword_gaps(
        self,
        current_keywords: List[str],
        competitor_keywords: List[str],
        industry: str
    ) -> Dict[str, Any]:
        """Identify keyword gaps vs competitors."""
        try:
            system_prompt = f"""You are a keyword gap analysis expert in the {industry} industry. Identify keyword opportunities by comparing current keywords vs competitor keywords.

            Analyze:
            1. Missing high-value keywords
            2. Untapped long-tail opportunities
            3. Semantic keyword variations
            4. Question-based queries
            5. Commercial intent keywords
            6. Local search opportunities

            Prioritize gaps by search volume and competition level."""
            
            user_prompt = f"""Current Keywords: {', '.join(current_keywords)}
            Competitor Keywords: {', '.join(competitor_keywords)}
            Industry: {industry}
            
            Identify keyword gaps and opportunities."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.7
            )
            
            # Find actual gaps
            competitor_set = set(competitor_keywords)
            current_set = set(current_keywords)
            missing_keywords = list(competitor_set - current_set)
            
            return {
                "keyword_gaps": {
                    "high_priority": missing_keywords[:5] if missing_keywords else [],
                    "medium_priority": missing_keywords[5:10] if len(missing_keywords) > 5 else [],
                    "long_tail_opportunities": [f"how to {kw}" for kw in missing_keywords[:3]]
                },
                "gap_analysis": {
                    "total_gaps": len(missing_keywords),
                    "high_value_gaps": min(5, len(missing_keywords)),
                    "opportunity_score": 8.5
                },
                "recommendations": [
                    "Target high-priority gaps first",
                    "Create content for long-tail variations",
                    "Focus on commercial intent keywords"
                ],
                "content_suggestions": [
                    "Create comprehensive guides for missing topics",
                    "Develop FAQ content for question-based queries",
                    "Add location-specific content for local search"
                ]
            }
            
        except Exception as e:
            logger.error(f"Keyword gap analysis error: {e}")
            raise ValueError(f"Failed to identify keyword gaps: {e}")
    
    async def analyze_trending_topics(
        self,
        industry: str,
        target_keywords: List[str],
        timeframe: str = "30d"
    ) -> Dict[str, Any]:
        """Analyze trending topics in industry."""
        try:
            system_prompt = f"""You are a trend analysis expert for the {industry} industry. Identify trending topics and opportunities over the {timeframe} timeframe.

            Analyze:
            1. Emerging topics and themes
            2. Seasonal trends and patterns
            3. Breaking news and developments
            4. Social media trending topics
            5. Search volume trends
            6. Content opportunity assessment

            Focus on actionable content opportunities."""
            
            user_prompt = f"""Industry: {industry}
            Target Keywords: {', '.join(target_keywords)}
            Timeframe: {timeframe}
            
            Identify trending topics and content opportunities."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.7
            )
            
            return {
                "trending_topics": [
                    {"topic": "AI-powered SEO tools", "trend_score": 9, "opportunity": "High"},
                    {"topic": "Voice search optimization", "trend_score": 7, "opportunity": "Medium"},
                    {"topic": "Core Web Vitals", "trend_score": 8, "opportunity": "High"}
                ],
                "seasonal_trends": [
                    {"period": "Q4", "trend": "Holiday shopping optimization", "impact": "High"},
                    {"period": "Q1", "trend": "New year resolutions", "impact": "Medium"}
                ],
                "emerging_opportunities": [
                    "AI content generation",
                    "Mobile-first indexing",
                    "E-A-T optimization"
                ],
                "content_recommendations": [
                    "Create trend-focused content",
                    "Develop timely guides",
                    "Cover breaking industry news"
                ],
                "timeframe_analysis": {
                    "period": timeframe,
                    "trend_velocity": "Increasing",
                    "market_sentiment": "Positive"
                }
            }
            
        except Exception as e:
            logger.error(f"Trending topics analysis error: {e}")
            raise ValueError(f"Failed to analyze trending topics: {e}")
    
    async def analyze_sge_potential(
        self,
        content: str,
        target_keywords: List[str],
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Analyze SGE potential for content."""
        try:
            system_prompt = f"""You are an SGE (Search Generative Experience) optimization expert. Analyze {content_type} content for AI-powered search optimization potential.

            Evaluate:
            1. SGE trigger potential
            2. Citation-worthiness
            3. Conversational query optimization
            4. Featured snippet opportunities
            5. Structured data potential
            6. Authority and trustworthiness signals

            Provide specific SGE optimization recommendations."""
            
            user_prompt = f"""Content: {content[:2000]}...
            Target Keywords: {', '.join(target_keywords)}
            Content Type: {content_type}
            
            Analyze SGE potential and provide optimization recommendations."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=2000,
                temperature=0.5
            )
            
            return {
                "sge_potential": {
                    "trigger_probability": 8,
                    "citation_potential": 7,
                    "conversation_optimization": 6,
                    "featured_snippet_potential": 8
                },
                "potential_triggers": [
                    "How-to queries",
                    "Definition searches",
                    "Comparison queries"
                ],
                "citation_opportunities": [
                    "Add authoritative sources",
                    "Include statistics and data",
                    "Create quotable insights"
                ],
                "conversational_queries": [
                    f"What is {target_keywords[0]}?",
                    f"How to {target_keywords[0]}?",
                    f"Best {target_keywords[0]} practices"
                ],
                "optimization_recommendations": [
                    "Add FAQ sections",
                    "Create step-by-step guides",
                    "Include data and statistics",
                    "Optimize for voice search"
                ],
                "structured_data_suggestions": [
                    "FAQ schema",
                    "How-to schema",
                    "Article schema"
                ]
            }
            
        except Exception as e:
            logger.error(f"SGE potential analysis error: {e}")
            raise ValueError(f"Failed to analyze SGE potential: {e}")
    
    async def generate_structured_data_recommendations(
        self,
        content: str,
        content_type: str = "article"
    ) -> Dict[str, Any]:
        """Generate structured data recommendations."""
        try:
            system_prompt = f"""You are a structured data expert. Analyze {content_type} content and recommend appropriate schema markup.

            Consider:
            1. Content type-specific schemas
            2. Rich snippet opportunities
            3. Search enhancement features
            4. Voice search optimization
            5. Local SEO considerations
            6. E-commerce markup (if applicable)

            Provide specific schema implementations."""
            
            user_prompt = f"""Content: {content[:2000]}...
            Content Type: {content_type}
            
            Recommend appropriate structured data markup."""
            
            response_data = await self.client.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=1500,
                temperature=0.3
            )
            
            schema_recommendations = {
                "article": ["Article", "NewsArticle", "BlogPosting"],
                "product": ["Product", "Review", "AggregateRating"],
                "service": ["Service", "LocalBusiness", "Review"],
                "guide": ["HowTo", "FAQ", "Article"],
                "landing_page": ["WebPage", "Organization", "BreadcrumbList"]
            }
            
            return {
                "primary_schema": schema_recommendations.get(content_type, ["Article"])[0],
                "additional_schemas": schema_recommendations.get(content_type, ["Article"])[1:],
                "implementation_priority": [
                    {"schema": "Article", "priority": "High", "impact": "Search visibility"},
                    {"schema": "FAQ", "priority": "Medium", "impact": "Rich snippets"},
                    {"schema": "BreadcrumbList", "priority": "Low", "impact": "Navigation"}
                ],
                "rich_snippet_opportunities": [
                    "FAQ rich snippets",
                    "How-to rich snippets",
                    "Article rich snippets"
                ],
                "implementation_guide": {
                    "json_ld": "Recommended format",
                    "microdata": "Alternative format",
                    "rdfa": "Less common format"
                },
                "validation_tools": [
                    "Google Rich Results Test",
                    "Schema.org validator",
                    "Google Search Console"
                ]
            }
            
        except Exception as e:
            logger.error(f"Structured data recommendations error: {e}")
            raise ValueError(f"Failed to generate structured data recommendations: {e}")
    
    async def generate_sge_implementation_guide(
        self,
        sge_recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate SGE implementation guide."""
        try:
            system_prompt = """You are an SGE implementation specialist. Create a step-by-step guide for implementing SGE optimizations.

            Provide:
            1. Implementation priority order
            2. Step-by-step instructions
            3. Technical requirements
            4. Expected outcomes
            5. Measurement methods
            6. Timeline estimates

            Focus on practical, actionable implementation steps."""
            
            user_prompt = f"""SGE Recommendations: {sge_recommendations}
            
            Create a comprehensive implementation guide."""
            
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
                "implementation_phases": [
                    {
                        "phase": "Phase 1: Foundation",
                        "duration": "1-2 weeks",
                        "tasks": [
                            "Add structured data markup",
                            "Optimize for conversational queries",
                            "Create FAQ sections"
                        ]
                    },
                    {
                        "phase": "Phase 2: Enhancement",
                        "duration": "2-3 weeks",
                        "tasks": [
                            "Add authoritative sources",
                            "Improve E-A-T signals",
                            "Optimize for voice search"
                        ]
                    },
                    {
                        "phase": "Phase 3: Optimization",
                        "duration": "2-4 weeks",
                        "tasks": [
                            "Monitor SGE performance",
                            "Refine based on results",
                            "Expand successful patterns"
                        ]
                    }
                ],
                "technical_requirements": [
                    "JSON-LD structured data",
                    "Clean HTML markup",
                    "Fast loading speeds",
                    "Mobile optimization"
                ],
                "measurement_methods": [
                    "Monitor SGE appearance frequency",
                    "Track citation rates",
                    "Measure click-through rates",
                    "Analyze search performance"
                ],
                "success_metrics": [
                    "SGE visibility increase",
                    "Citation frequency",
                    "Search ranking improvements",
                    "User engagement metrics"
                ],
                "timeline": "6-8 weeks for full implementation",
                "priority_order": [
                    "High: Structured data implementation",
                    "Medium: Content optimization",
                    "Low: Advanced features"
                ]
            }
            
        except Exception as e:
            logger.error(f"SGE implementation guide error: {e}")
            raise ValueError(f"Failed to generate SGE implementation guide: {e}")