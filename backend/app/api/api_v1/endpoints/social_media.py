"""
API endpoints for Social Media integration.

This module provides endpoints for social media analytics, brand mentions,
and social SEO metrics.
"""
import logging
from datetime import datetime
from typing import Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.models.user import User
from app.services.social_media import social_media_aggregator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/brand-mentions")
async def get_brand_mentions(
    request: Request,
    brand_name: str = Query(..., description="Brand name to search for"),
    include_hashtags: bool = Query(True, description="Include hashtag variations"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get brand mentions across social media platforms.
    
    Args:
        brand_name: Brand name to search for
        include_hashtags: Whether to include hashtag variations
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Brand mentions data
    """
    try:
        mentions_data = await social_media_aggregator.get_brand_mentions(
            brand_name=brand_name,
            include_hashtags=include_hashtags
        )
        
        return {
            "success": True,
            "data": mentions_data
        }
        
    except Exception as e:
        logger.error(f"Error getting brand mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/social-seo-metrics")
async def get_social_seo_metrics(
    request: Request,
    domain: str = Query(..., description="Website domain"),
    brand_name: str = Query(..., description="Brand name"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get social SEO metrics that impact search rankings.
    
    Args:
        domain: Website domain
        brand_name: Brand name
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Social SEO metrics
    """
    try:
        seo_metrics = await social_media_aggregator.get_social_seo_metrics(
            domain=domain,
            brand_name=brand_name
        )
        
        return {
            "success": True,
            "data": seo_metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting social SEO metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twitter/mentions")
async def get_twitter_mentions(
    request: Request,
    query: str = Query(..., description="Search query"),
    max_results: int = Query(10, description="Maximum number of results (10-100)"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Search for mentions on Twitter/X.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Twitter mentions data
    """
    try:
        mentions_data = await social_media_aggregator.twitter.search_mentions(
            query=query,
            max_results=max_results
        )
        
        return {
            "success": True,
            "data": mentions_data
        }
        
    except Exception as e:
        logger.error(f"Error getting Twitter mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twitter/hashtag-analytics")
async def get_hashtag_analytics(
    request: Request,
    hashtag: str = Query(..., description="Hashtag to analyze (without #)"),
    max_results: int = Query(50, description="Maximum number of results"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get analytics for a specific hashtag on Twitter/X.
    
    Args:
        hashtag: Hashtag to analyze
        max_results: Maximum number of results
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Hashtag analytics data
    """
    try:
        analytics_data = await social_media_aggregator.twitter.get_hashtag_analytics(
            hashtag=hashtag,
            max_results=max_results
        )
        
        return {
            "success": True,
            "data": analytics_data
        }
        
    except Exception as e:
        logger.error(f"Error getting hashtag analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facebook/page-insights")
async def get_facebook_page_insights(
    request: Request,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get Facebook page insights and metrics.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Facebook page insights data
    """
    try:
        insights_data = await social_media_aggregator.facebook.get_page_insights()
        
        return {
            "success": True,
            "data": insights_data
        }
        
    except Exception as e:
        logger.error(f"Error getting Facebook page insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/linkedin/company-analytics")
async def get_linkedin_company_analytics(
    request: Request,
    company_id: str = Query(..., description="LinkedIn company ID"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get LinkedIn company page analytics.
    
    Args:
        company_id: LinkedIn company ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        LinkedIn company analytics
    """
    try:
        analytics_data = await social_media_aggregator.linkedin.get_company_analytics(
            company_id=company_id
        )
        
        return {
            "success": True,
            "data": analytics_data
        }
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn company analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/social-signals-report")
async def get_social_signals_report(
    request: Request,
    domain: str = Query(..., description="Website domain"),
    brand_name: str = Query(..., description="Brand name"),
    competitor_brands: Optional[str] = Query(None, description="Comma-separated competitor brand names"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get comprehensive social signals report.
    
    Args:
        domain: Website domain
        brand_name: Brand name
        competitor_brands: Comma-separated competitor brand names
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Comprehensive social signals report
    """
    try:
        # Get main brand social signals
        main_brand_data = await social_media_aggregator.get_social_seo_metrics(
            domain=domain,
            brand_name=brand_name
        )
        
        # Get competitor data if provided
        competitor_data = []
        if competitor_brands:
            competitors = [c.strip() for c in competitor_brands.split(',')]
            for competitor in competitors:
                try:
                    comp_data = await social_media_aggregator.get_brand_mentions(
                        brand_name=competitor,
                        include_hashtags=True
                    )
                    competitor_data.append({
                        "brand_name": competitor,
                        "mentions": comp_data['summary']['total_mentions'],
                        "data": comp_data
                    })
                except Exception as e:
                    logger.warning(f"Error getting data for competitor {competitor}: {e}")
                    competitor_data.append({
                        "brand_name": competitor,
                        "error": str(e)
                    })
        
        # Generate comparative insights
        insights = {
            "social_presence_score": main_brand_data['data']['social_seo_metrics']['social_signals_score'],
            "competitor_comparison": competitor_data,
            "recommendations": [
                main_brand_data['data']['social_seo_metrics']['recommendation']
            ]
        }
        
        if competitor_data:
            competitor_scores = [
                c.get('mentions', 0) * 2 for c in competitor_data 
                if 'mentions' in c
            ]
            if competitor_scores:
                avg_competitor_score = sum(competitor_scores) / len(competitor_scores)
                main_score = main_brand_data['data']['social_seo_metrics']['social_signals_score']
                
                if main_score > avg_competitor_score:
                    insights["recommendations"].append("Your social presence is stronger than competitors. Maintain this advantage.")
                else:
                    insights["recommendations"].append("Competitors have stronger social presence. Focus on increasing brand mentions and engagement.")
        
        return {
            "success": True,
            "data": {
                "main_brand": main_brand_data['data'],
                "competitors": competitor_data,
                "insights": insights,
                "fetched_at": main_brand_data['data']['fetched_at']
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting social signals report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track-social-signals")
async def track_social_signals(
    request: Request,
    domain: str = Body(..., description="Website domain to track"),
    brand_name: str = Body(..., description="Primary brand name"),
    competitor_brands: Optional[List[str]] = Body(None, description="List of competitor brand names"),
    track_urls: Optional[List[str]] = Body(None, description="Specific URLs to track social shares"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Track comprehensive social signals for SEO impact.
    
    Args:
        domain: Website domain to track
        brand_name: Primary brand name
        competitor_brands: List of competitor brand names
        track_urls: Specific URLs to track social shares
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Comprehensive social signals tracking data
    """
    try:
        signals_data = await social_media_aggregator.track_social_signals(
            domain=domain,
            brand_name=brand_name,
            competitor_brands=competitor_brands,
            track_urls=track_urls
        )
        
        # Log activity
        from app.services.activity_service import log_seo_activity
        from app.models.activity_feed import ActivityType
        
        await log_seo_activity(
            type=ActivityType.SERP_ANALYZED,
            title=f"Social signals tracked for {brand_name}",
            organization_id=current_user.organization_id,
            data={
                "domain": domain,
                "brand_name": brand_name,
                "signal_strength": signals_data.get('social_signal_strength', {}).get('total_score', 0),
                "grade": signals_data.get('social_signal_strength', {}).get('grade', 'N/A')
            }
        )
        
        return {
            "success": True,
            "data": signals_data
        }
        
    except Exception as e:
        logger.error(f"Error tracking social signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facebook/demographics")
async def get_facebook_demographics(
    request: Request,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get Facebook page audience demographics.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Audience demographics data
    """
    try:
        demographics_data = await social_media_aggregator.facebook.get_page_demographics()
        
        return {
            "success": True,
            "data": demographics_data
        }
        
    except Exception as e:
        logger.error(f"Error getting Facebook demographics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facebook/competitor-analysis")
async def analyze_facebook_competitors(
    request: Request,
    competitor_page_ids: List[str] = Body(..., description="List of competitor Facebook page IDs"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Compare page performance with competitors on Facebook.
    
    Args:
        competitor_page_ids: List of competitor Facebook page IDs
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Comparative analysis data
    """
    try:
        analysis_data = await social_media_aggregator.facebook.get_competitor_analysis(
            competitor_page_ids=competitor_page_ids
        )
        
        return {
            "success": True,
            "data": analysis_data
        }
        
    except Exception as e:
        logger.error(f"Error analyzing Facebook competitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/linkedin/company-updates")
async def get_linkedin_company_updates(
    request: Request,
    company_id: str = Query(..., description="LinkedIn company ID"),
    count: int = Query(10, description="Number of updates to retrieve"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get recent updates from a LinkedIn company page.
    
    Args:
        company_id: LinkedIn company ID
        count: Number of updates to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Company updates data
    """
    try:
        updates_data = await social_media_aggregator.linkedin.search_company_updates(
            company_id=company_id,
            count=count
        )
        
        return {
            "success": True,
            "data": updates_data
        }
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn company updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified-dashboard")
async def get_unified_social_dashboard(
    request: Request,
    domain: str = Query(..., description="Website domain"),
    brand_name: str = Query(..., description="Primary brand name"),
    company_id: Optional[str] = Query(None, description="LinkedIn company ID"),
    include_demographics: bool = Query(False, description="Include Facebook demographics"),
    include_competitors: bool = Query(False, description="Include competitor analysis"),
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get unified social media dashboard data aggregating all platforms.
    
    Args:
        domain: Website domain
        brand_name: Primary brand name
        company_id: LinkedIn company ID (optional)
        include_demographics: Include Facebook demographics
        include_competitors: Include competitor analysis
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Unified social media dashboard data
    """
    try:
        dashboard_data = {
            "brand_name": brand_name,
            "domain": domain,
            "platforms": {},
            "social_signals": {},
            "summary": {
                "total_followers": 0,
                "total_engagement": 0,
                "total_mentions": 0,
                "platforms_active": 0,
                "social_health_score": 0
            },
            "recommendations": [],
            "fetched_at": datetime.now().isoformat()
        }
        
        # Get brand mentions across platforms
        mentions_data = await social_media_aggregator.get_brand_mentions(brand_name, include_hashtags=True)
        dashboard_data["brand_mentions"] = mentions_data
        
        # Twitter/X data
        if 'twitter' in mentions_data.get('platforms', {}):
            twitter_data = mentions_data['platforms']['twitter']
            if 'error' not in twitter_data:
                dashboard_data["platforms"]["twitter"] = {
                    "mentions": len(twitter_data.get('mentions', [])),
                    "hashtag_analytics": mentions_data['platforms'].get('twitter_hashtag', {}),
                    "status": "active"
                }
                dashboard_data["summary"]["total_mentions"] += len(twitter_data.get('mentions', []))
                dashboard_data["summary"]["platforms_active"] += 1
            else:
                dashboard_data["platforms"]["twitter"] = {"status": "not_configured", "error": twitter_data.get('error')}
        
        # Facebook data
        fb_insights = await social_media_aggregator.facebook.get_page_insights()
        if 'error' not in fb_insights:
            fb_data = fb_insights.get('insights', {})
            dashboard_data["platforms"]["facebook"] = {
                "page_name": fb_insights.get('page_info', {}).get('name', ''),
                "followers": fb_data.get('fan_count', 0),
                "engagement": fb_data.get('total_engagement', 0),
                "talking_about": fb_data.get('talking_about_count', 0),
                "top_posts": fb_insights.get('top_posts', []),
                "status": "active"
            }
            dashboard_data["summary"]["total_followers"] += fb_data.get('fan_count', 0)
            dashboard_data["summary"]["total_engagement"] += fb_data.get('total_engagement', 0)
            dashboard_data["summary"]["platforms_active"] += 1
            
            # Include demographics if requested
            if include_demographics:
                demographics = await social_media_aggregator.facebook.get_page_demographics()
                dashboard_data["platforms"]["facebook"]["demographics"] = demographics.get('demographics', {})
        else:
            dashboard_data["platforms"]["facebook"] = {"status": "not_configured", "error": fb_insights.get('error')}
        
        # LinkedIn data
        if company_id:
            linkedin_data = await social_media_aggregator.linkedin.get_company_analytics(company_id)
            if 'error' not in linkedin_data:
                analytics = linkedin_data.get('analytics', {})
                dashboard_data["platforms"]["linkedin"] = {
                    "company_name": linkedin_data.get('company_info', {}).get('name', ''),
                    "followers": analytics.get('follower_count', 0),
                    "share_statistics": analytics.get('share_statistics', {}),
                    "engagement_rate": analytics.get('engagement_rate', 0),
                    "status": "active"
                }
                dashboard_data["summary"]["total_followers"] += analytics.get('follower_count', 0)
                dashboard_data["summary"]["total_engagement"] += analytics.get('share_statistics', {}).get('total_engagement', 0)
                dashboard_data["summary"]["platforms_active"] += 1
                
                # Get recent updates
                updates = await social_media_aggregator.linkedin.search_company_updates(company_id, count=5)
                if 'error' not in updates:
                    dashboard_data["platforms"]["linkedin"]["recent_updates"] = updates.get('updates', [])
            else:
                dashboard_data["platforms"]["linkedin"] = {"status": "not_configured", "error": linkedin_data.get('error')}
        
        # Get social signals analysis
        signals_data = await social_media_aggregator.track_social_signals(
            domain=domain,
            brand_name=brand_name,
            competitor_brands=None,
            track_urls=None
        )
        dashboard_data["social_signals"] = signals_data.get('social_signal_strength', {})
        
        # Calculate overall social health score
        active_platforms = dashboard_data["summary"]["platforms_active"]
        if active_platforms > 0:
            # Weighted scoring
            engagement_score = min(dashboard_data["summary"]["total_engagement"] / 100, 30)  # Max 30
            follower_score = min(dashboard_data["summary"]["total_followers"] / 1000, 30)  # Max 30
            mention_score = min(dashboard_data["summary"]["total_mentions"] * 2, 20)  # Max 20
            platform_score = active_platforms * 6.67  # Max 20 for 3 platforms
            
            health_score = engagement_score + follower_score + mention_score + platform_score
            dashboard_data["summary"]["social_health_score"] = round(health_score, 2)
            
            # Generate recommendations
            if health_score < 50:
                dashboard_data["recommendations"].append("Your social media presence needs improvement. Focus on increasing engagement and follower growth.")
            if active_platforms < 3:
                dashboard_data["recommendations"].append(f"You're only active on {active_platforms} platform(s). Consider expanding to more social networks.")
            if dashboard_data["summary"]["total_engagement"] < 100:
                dashboard_data["recommendations"].append("Low engagement detected. Create more compelling content and interact with your audience.")
            if dashboard_data["summary"]["total_mentions"] < 10:
                dashboard_data["recommendations"].append("Low brand mentions. Implement a social media marketing campaign to increase brand awareness.")
        
        # Competitor analysis if requested
        if include_competitors and fb_insights.get('page_id'):
            # Use default competitors for demo
            competitor_analysis = await social_media_aggregator.facebook.get_competitor_analysis(
                competitor_page_ids=["meta", "google", "microsoft"]  # Example competitor IDs
            )
            dashboard_data["competitor_analysis"] = competitor_analysis
        
        # Log activity
        from app.services.activity_service import log_seo_activity
        from app.models.activity_feed import ActivityType
        
        await log_seo_activity(
            type=ActivityType.SERP_ANALYZED,
            title=f"Social media dashboard viewed for {brand_name}",
            organization_id=current_user.organization_id,
            data={
                "domain": domain,
                "brand_name": brand_name,
                "platforms_active": active_platforms,
                "health_score": dashboard_data["summary"]["social_health_score"]
            }
        )
        
        return {
            "success": True,
            "data": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Error getting unified social dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
