"""
API endpoints for the SGE Readiness Engine (Pillar 5).

This module provides endpoints for preparing for AI-generated search results,
including SGE trigger analysis, source citation optimization, and conversational gap analysis.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.services.sge_readiness import sge_readiness_service

router = APIRouter()
logger = logging.getLogger(__name__)


class SGEOptimizationRequest(BaseModel):
    content: str = Field(..., description="Content to optimize for SGE")
    target_queries: List[str] = Field(..., description="Target search queries")
    content_type: str = Field(default="article", description="Type of content")


@router.post("/optimize-content")
async def optimize_content_for_sge(
    request: SGEOptimizationRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Optimize content for Search Generative Experience (SGE).
    
    This endpoint uses AI to analyze and optimize content for better performance
    in AI-powered search results and increased likelihood of being cited by SGE.
    
    Args:
        request: SGE optimization parameters
        current_user: The authenticated user
        db: Database session
        
    Returns:
        SGE optimization analysis and improved content
    """
    try:
        result = await sge_readiness_service.optimize_content_for_sge(
            content=request.content,
            target_queries=request.target_queries,
            content_type=request.content_type,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "success": True,
            "data": result,
            "is_service_configured": sge_readiness_service.is_configured()
        }
        
    except ValueError as e:
        logger.error(f"SGE optimization validation error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid request data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"SGE optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"SGE optimization failed: {str(e)}")


@router.get("/triggers")
async def analyze_sge_triggers(
    keywords: List[str] = Query(..., description="Keywords to analyze for SGE triggers"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Analyze keywords for SGE triggers.
    
    This endpoint analyzes the provided keywords to determine which are likely to
    trigger Google's Search Generative Experience (SGE) AI-generated answers.
    
    Args:
        keywords: List of keywords to analyze
        current_user: The authenticated user
        
    Returns:
        Analysis of SGE triggers for the provided keywords
    """
    try:
        result = await sge_readiness_service.analyze_sge_triggers(
            keywords=keywords
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        logger.error(f"SGE triggers analysis validation error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid keywords: {str(e)}"
        )
    except Exception as e:
        logger.error(f"SGE triggers analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"SGE triggers analysis failed: {str(e)}")


@router.get("/citations")
async def analyze_source_citations(
    keywords: List[str] = Query(..., description="Keywords to analyze for source citations"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Analyze source citations in SGE results.
    
    This endpoint analyzes the sources cited in AI answers for the provided keywords
    and identifies the attributes of those sources.
    
    Args:
        keywords: List of keywords to analyze
        current_user: The authenticated user
        
    Returns:
        Analysis of source citations in SGE results
    """
    try:
        result = await sge_readiness_service.analyze_source_citations(
            keywords=keywords
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        logger.error(f"Source citations analysis validation error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid keywords: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Source citations analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Source citations analysis failed: {str(e)}")


@router.get("/conversational-gaps")
async def analyze_conversational_gaps(
    topic: str = Query(..., description="Topic to analyze for conversational gaps"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Any:
    """
    Analyze conversational gaps for a topic.
    
    This endpoint identifies gaps in content coverage that could be addressed
    to better serve conversational search queries and SGE opportunities.
    
    Args:
        topic: Topic to analyze
        current_user: The authenticated user
        
    Returns:
        Analysis of conversational gaps and opportunities
    """
    try:
        result = await sge_readiness_service.analyze_conversational_gaps(
            topic=topic
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        logger.error(f"Conversational gaps analysis validation error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid topic: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Conversational gaps analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Conversational gaps analysis failed: {str(e)}")


@router.post("/sge-monitor")
async def create_sge_monitor(
    monitor_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create an SGE monitoring task.
    
    This endpoint creates a monitoring task to track changes in SGE behavior
    for specified keywords over time.
    
    Args:
        monitor_data: Monitor configuration data
        background_tasks: FastAPI background tasks
        current_user: The authenticated user
        
    Returns:
        Created monitor with ID and initial status
    """
    try:
        result = await sge_readiness_service.create_sge_monitor(
            monitor_data=monitor_data,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "success": True,
            "data": result,
            "message": "SGE monitor created successfully"
        }
        
    except ValueError as e:
        logger.error(f"SGE monitor creation validation error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid monitor data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"SGE monitor creation error: {e}")
        raise HTTPException(status_code=500, detail=f"SGE monitor creation failed: {str(e)}")


@router.get("/sge-monitor/{monitor_id}")
async def get_sge_monitor(
    monitor_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get SGE monitor results.

    This endpoint returns the current status and results of an SGE monitoring task.

    Args:
        monitor_id: ID of the monitor
        current_user: The authenticated user
        db: Database session

    Returns:
        Monitor results and status
    """
    try:
        result = await sge_readiness_service.get_sge_monitor(
            monitor_id=monitor_id,
            user_id=current_user.id,
            db=db
        )

        return {
            "success": True,
            "data": result
        }

    except ValueError as e:
        logger.error(f"SGE monitor retrieval error: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Monitor not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"SGE monitor retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve SGE monitor: {str(e)}")

