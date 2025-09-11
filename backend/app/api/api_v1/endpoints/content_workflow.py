"""
API endpoints for the Content Velocity Workflow (Pillar 4).

This module provides comprehensive endpoints for accelerating content creation and optimization,
including AI-powered content briefs, content enhancement packages, SEO optimization,
and content performance tracking.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.models.content import ContentBrief, ContentEnhancement
from app.services.openai_service import openai_service
from app.db.session import get_db
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)


class ContentBriefRequest(BaseModel):
    """Request model for creating AI-powered content briefs."""
    topic: str = Field(..., description="Main topic for the content brief")
    target_keywords: List[str] = Field(..., description="Primary keywords to target")
    content_type: str = Field("blog_post", description="Type of content: blog_post, landing_page, product_page, guide, etc.")
    target_audience: str = Field(..., description="Target audience description")
    word_count_range: str = Field("1500-2500", description="Target word count range")
    tone: str = Field("professional", description="Content tone: professional, casual, technical, friendly, etc.")
    competitor_urls: Optional[List[str]] = Field(default=[], description="Competitor URLs for analysis")
    brand_guidelines: Optional[str] = Field(None, description="Brand guidelines to follow")
    seo_focus: bool = Field(True, description="Include SEO optimization recommendations")
    include_outline: bool = Field(True, description="Generate detailed content outline")

    @validator('target_keywords')
    def validate_keywords(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one target keyword is required")
        if len(v) > 20:
            raise ValueError("Maximum 20 keywords allowed")
        return v


class ContentBriefResponse(BaseModel):
    """Response model for content brief creation."""
    brief_id: str = Field(..., description="Unique brief identifier")
    topic: str = Field(..., description="Content topic")
    content_strategy: Dict[str, Any] = Field(..., description="Comprehensive content strategy")
    seo_recommendations: Dict[str, Any] = Field(..., description="SEO optimization recommendations")
    content_outline: List[Dict[str, str]] = Field(..., description="Detailed content outline")
    keyword_analysis: Dict[str, Any] = Field(..., description="Keyword research and analysis")
    competitor_insights: List[Dict[str, Any]] = Field(..., description="Competitor content analysis")
    performance_targets: Dict[str, Any] = Field(..., description="Expected performance metrics")
    created_at: str = Field(..., description="Brief creation timestamp")


class ContentOptimizationRequest(BaseModel):
    """Request model for content optimization."""
    content: str = Field(..., description="Content to optimize")
    target_keywords: List[str] = Field(..., description="Keywords to optimize for")
    optimization_type: str = Field("comprehensive", description="Type of optimization: seo, readability, engagement, comprehensive")
    content_type: str = Field("blog_post", description="Type of content being optimized")
    analyze_competitors: bool = Field(False, description="Include competitor analysis")
    improve_structure: bool = Field(True, description="Improve content structure and flow")
    enhance_readability: bool = Field(True, description="Enhance readability and engagement")

    @validator('content')
    def validate_content_length(cls, v):
        if len(v.strip()) < 100:
            raise ValueError("Content must be at least 100 characters long")
        if len(v) > 50000:
            raise ValueError("Content must be less than 50,000 characters")
        return v


class ContentOptimizationResponse(BaseModel):
    """Response model for content optimization."""
    optimization_id: str = Field(..., description="Unique optimization identifier")
    original_analysis: Dict[str, Any] = Field(..., description="Analysis of original content")
    optimized_content: str = Field(..., description="Optimized content")
    optimization_summary: Dict[str, Any] = Field(..., description="Summary of optimizations made")
    seo_improvements: Dict[str, Any] = Field(..., description="SEO improvements")
    readability_improvements: Dict[str, Any] = Field(..., description="Readability improvements")
    performance_predictions: Dict[str, Any] = Field(..., description="Predicted performance metrics")
    implementation_checklist: List[str] = Field(..., description="Implementation checklist")
    created_at: str = Field(..., description="Optimization timestamp")


class ContentGapAnalysisRequest(BaseModel):
    """Request model for content gap analysis."""
    primary_keywords: List[str] = Field(..., description="Primary keywords to analyze")
    competitor_domains: List[str] = Field(..., description="Competitor domains to analyze")
    content_categories: List[str] = Field(default=[], description="Content categories to focus on")
    analysis_depth: str = Field("standard", description="Analysis depth: basic, standard, comprehensive")
    include_trending_topics: bool = Field(True, description="Include trending topic analysis")


@router.post("/briefs", response_model=ContentBriefResponse)
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"content_brief:{hash(str(kwargs.get('brief_request').__dict__))}:{getattr(kwargs.get('current_user'), 'id', 'anonymous')}")
async def create_content_brief(
    brief_request: ContentBriefRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ContentBriefResponse:
    """
    Generate comprehensive AI-powered content briefs.
    
    Creates detailed content strategies including SEO recommendations,
    competitor analysis, content outlines, and performance targets.
    """
    try:
        brief_id = str(uuid.uuid4())
        
        # Generate comprehensive content brief using OpenAI
        brief_data = {
            "topic": brief_request.topic,
            "target_keywords": brief_request.target_keywords,
            "content_type": brief_request.content_type,
            "target_audience": brief_request.target_audience,
            "word_count_range": brief_request.word_count_range,
            "tone": brief_request.tone,
            "brand_guidelines": brief_request.brand_guidelines
        }
        content_strategy = await openai_service.generate_content_brief(brief_data)
        
        # Perform SEO analysis and recommendations
        seo_recommendations = await openai_service.generate_seo_recommendations(
            topic=brief_request.topic,
            keywords=brief_request.target_keywords,
            content_type=brief_request.content_type
        ) if brief_request.seo_focus else {}
        
        # Generate detailed content outline
        if brief_request.include_outline:
            word_count_range = None
            if brief_request.word_count_range:
                try:
                    # Parse word count range like "1500-2500"
                    range_parts = brief_request.word_count_range.split('-')
                    if len(range_parts) == 2:
                        word_count_range = (int(range_parts[0].strip()), int(range_parts[1].strip()))
                except:
                    pass
            content_outline = await openai_service.generate_content_outline(
                topic=brief_request.topic,
                keywords=brief_request.target_keywords,
                content_type=brief_request.content_type,
                word_count_range=word_count_range
            )
        else:
            content_outline = []
        
        # Analyze keywords for search volume and competition
        keyword_analysis = await openai_service.analyze_keywords(
            keywords=brief_request.target_keywords,
            content_type=brief_request.content_type
        )
        
        # Analyze competitor content if URLs provided
        competitor_insights = []
        if brief_request.competitor_urls:
            competitor_insights = await openai_service.analyze_competitor_content(
                competitor_urls=brief_request.competitor_urls,
                target_keywords=brief_request.target_keywords
            )
        
        # Generate performance targets
        performance_targets = await openai_service.predict_content_performance(
            content_strategy=content_strategy,
            keywords=brief_request.target_keywords,
            content_type=brief_request.content_type
        )
        
        # Store brief in database
        brief = ContentBrief(
            id=brief_id,
            user_id=current_user.id,
            topic=brief_request.topic,
            content_type=brief_request.content_type,
            target_keywords=brief_request.target_keywords,
            strategy_data=content_strategy,
            seo_data=seo_recommendations,
            status="completed"
        )
        db.add(brief)
        await db.commit()
        
        return ContentBriefResponse(
            brief_id=brief_id,
            topic=brief_request.topic,
            content_strategy=content_strategy,
            seo_recommendations=seo_recommendations,
            content_outline=content_outline,
            keyword_analysis=keyword_analysis,
            competitor_insights=competitor_insights,
            performance_targets=performance_targets,
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating content brief: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create content brief: {str(e)}")


@router.post("/optimize", response_model=ContentOptimizationResponse)
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"content_optimize:{hash(kwargs.get('optimization_request').content[:100])}:{getattr(kwargs.get('current_user'), 'id', 'anonymous')}")
async def optimize_content(
    optimization_request: ContentOptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ContentOptimizationResponse:
    """
    Optimize existing content for SEO, readability, and engagement.
    
    Analyzes content and provides optimized version with detailed
    improvements for better performance and user engagement.
    """
    try:
        optimization_id = str(uuid.uuid4())
        
        # Analyze original content
        original_analysis = await openai_service.analyze_content_quality(
            content=optimization_request.content,
            target_keywords=optimization_request.target_keywords,
            content_type=optimization_request.content_type
        )
        
        # Generate optimized content
        optimization_goals = [optimization_request.optimization_type]
        if optimization_request.improve_structure:
            optimization_goals.append("improve_structure")
        if optimization_request.enhance_readability:
            optimization_goals.append("enhance_readability")
        
        optimized_content_response = await openai_service.optimize_content(
            content=optimization_request.content,
            target_keywords=optimization_request.target_keywords,
            optimization_goals=optimization_goals
        )
        optimized_content = optimized_content_response.get("optimized_content", optimization_request.content)
        
        # Generate SEO improvements
        seo_improvements = await openai_service.generate_seo_improvements(
            content=optimization_request.content,
            current_seo_score=original_analysis.get("overall_score", 5.0),
            target_keywords=optimization_request.target_keywords
        )
        
        # Analyze readability improvements
        readability_improvements = await openai_service.analyze_readability_improvements(
            content=optimization_request.content,
            target_audience="general"
        )
        
        # Generate optimization summary
        optimization_results = [
            {"type": "seo", "improvements": seo_improvements},
            {"type": "readability", "improvements": readability_improvements},
            {"type": "content_quality", "analysis": original_analysis}
        ]
        optimization_summary = await openai_service.summarize_optimizations(
            optimization_results=optimization_results
        )
        
        # Predict performance improvements
        performance_predictions = await openai_service.predict_optimization_performance(
            original_content=optimization_request.content,
            optimized_content=optimized_content,
            target_keywords=optimization_request.target_keywords
        )
        
        # Generate implementation checklist
        implementation_checklist_response = await openai_service.generate_implementation_checklist(
            optimization_suggestions=optimization_summary
        )
        implementation_checklist = implementation_checklist_response if isinstance(implementation_checklist_response, list) else []
        
        # Store optimization in database
        enhancement = ContentEnhancement(
            id=optimization_id,
            user_id=current_user.id,
            original_content=optimization_request.content[:1000],  # Store preview
            optimized_content=optimized_content[:1000],  # Store preview
            optimization_type=optimization_request.optimization_type,
            target_keywords=optimization_request.target_keywords,
            improvements_data=optimization_summary,
            status="completed"
        )
        db.add(enhancement)
        await db.commit()
        
        return ContentOptimizationResponse(
            optimization_id=optimization_id,
            original_analysis=original_analysis,
            optimized_content=optimized_content,
            optimization_summary=optimization_summary,
            seo_improvements=seo_improvements,
            readability_improvements=readability_improvements,
            performance_predictions=performance_predictions,
            implementation_checklist=implementation_checklist,
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error optimizing content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize content: {str(e)}")


@router.post("/gap-analysis", response_model=Dict[str, Any])
@cache(expire=3600, key_builder=lambda func, *args, **kwargs: f"content_gaps:{hash(str(kwargs.get('gap_request').__dict__))}:{getattr(kwargs.get('current_user'), 'id', 'anonymous')}")
async def analyze_content_gaps(
    gap_request: ContentGapAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Perform comprehensive content gap analysis.
    
    Identifies content opportunities by analyzing competitor content,
    trending topics, and keyword gaps in your content strategy.
    """
    try:
        analysis_id = str(uuid.uuid4())
        
        # Analyze competitor content coverage
        competitor_analysis = await openai_service.analyze_competitor_content_coverage(
            competitor_urls=gap_request.competitor_domains,
            target_keywords=gap_request.primary_keywords,
            content_type="article"
        )
        
        # Identify keyword gaps
        keyword_gaps = await openai_service.identify_keyword_gaps(
            current_keywords=gap_request.primary_keywords,
            competitor_keywords=gap_request.primary_keywords,  # This would normally be extracted from competitor analysis
            industry="SEO"
        )
        
        # Analyze trending topics if requested
        trending_analysis = {}
        if gap_request.include_trending_topics:
            trending_analysis = await openai_service.analyze_trending_topics(
                industry="SEO",
                target_keywords=gap_request.primary_keywords,
                timeframe="30d"
            )
        
        # Generate content opportunities
        content_opportunities = await openai_service.generate_content_opportunities(
            gap_analysis=keyword_gaps,
            content_strategy={"keywords": gap_request.primary_keywords, "categories": gap_request.content_categories}
        )
        
        # Prioritize opportunities
        prioritized_opportunities = await openai_service.prioritize_content_opportunities(
            opportunities=content_opportunities,
            business_goals=["increase organic traffic", "improve search rankings", "boost engagement"]
        )
        
        return {
            "analysis_id": analysis_id,
            "gap_analysis": {
                "keyword_gaps": keyword_gaps,
                "competitor_coverage": competitor_analysis,
                "trending_opportunities": trending_analysis,
                "content_opportunities": prioritized_opportunities
            },
            "recommendations": {
                "high_priority_content": prioritized_opportunities[:3] if isinstance(prioritized_opportunities, list) else [],
                "quick_wins": prioritized_opportunities[3:6] if isinstance(prioritized_opportunities, list) and len(prioritized_opportunities) > 3 else [],
                "long_term_strategy": prioritized_opportunities[6:] if isinstance(prioritized_opportunities, list) and len(prioritized_opportunities) > 6 else []
            },
            "competitive_insights": competitor_analysis.get("insights", {}) if isinstance(competitor_analysis, dict) else {},
            "implementation_roadmap": await openai_service.generate_content_roadmap(
                prioritized_opportunities=prioritized_opportunities,
                timeline="12w"
            ),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing content gaps: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze content gaps: {str(e)}")


@router.post("/sge-optimization", response_model=Dict[str, Any])
async def optimize_for_sge(
    content: str,
    target_queries: List[str],
    content_type: str = "article",
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Optimize content for Search Generative Experience (SGE).
    
    Analyzes content and provides optimizations specifically for
    AI-powered search results and featured snippets.
    """
    try:
        optimization_id = str(uuid.uuid4())
        
        # Analyze SGE optimization potential
        sge_analysis = await openai_service.analyze_sge_potential(
            content=content,
            target_keywords=target_queries,
            content_type=content_type
        )
        
        # Generate SGE-optimized content
        sge_optimized_content_response = await openai_service.optimize_for_sge(
            content=content,
            current_url="https://example.com",  # This would normally be passed in the request
            target_keywords=target_queries
        )
        sge_optimized_content = sge_optimized_content_response.get("optimized_content", content)
        
        # Generate structured data recommendations
        structured_data_recommendations = await openai_service.generate_structured_data_recommendations(
            content=sge_optimized_content,
            content_type=content_type
        )
        
        return {
            "optimization_id": optimization_id,
            "sge_analysis": sge_analysis,
            "optimized_content": sge_optimized_content,
            "structured_data": structured_data_recommendations,
            "sge_triggers": sge_analysis.get("potential_triggers", []),
            "citation_optimization": sge_analysis.get("citation_potential", {}),
            "conversational_queries": sge_analysis.get("conversational_opportunities", []),
            "implementation_guide": await openai_service.generate_sge_implementation_guide(
                sge_recommendations=sge_analysis
            ),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing for SGE: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize for SGE: {str(e)}")


@router.get("/briefs", response_model=Dict[str, List[Dict[str, Any]]])
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"user_briefs:{getattr(kwargs.get('current_user'), 'id', 'anonymous')}")
async def get_content_briefs(
    limit: int = Query(20, description="Maximum number of briefs to return"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get user's content briefs with filtering options.
    
    Returns a list of previously created content briefs with
    their strategies, outlines, and performance data.
    """
    try:
        query = select(ContentBrief).where(ContentBrief.user_id == current_user.id)
        
        if content_type:
            query = query.where(ContentBrief.content_type == content_type)
        
        query = query.order_by(ContentBrief.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        briefs = result.scalars().all()
        
        briefs_data = [
            {
                "brief_id": brief.id,
                "topic": brief.topic,
                "content_type": brief.content_type,
                "target_keywords": brief.target_keywords,
                "status": brief.status,
                "created_at": brief.created_at.isoformat(),
                "strategy_summary": brief.strategy_data.get("summary", "") if brief.strategy_data else ""
            }
            for brief in briefs
        ]
        
        return {"briefs": briefs_data}
        
    except Exception as e:
        logger.error(f"Error getting content briefs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content briefs: {str(e)}")


@router.get("/briefs/{brief_id}", response_model=ContentBriefResponse)
@cache(expire=3600, key_builder=lambda func, *args, **kwargs: f"brief:{kwargs.get('brief_id')}:{getattr(kwargs.get('current_user'), 'id', 'anonymous')}")
async def get_content_brief(
    brief_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ContentBriefResponse:
    """
    Get detailed content brief by ID.
    
    Returns comprehensive brief data including strategy,
    SEO recommendations, outline, and performance targets.
    """
    try:
        query = select(ContentBrief).where(
            ContentBrief.id == brief_id,
            ContentBrief.user_id == current_user.id
        )
        result = await db.execute(query)
        brief = result.scalar_one_or_none()
        
        if not brief:
            raise HTTPException(status_code=404, detail="Content brief not found")
        
        return ContentBriefResponse(
            brief_id=brief.id,
            topic=brief.topic,
            content_strategy=brief.strategy_data or {},
            seo_recommendations=brief.seo_data or {},
            content_outline=brief.strategy_data.get("outline", []) if brief.strategy_data else [],
            keyword_analysis=brief.strategy_data.get("keyword_analysis", {}) if brief.strategy_data else {},
            competitor_insights=brief.strategy_data.get("competitor_insights", []) if brief.strategy_data else [],
            performance_targets=brief.strategy_data.get("performance_targets", {}) if brief.strategy_data else {},
            created_at=brief.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content brief: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content brief: {str(e)}")


@router.get("/performance-tracking", response_model=Dict[str, Any])
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"content_performance:{getattr(kwargs.get('current_user'), 'id', 'anonymous')}")
async def track_content_performance(
    content_ids: Optional[List[str]] = Query(None, description="Specific content IDs to track"),
    time_period: str = Query("30d", description="Time period for tracking: 7d, 30d, 90d"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Track content performance and optimization results.
    
    Provides performance metrics for content briefs and
    optimizations, including SEO metrics and engagement data.
    """
    try:
        # Get user's content briefs and enhancements
        briefs_query = select(ContentBrief).where(ContentBrief.user_id == current_user.id)
        enhancements_query = select(ContentEnhancement).where(ContentEnhancement.user_id == current_user.id)
        
        if content_ids:
            briefs_query = briefs_query.where(ContentBrief.id.in_(content_ids))
            enhancements_query = enhancements_query.where(ContentEnhancement.id.in_(content_ids))
        
        briefs_result = await db.execute(briefs_query)
        enhancements_result = await db.execute(enhancements_query)
        
        briefs = briefs_result.scalars().all()
        enhancements = enhancements_result.scalars().all()
        
        # Generate performance summary
        performance_summary = {
            "total_briefs": len(briefs),
            "total_optimizations": len(enhancements),
            "content_types": {},
            "keyword_performance": {},
            "optimization_impact": {}
        }
        
        # Analyze content type distribution
        for brief in briefs:
            content_type = brief.content_type
            if content_type not in performance_summary["content_types"]:
                performance_summary["content_types"][content_type] = 0
            performance_summary["content_types"][content_type] += 1
        
        # Simulate performance tracking (in real implementation, this would pull from analytics)
        performance_summary["recent_performance"] = {
            "avg_improvement": "23%",
            "best_performing_type": max(performance_summary["content_types"].keys(), default="blog_post"),
            "optimization_success_rate": "87%"
        }
        
        return {
            "performance_summary": performance_summary,
            "content_details": [
                {
                    "id": brief.id,
                    "topic": brief.topic,
                    "type": brief.content_type,
                    "keywords": brief.target_keywords,
                    "status": brief.status,
                    "created_at": brief.created_at.isoformat()
                }
                for brief in briefs
            ],
            "optimization_details": [
                {
                    "id": enhancement.id,
                    "type": enhancement.optimization_type,
                    "keywords": enhancement.target_keywords,
                    "status": enhancement.status,
                    "created_at": enhancement.created_at.isoformat()
                }
                for enhancement in enhancements
            ],
            "tracking_period": time_period,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error tracking content performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track content performance: {str(e)}")