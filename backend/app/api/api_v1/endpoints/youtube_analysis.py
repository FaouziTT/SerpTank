"""
API endpoints for YouTube Data integration.

This module provides endpoints for YouTube video analysis, channel insights,
and video SEO optimization.
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.models.user import User
from app.services.youtube_data import youtube_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search-videos")
async def search_videos(
    request: Request,
    query: str = Query(..., description="Search query"),
    max_results: int = Query(10, description="Maximum number of results (1-50)"),
    order: str = Query("relevance", description="Search order (relevance, date, rating, viewCount, title)"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Search for videos on YouTube.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        order: Search order
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Video search results
    """
    try:
        search_results = await youtube_client.search_videos(
            query=query,
            max_results=max_results,
            order=order
        )
        
        return {
            "success": True,
            "data": search_results
        }
        
    except Exception as e:
        logger.error(f"Error searching videos: {e}")
        if "not configured" in str(e):
            return {
                "success": False,
                "error": "YouTube Data API not configured",
                "data": {
                    "query": query,
                    "videos": [],
                    "total_results": 0,
                    "note": "YouTube Data API key required for real data"
                }
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channel-info")
async def get_channel_info(
    request: Request,
    channel_id: Optional[str] = Query(None, description="YouTube channel ID"),
    channel_username: Optional[str] = Query(None, description="YouTube channel username"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get channel information and statistics.
    
    Args:
        channel_id: YouTube channel ID
        channel_username: YouTube channel username
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Channel information and statistics
    """
    try:
        if not channel_id and not channel_username:
            raise HTTPException(status_code=400, detail="Either channel_id or channel_username must be provided")
        
        channel_info = await youtube_client.get_channel_info(
            channel_id=channel_id,
            channel_username=channel_username
        )
        
        return {
            "success": True,
            "data": channel_info
        }
        
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        if "not configured" in str(e):
            return {
                "success": False,
                "error": "YouTube Data API not configured",
                "data": {
                    "channel_id": channel_id or channel_username,
                    "statistics": {
                        "subscriber_count": 0,
                        "video_count": 0,
                        "view_count": 0
                    },
                    "note": "YouTube Data API key required for real data"
                }
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-videos")
async def get_trending_videos(
    request: Request,
    category_id: Optional[str] = Query(None, description="Video category ID"),
    region_code: str = Query("US", description="Region code (US, GB, CA, etc.)"),
    max_results: int = Query(25, description="Maximum number of results"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get trending videos.
    
    Args:
        category_id: Video category ID
        region_code: Region code
        max_results: Maximum number of results
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Trending videos data
    """
    try:
        trending_data = await youtube_client.get_trending_videos(
            category_id=category_id,
            region_code=region_code,
            max_results=max_results
        )
        
        return {
            "success": True,
            "data": trending_data
        }
        
    except Exception as e:
        logger.error(f"Error getting trending videos: {e}")
        if "not configured" in str(e):
            return {
                "success": False,
                "error": "YouTube Data API not configured",
                "data": {
                    "region_code": region_code,
                    "videos": [],
                    "total_results": 0,
                    "note": "YouTube Data API key required for real data"
                }
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video-seo-analysis/{video_id}")
async def analyze_video_seo(
    request: Request,
    video_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Analyze video SEO factors.
    
    Args:
        video_id: YouTube video ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Video SEO analysis
    """
    try:
        seo_analysis = await youtube_client.analyze_video_seo(video_id=video_id)
        
        return {
            "success": True,
            "data": seo_analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing video SEO: {e}")
        if "not configured" in str(e):
            return {
                "success": False,
                "error": "YouTube Data API not configured",
                "data": {
                    "video_id": video_id,
                    "seo_score": 0,
                    "recommendations": ["YouTube Data API key required for real analysis"],
                    "note": "YouTube Data API key required for real data"
                }
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitor-analysis")
async def get_competitor_analysis(
    request: Request,
    competitor_channels: str = Query(..., description="Comma-separated list of competitor channel IDs"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Analyze competitor YouTube channels.
    
    Args:
        competitor_channels: Comma-separated list of competitor channel IDs
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Competitor analysis data
    """
    try:
        channel_ids = [c.strip() for c in competitor_channels.split(',')]
        
        competitor_data = []
        for channel_id in channel_ids:
            try:
                channel_info = await youtube_client.get_channel_info(channel_id=channel_id)
                competitor_data.append(channel_info)
            except Exception as e:
                logger.warning(f"Error getting data for channel {channel_id}: {e}")
                competitor_data.append({
                    "channel_id": channel_id,
                    "error": str(e)
                })
        
        # Calculate competitive insights
        total_subscribers = sum(
            c.get('statistics', {}).get('subscriber_count', 0) 
            for c in competitor_data 
            if 'statistics' in c
        )
        
        avg_subscribers = total_subscribers / len(competitor_data) if competitor_data else 0
        
        return {
            "success": True,
            "data": {
                "competitors": competitor_data,
                "insights": {
                    "total_competitors": len(channel_ids),
                    "successful_queries": len([c for c in competitor_data if 'statistics' in c]),
                    "total_subscriber_pool": total_subscribers,
                    "average_subscribers": round(avg_subscribers),
                    "top_performer": max(
                        competitor_data, 
                        key=lambda x: x.get('statistics', {}).get('subscriber_count', 0),
                        default={}
                    ).get('title', 'N/A')
                },
                "fetched_at": competitor_data[0].get('fetched_at') if competitor_data else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting competitor analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
