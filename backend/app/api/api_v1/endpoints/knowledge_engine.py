"""
API endpoints for the Institutional Knowledge Engine (Pillar 6).

This module provides comprehensive endpoints for creating compounding competitive advantage
through strategic ledger, private tuning loop, evolving intelligence, and institutional
memory that continuously learns and adapts to improve strategic decision-making.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.db.session import get_db
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.services.knowledge_engine import knowledge_engine_service
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)


class StrategicLedgerEntry(BaseModel):
    """Model for strategic ledger entries."""
    entry_id: str = Field(..., description="Unique entry identifier")
    category: str = Field(..., description="Entry category: insight, decision, outcome, lesson")
    title: str = Field(..., description="Entry title")
    content: str = Field(..., description="Detailed content")
    tags: List[str] = Field(default=[], description="Tags for categorization")
    confidence_score: float = Field(..., description="Confidence in this insight (0.0-1.0)")
    business_impact: str = Field(..., description="Expected business impact: low, medium, high, critical")
    source_data: Dict[str, Any] = Field(..., description="Source data and references")
    created_at: str = Field(..., description="Creation timestamp")


class IntelligenceGenerationRequest(BaseModel):
    """Request model for generating strategic intelligence."""
    analysis_type: str = Field(..., description="Type of analysis: competitive, market, performance, strategic")
    data_sources: List[str] = Field(..., description="Data sources to analyze")
    focus_areas: List[str] = Field(default=[], description="Specific focus areas")
    time_horizon: str = Field("quarterly", description="Time horizon: weekly, monthly, quarterly, annual")
    include_predictions: bool = Field(True, description="Include predictive insights")
    learning_mode: bool = Field(True, description="Enable learning mode for future improvements")

    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        allowed_types = ['competitive', 'market', 'performance', 'strategic', 'trend', 'opportunity']
        if v not in allowed_types:
            raise ValueError(f"Analysis type must be one of: {', '.join(allowed_types)}")
        return v


class LearningFeedbackRequest(BaseModel):
    """Request model for providing learning feedback."""
    insight_id: str = Field(..., description="ID of the insight to provide feedback on")
    feedback_type: str = Field(..., description="Feedback type: accuracy, usefulness, implementation")
    rating: float = Field(..., description="Rating from 0.0 to 1.0")
    comments: Optional[str] = Field(None, description="Additional feedback comments")
    outcome_data: Optional[Dict[str, Any]] = Field(None, description="Actual outcome data")

    @validator('rating')
    def validate_rating(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Rating must be between 0.0 and 1.0")
        return v


class PersonalizedRecommendationRequest(BaseModel):
    """Request model for personalized recommendations."""
    recommendation_type: str = Field(..., description="Type: content, strategy, optimization, competitive")
    current_context: Dict[str, Any] = Field(..., description="Current business context")
    priority_level: str = Field("medium", description="Priority: low, medium, high, urgent")
    consider_history: bool = Field(True, description="Consider historical performance")
    learning_preferences: Optional[Dict[str, Any]] = Field(None, description="User learning preferences")


@router.post("/strategic-ledger", response_model=StrategicLedgerEntry)
async def create_strategic_entry(
    entry_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StrategicLedgerEntry:
    """
    Create a new strategic ledger entry.
    
    Records strategic insights, decisions, outcomes, and lessons learned
    to build institutional knowledge and enable continuous learning.
    """
    try:
        entry_id = str(uuid.uuid4())
        
        # Process and validate entry data
        processed_entry = await knowledge_engine_service.process_strategic_entry(
            entry_data=entry_data,
            user_id=current_user.id,
            entry_id=entry_id,
            db=db
        )
        
        # Extract key insights and patterns
        insights = await knowledge_engine_service.extract_strategic_insights(
            entry_data=processed_entry,
            historical_context=await knowledge_engine_service.get_historical_context(current_user.id, db)
        )
        
        # Update learning models
        background_tasks.add_task(
            knowledge_engine_service.update_learning_models,
            user_id=current_user.id,
            entry_data=processed_entry,
            insights=insights
        )
        
        return StrategicLedgerEntry(
            entry_id=entry_id,
            category=entry_data.get("category", "insight"),
            title=entry_data.get("title", "Strategic Entry"),
            content=entry_data.get("content", ""),
            tags=entry_data.get("tags", []),
            confidence_score=insights.get("confidence_score", 0.8),
            business_impact=entry_data.get("business_impact", "medium"),
            source_data=entry_data.get("source_data", {}),
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error creating strategic entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create strategic entry: {str(e)}")


@router.get("/strategic-ledger", response_model=Dict[str, List[StrategicLedgerEntry]])
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"strategic_ledger:{kwargs.get('current_user').id}:{kwargs.get('category', 'all')}")
async def get_strategic_ledger(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, description="Maximum number of entries to return"),
    time_range: str = Query("all", description="Time range: 7d, 30d, 90d, all"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, List[StrategicLedgerEntry]]:
    """
    Retrieve strategic ledger entries with filtering and analysis.
    
    Returns organized strategic knowledge with insights, patterns,
    and learning outcomes to guide decision-making.
    """
    try:
        entries = await knowledge_engine_service.get_strategic_entries(
            user_id=current_user.id,
            category=category,
            limit=limit,
            time_range=time_range,
            db=db
        )
        
        # Analyze patterns and trends
        pattern_analysis = await knowledge_engine_service.analyze_entry_patterns(
            entries=entries,
            user_id=current_user.id
        )
        
        # Generate insights from the ledger
        ledger_insights = await knowledge_engine_service.generate_ledger_insights(
            entries=entries,
            pattern_analysis=pattern_analysis
        )
        
        return {
            "entries": entries,
            "pattern_analysis": pattern_analysis,
            "insights": ledger_insights,
            "summary": {
                "total_entries": len(entries),
                "categories": pattern_analysis.get("category_distribution", {}),
                "confidence_trend": pattern_analysis.get("confidence_trend", {}),
                "impact_distribution": pattern_analysis.get("impact_distribution", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving strategic ledger: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve strategic ledger: {str(e)}")


@router.post("/generate-intelligence", response_model=Dict[str, Any])
@cache(expire=3600, key_builder=lambda func, *args, **kwargs: f"intelligence:{hash(str(kwargs.get('request').__dict__))}:{kwargs.get('current_user').id}")
async def generate_strategic_intelligence(
    request: IntelligenceGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate strategic intelligence using institutional knowledge.
    
    Leverages accumulated knowledge, patterns, and learning to generate
    actionable intelligence for strategic decision-making.
    """
    try:
        intelligence_id = str(uuid.uuid4())
        
        # Gather relevant historical data and context
        historical_context = await knowledge_engine_service.gather_intelligence_context(
            user_id=current_user.id,
            analysis_type=request.analysis_type,
            data_sources=request.data_sources,
            time_horizon=request.time_horizon,
            db=db
        )
        
        # Generate intelligence using AI and accumulated knowledge
        intelligence_results = await knowledge_engine_service.generate_intelligence(
            analysis_type=request.analysis_type,
            data_sources=request.data_sources,
            focus_areas=request.focus_areas,
            historical_context=historical_context,
            include_predictions=request.include_predictions
        )
        
        # Apply institutional learning and patterns
        enhanced_intelligence = await knowledge_engine_service.enhance_with_institutional_knowledge(
            base_intelligence=intelligence_results,
            user_context=historical_context,
            learning_patterns=await knowledge_engine_service.get_learning_patterns(current_user.id, db)
        )
        
        # Generate actionable recommendations
        recommendations = await knowledge_engine_service.generate_actionable_recommendations(
            intelligence=enhanced_intelligence,
            user_context=historical_context,
            focus_areas=request.focus_areas
        )
        
        # Update learning models if enabled
        if request.learning_mode:
            background_tasks.add_task(
                knowledge_engine_service.update_intelligence_models,
                user_id=current_user.id,
                intelligence_data=enhanced_intelligence,
                request_context=request.dict()
            )
        
        return {
            "intelligence_id": intelligence_id,
            "analysis_type": request.analysis_type,
            "intelligence": enhanced_intelligence,
            "recommendations": recommendations,
            "confidence_metrics": {
                "overall_confidence": enhanced_intelligence.get("confidence_score", 0.8),
                "data_quality": enhanced_intelligence.get("data_quality_score", 0.85),
                "prediction_confidence": enhanced_intelligence.get("prediction_confidence", 0.75),
                "historical_validation": enhanced_intelligence.get("historical_validation", 0.82)
            },
            "learning_insights": enhanced_intelligence.get("learning_insights", {}),
            "implementation_priority": await knowledge_engine_service.calculate_implementation_priority(
                recommendations=recommendations,
                user_context=historical_context
            ),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating strategic intelligence: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate strategic intelligence: {str(e)}")


@router.post("/learning-feedback", response_model=Dict[str, Any])
async def provide_learning_feedback(
    feedback: LearningFeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Provide feedback to improve the knowledge engine's learning.
    
    Enables continuous improvement by collecting feedback on insights,
    recommendations, and outcomes to refine future intelligence.
    """
    try:
        feedback_id = str(uuid.uuid4())
        
        # Process feedback and update learning models
        feedback_analysis = await knowledge_engine_service.process_learning_feedback(
            insight_id=feedback.insight_id,
            feedback_type=feedback.feedback_type,
            rating=feedback.rating,
            comments=feedback.comments,
            outcome_data=feedback.outcome_data,
            user_id=current_user.id,
            db=db
        )
        
        # Update model weights and parameters
        background_tasks.add_task(
            knowledge_engine_service.update_learning_parameters,
            user_id=current_user.id,
            feedback_data=feedback_analysis,
            insight_id=feedback.insight_id
        )
        
        # Generate learning insights
        learning_insights = await knowledge_engine_service.generate_learning_insights(
            feedback_analysis=feedback_analysis,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "feedback_id": feedback_id,
            "feedback_processed": True,
            "learning_impact": feedback_analysis.get("learning_impact", {}),
            "model_updates": feedback_analysis.get("model_updates", []),
            "improvement_suggestions": learning_insights.get("suggestions", []),
            "confidence_adjustments": feedback_analysis.get("confidence_adjustments", {}),
            "validation_status": feedback_analysis.get("validation_status", "processed"),
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing learning feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process learning feedback: {str(e)}")


@router.get("/personalized-recommendations", response_model=Dict[str, Any])
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"recommendations:{kwargs.get('current_user').id}:{kwargs.get('recommendation_type', 'all')}")
async def get_personalized_recommendations(
    recommendation_type: str = Query("strategic", description="Type of recommendations to generate"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority level"),
    limit: int = Query(10, description="Maximum number of recommendations"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get personalized recommendations based on institutional knowledge.
    
    Provides tailored recommendations using accumulated learning,
    user patterns, and strategic context for optimal decision-making.
    """
    try:
        # Get user's context and history
        user_context = await knowledge_engine_service.build_user_context(
            user_id=current_user.id,
            db=db
        )
        
        # Generate personalized recommendations
        recommendations = await knowledge_engine_service.generate_personalized_recommendations(
            user_id=current_user.id,
            recommendation_type=recommendation_type,
            user_context=user_context,
            priority_filter=priority_filter,
            limit=limit,
            db=db
        )
        
        # Rank recommendations by relevance and impact
        ranked_recommendations = await knowledge_engine_service.rank_recommendations(
            recommendations=recommendations,
            user_context=user_context,
            historical_performance=await knowledge_engine_service.get_historical_performance(current_user.id, db)
        )
        
        # Generate implementation guidance
        implementation_guidance = await knowledge_engine_service.generate_implementation_guidance(
            recommendations=ranked_recommendations,
            user_context=user_context
        )
        
        return {
            "recommendation_type": recommendation_type,
            "recommendations": ranked_recommendations,
            "implementation_guidance": implementation_guidance,
            "personalization_factors": {
                "user_preferences": user_context.get("preferences", {}),
                "historical_success_patterns": user_context.get("success_patterns", {}),
                "risk_tolerance": user_context.get("risk_tolerance", "medium"),
                "learning_style": user_context.get("learning_style", "analytical")
            },
            "confidence_metrics": {
                "recommendation_confidence": ranked_recommendations[0].get("confidence", 0.8) if ranked_recommendations else 0.0,
                "personalization_accuracy": user_context.get("personalization_accuracy", 0.85),
                "historical_validation": user_context.get("historical_validation", 0.80)
            },
            "next_actions": await knowledge_engine_service.suggest_next_actions(
                recommendations=ranked_recommendations,
                user_context=user_context
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate personalized recommendations: {str(e)}")


@router.get("/competitive-intelligence", response_model=Dict[str, Any])
@cache(expire=3600, key_builder=lambda func, *args, **kwargs: f"competitive_intel:{kwargs.get('current_user').id}:{kwargs.get('analysis_depth', 'standard')}")
async def get_competitive_intelligence(
    competitor_domains: List[str] = Query(..., description="Competitor domains to analyze"),
    analysis_depth: str = Query("standard", description="Analysis depth: basic, standard, comprehensive"),
    include_predictions: bool = Query(True, description="Include competitive predictions"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate comprehensive competitive intelligence.
    
    Leverages institutional knowledge and learning to provide deep
    competitive insights and strategic recommendations.
    """
    try:
        intelligence_id = str(uuid.uuid4())
        
        # Gather competitive intelligence
        competitive_analysis = await knowledge_engine_service.generate_competitive_intelligence(
            competitor_domains=competitor_domains,
            analysis_depth=analysis_depth,
            user_id=current_user.id,
            db=db
        )
        
        # Apply institutional learning patterns
        enhanced_analysis = await knowledge_engine_service.enhance_competitive_analysis(
            base_analysis=competitive_analysis,
            institutional_knowledge=await knowledge_engine_service.get_competitive_patterns(current_user.id, db),
            user_context=await knowledge_engine_service.build_user_context(current_user.id, db)
        )
        
        # Generate competitive predictions if requested
        predictions = {}
        if include_predictions:
            predictions = await knowledge_engine_service.generate_competitive_predictions(
                competitive_analysis=enhanced_analysis,
                historical_patterns=await knowledge_engine_service.get_competitive_trends(competitor_domains, db)
            )
        
        # Generate strategic counter-measures
        counter_strategies = await knowledge_engine_service.generate_counter_strategies(
            competitive_analysis=enhanced_analysis,
            user_strengths=await knowledge_engine_service.identify_user_strengths(current_user.id, db),
            market_context=await knowledge_engine_service.get_market_context(competitor_domains)
        )
        
        return {
            "intelligence_id": intelligence_id,
            "competitive_analysis": enhanced_analysis,
            "market_positioning": enhanced_analysis.get("market_positioning", {}),
            "threat_assessment": enhanced_analysis.get("threat_assessment", {}),
            "opportunity_analysis": enhanced_analysis.get("opportunities", {}),
            "predictions": predictions,
            "counter_strategies": counter_strategies,
            "learning_insights": enhanced_analysis.get("learning_insights", {}),
            "confidence_metrics": {
                "analysis_confidence": enhanced_analysis.get("confidence_score", 0.8),
                "prediction_confidence": predictions.get("confidence", 0.75) if predictions else 0.0,
                "strategic_relevance": enhanced_analysis.get("strategic_relevance", 0.85)
            },
            "monitoring_recommendations": await knowledge_engine_service.generate_monitoring_recommendations(
                competitors=competitor_domains,
                key_metrics=enhanced_analysis.get("key_metrics", [])
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating competitive intelligence: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate competitive intelligence: {str(e)}")


@router.get("/learning-analytics", response_model=Dict[str, Any])
@cache(expire=1800, key_builder=lambda func, *args, **kwargs: f"learning_analytics:{kwargs.get('current_user').id}")
async def get_learning_analytics(
    time_period: str = Query("30d", description="Time period for analytics: 7d, 30d, 90d"),
    include_predictions: bool = Query(True, description="Include learning predictions"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get learning analytics and model performance metrics.
    
    Provides insights into how well the knowledge engine is learning
    and improving over time, with performance metrics and trends.
    """
    try:
        # Get learning performance metrics
        learning_metrics = await knowledge_engine_service.get_learning_metrics(
            user_id=current_user.id,
            time_period=time_period,
            db=db
        )
        
        # Analyze model performance trends
        performance_trends = await knowledge_engine_service.analyze_performance_trends(
            user_id=current_user.id,
            time_period=time_period,
            db=db
        )
        
        # Get accuracy improvements over time
        accuracy_trends = await knowledge_engine_service.calculate_accuracy_trends(
            user_id=current_user.id,
            time_period=time_period,
            db=db
        )
        
        # Generate learning predictions if requested
        learning_predictions = {}
        if include_predictions:
            learning_predictions = await knowledge_engine_service.predict_learning_improvements(
                learning_metrics=learning_metrics,
                performance_trends=performance_trends,
                user_id=current_user.id
            )
        
        return {
            "analytics_period": time_period,
            "learning_metrics": learning_metrics,
            "performance_trends": performance_trends,
            "accuracy_improvements": accuracy_trends,
            "model_effectiveness": {
                "recommendation_success_rate": learning_metrics.get("recommendation_success_rate", 0.0),
                "prediction_accuracy": learning_metrics.get("prediction_accuracy", 0.0),
                "user_satisfaction": learning_metrics.get("user_satisfaction", 0.0),
                "learning_velocity": learning_metrics.get("learning_velocity", 0.0)
            },
            "learning_predictions": learning_predictions,
            "optimization_opportunities": await knowledge_engine_service.identify_optimization_opportunities(
                learning_metrics=learning_metrics,
                performance_trends=performance_trends
            ),
            "knowledge_growth": {
                "total_insights": learning_metrics.get("total_insights", 0),
                "validated_patterns": learning_metrics.get("validated_patterns", 0),
                "confidence_improvements": learning_metrics.get("confidence_improvements", {}),
                "domain_expertise_level": learning_metrics.get("domain_expertise", "developing")
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting learning analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get learning analytics: {str(e)}")


@router.post("/knowledge-synthesis", response_model=Dict[str, Any])
async def synthesize_knowledge(
    synthesis_request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Synthesize knowledge from multiple sources and contexts.
    
    Combines insights from various sources to create higher-level
    strategic understanding and actionable intelligence.
    """
    try:
        synthesis_id = str(uuid.uuid4())
        
        # Gather all relevant knowledge sources
        knowledge_sources = await knowledge_engine_service.gather_knowledge_sources(
            user_id=current_user.id,
            synthesis_request=synthesis_request,
            db=db
        )
        
        # Perform knowledge synthesis
        synthesized_knowledge = await knowledge_engine_service.synthesize_knowledge(
            knowledge_sources=knowledge_sources,
            synthesis_context=synthesis_request,
            user_id=current_user.id
        )
        
        # Generate meta-insights
        meta_insights = await knowledge_engine_service.generate_meta_insights(
            synthesized_knowledge=synthesized_knowledge,
            user_context=await knowledge_engine_service.build_user_context(current_user.id, db)
        )
        
        # Create actionable synthesis
        actionable_synthesis = await knowledge_engine_service.create_actionable_synthesis(
            synthesized_knowledge=synthesized_knowledge,
            meta_insights=meta_insights,
            synthesis_request=synthesis_request
        )
        
        # Update knowledge base with synthesis results
        background_tasks.add_task(
            knowledge_engine_service.update_knowledge_base,
            user_id=current_user.id,
            synthesis_results=actionable_synthesis,
            synthesis_id=synthesis_id
        )
        
        return {
            "synthesis_id": synthesis_id,
            "synthesized_knowledge": actionable_synthesis,
            "meta_insights": meta_insights,
            "knowledge_connections": synthesized_knowledge.get("connections", []),
            "strategic_implications": actionable_synthesis.get("strategic_implications", {}),
            "confidence_metrics": {
                "synthesis_confidence": actionable_synthesis.get("confidence_score", 0.8),
                "source_reliability": synthesized_knowledge.get("source_reliability", 0.85),
                "insight_novelty": meta_insights.get("novelty_score", 0.7)
            },
            "implementation_roadmap": await knowledge_engine_service.generate_synthesis_roadmap(
                actionable_synthesis=actionable_synthesis,
                user_context=await knowledge_engine_service.build_user_context(current_user.id, db)
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error synthesizing knowledge: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to synthesize knowledge: {str(e)}")