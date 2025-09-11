"""
API endpoints for the Unified Profitability Engine (Pillar 2).

This module provides endpoints for connecting SEO performance to business results,
including data fusion, profit attribution mapping, and sales enablement.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.core.config import settings
from app.core.rate_limit_dependencies import rate_limit_data_intensive
from app.models.user import User # Keep this import
from app.models.project import Project
from app.services.google_analytics4 import ga4_service, GoogleAnalytics4Service # Use the new GA4 service
from app.services.oauth_service import oauth_service
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache.decorator import cache

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_project_with_ga4(
    project_id: int,
    current_user: User,
    db: AsyncSession
) -> tuple[Project, GoogleAnalytics4Service]:
    """Get project and validate GA4 configuration for the current user."""
    # Get project and verify ownership
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if analytics is enabled for this project
    if not project.analytics_enabled:
        raise HTTPException(
            status_code=400,
            detail="Analytics tracking is disabled for this project"
        )
    
    # First, check if user has OAuth access to GA4
    access_token = await oauth_service.get_valid_access_token(db, current_user.id)
    has_analytics_scope = oauth_service.has_scope(current_user, 'https://www.googleapis.com/auth/analytics.readonly')
    
    # If user has OAuth access, use that
    if access_token and has_analytics_scope:
        # Check if we have a property ID for this project
        if not project.ga4_property_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "GA4 property not selected",
                    "message": "Please select a GA4 property in project settings",
                    "setup_required": True,
                    "project_id": project_id,
                    "oauth_connected": True
                }
            )
        
        # Create GA4 service with OAuth token
        project_ga4_service = GoogleAnalytics4Service(
            property_id=project.ga4_property_id,
            access_token=access_token
        )
    else:
        # Fall back to API key authentication
        if not project.ga4_configured or not project.ga4_property_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Google Analytics 4 not configured",
                    "message": "Please configure GA4 OAuth or API credentials",
                    "setup_required": True,
                    "project_id": project_id,
                    "oauth_connected": False,
                    "oauth_url": "/api/v1/oauth/google/authorize?scopes=analytics"
                }
            )
        
        # Create project-specific GA4 service with API key
        project_ga4_service = GoogleAnalytics4Service(property_id=project.ga4_property_id)
        
        # Verify GA4 service is properly configured
        if not project_ga4_service.is_configured():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "GA4 authentication not configured",
                    "message": "Please configure GA4 service account or API credentials",
                    "auth_required": True
                }
            )
    
    return project, project_ga4_service


class ProfitabilityRequest(BaseModel):
    start_date: str = Field(default="30daysAgo", description="Start date for analysis")
    end_date: str = Field(default="today", description="End date for analysis")
    include_forecasting: bool = Field(default=True, description="Include revenue forecasting")


@router.post("/{project_id}/overview")
# @cache(expire=900, key_builder=lambda func, *args, **kwargs: f"profitability:overview:{kwargs.get('project_id')}:{kwargs.get('payload').start_date}:{kwargs.get('payload').end_date}:{kwargs.get('current_user').id}")
async def get_profitability_overview(
    project_id: int,
    payload: ProfitabilityRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_data_intensive)  # 10 requests per minute
) -> Any:
    """
    Get a comprehensive overview of SEO profitability metrics.
    
    This endpoint returns key profitability metrics using Google Analytics 4 data,
    including ROI, revenue attribution, conversion tracking, and profit margins.
    
    Args:
        payload: Profitability analysis parameters
        request: The request object
        current_user: The authenticated user
        
    Returns:
        Comprehensive profitability analysis with real GA4 data
    """
    try:
        # Get project and validate GA4 configuration
        try:
            project, project_ga4_service = await get_project_with_ga4(
                project_id, current_user, db
            )
        except HTTPException as e:
            # Handle GA4 not configured error with empty data response
            if e.status_code == 400 and "not configured" in str(e.detail):
                return {
                    "setup_required": True,
                    "error": "Google Analytics 4 not configured",
                    "message": "Please configure GA4 OAuth or API credentials",
                    "project_id": project_id,
                    "oauth_connected": False,
                    "oauth_url": "/api/v1/oauth/google/authorize?scopes=analytics",
                    "revenue_data": {
                        "total_revenue": 0,
                        "organic_revenue": 0,
                        "conversion_rate": 0,
                        "transactions": 0
                    },
                    "organic_data": {
                        "sessions": 0,
                        "users": 0,
                        "bounce_rate": 0,
                        "avg_session_duration": 0
                    },
                    "roi_analysis": {
                        "roi": 0,
                        "profit_margin": 0,
                        "cost_per_acquisition": 0
                    }
                }
            else:
                raise
        
        # Get revenue metrics from project's GA4
        revenue_data = await project_ga4_service.get_revenue_metrics(
            start_date=payload.start_date,
            end_date=payload.end_date
        )
        
        # Get organic performance data
        organic_data = await project_ga4_service.get_organic_performance(
            start_date=payload.start_date,
            end_date=payload.end_date
        )
        
        # Get conversion funnel data
        funnel_data = await project_ga4_service.get_conversion_funnel(
            start_date=payload.start_date,
            end_date=payload.end_date
        )
        
        # Calculate profitability metrics
        profitability_analysis = _calculate_profitability_metrics(
            revenue_data, organic_data, funnel_data
        )
        
        return {
            "success": True,
            "project_id": project_id,
            "project_name": project.name,
            "data": {
                "overview": profitability_analysis,
                "revenue_metrics": revenue_data,
                "organic_performance": organic_data,
                "conversion_funnel": funnel_data,
                "analysis_period": {
                    "start_date": payload.start_date,
                    "end_date": payload.end_date
                }
            },
            "is_ga4_configured": project.ga4_configured,
            "ga4_property_id": project.ga4_property_id,
            "data_source": "Google Analytics 4"
        }
        
    except ValueError as e:
        # Handle configuration errors
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Profitability overview error: {e}")
        raise HTTPException(status_code=500, detail=f"Profitability analysis failed: {str(e)}")


@router.get("/{project_id}/revenue-attribution")
async def get_revenue_attribution(
    project_id: int,
    request: Request,
    start_date: str = Query(default="30daysAgo", description="Start date"),
    end_date: str = Query(default="today", description="End date"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get detailed revenue attribution analysis.
    
    This endpoint analyzes how different traffic sources and channels
    contribute to revenue generation.
    
    Args:
        request: The request object
        start_date: Start date for analysis
        end_date: End date for analysis
        current_user: The authenticated user
        
    Returns:
        Revenue attribution analysis by traffic source
    """
    try:
        # Get project and validate GA4 configuration
        project, project_ga4_service = await get_project_with_ga4(
            project_id, current_user, db
        )
        
        # Get revenue metrics with source breakdown
        revenue_data = await project_ga4_service.get_revenue_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate attribution percentages
        source_breakdown = revenue_data.get("source_breakdown", {})
        total_revenue = revenue_data.get("total_revenue", 0)
        
        attribution_analysis = []
        for source, data in source_breakdown.items():
            source_revenue = data.get("revenue", 0)
            attribution_percentage = (source_revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            attribution_analysis.append({
                "source": source,
                "revenue": source_revenue,
                "conversions": data.get("conversions", 0),
                "sessions": data.get("sessions", 0),
                "attribution_percentage": round(attribution_percentage, 2),
                "revenue_per_session": source_revenue / data.get("sessions", 1),
                "conversion_rate": (data.get("conversions", 0) / data.get("sessions", 1) * 100) if data.get("sessions", 0) > 0 else 0
            })
        
        # Sort by revenue descending
        attribution_analysis.sort(key=lambda x: x["revenue"], reverse=True)
        
        return {
            "success": True,
            "data": {
                "total_revenue": total_revenue,
                "attribution_analysis": attribution_analysis,
                "top_revenue_source": attribution_analysis[0] if attribution_analysis else None,
                "organic_share": next(
                    (item["attribution_percentage"] for item in attribution_analysis 
                     if "organic" in item["source"].lower()), 0
                )
            },
            "is_ga4_configured": ga4_service.is_configured()
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Revenue attribution error: {e}")
        raise HTTPException(status_code=500, detail=f"Revenue attribution analysis failed: {str(e)}")


@router.get("/conversion-tracking")
async def get_conversion_tracking(
    request: Request,
    start_date: str = Query(default="30daysAgo", description="Start date"),
    end_date: str = Query(default="today", description="End date"),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get detailed conversion tracking and funnel analysis.
    
    This endpoint provides comprehensive conversion funnel analysis
    and optimization recommendations.
    
    Args:
        request: The request object
        start_date: Start date for analysis
        end_date: End date for analysis
        current_user: The authenticated user
        
    Returns:
        Conversion tracking and funnel optimization insights
    """
    try:
        # Get conversion funnel data
        funnel_data = await ga4_service.get_conversion_funnel(
            start_date=start_date,
            end_date=end_date
        )
        
        # Get traffic analytics for context
        traffic_data = await ga4_service.get_traffic_analytics(
            start_date=start_date,
            end_date=end_date
        )
        
        # Generate optimization recommendations
        recommendations = _generate_conversion_recommendations(funnel_data, traffic_data)
        
        return {
            "success": True,
            "data": {
                "funnel_analysis": funnel_data,
                "traffic_context": {
                    "total_sessions": traffic_data.get("total_sessions", 0),
                    "total_users": traffic_data.get("total_users", 0),
                    "device_breakdown": traffic_data.get("device_breakdown", {})
                },
                "optimization_recommendations": recommendations,
                "analysis_period": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            },
            "is_ga4_configured": project.ga4_configured,
            "ga4_property_id": project.ga4_property_id,
            "project_id": project_id,
            "project_name": project.name
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Conversion tracking error: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion tracking analysis failed: {str(e)}")


@router.get("/{project_id}/roi-analysis")
async def get_roi_analysis(
    project_id: int,
    request: Request,
    start_date: str = Query(default="30daysAgo", description="Start date"),
    end_date: str = Query(default="today", description="End date"),
    seo_investment: float = Query(default=5000.0, description="SEO investment amount"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Calculate SEO ROI analysis based on organic revenue and investment.
    
    This endpoint calculates return on investment for SEO efforts
    based on organic revenue and specified investment amounts.
    
    Args:
        start_date: Start date for analysis
        end_date: End date for analysis  
        seo_investment: SEO investment amount for ROI calculation
        current_user: The authenticated user
        
    Returns:
        Comprehensive SEO ROI analysis
    """
    try:
        # Get project and validate GA4 configuration
        project, project_ga4_service = await get_project_with_ga4(
            project_id, current_user, db
        )
        
        # Get organic performance data
        organic_data = await project_ga4_service.get_organic_performance(
            start_date=start_date,
            end_date=end_date
        )
        
        # Get revenue attribution for organic traffic
        revenue_data = await project_ga4_service.get_revenue_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate organic revenue
        organic_revenue = organic_data.get("total_organic_revenue", 0)
        
        # Calculate ROI metrics
        roi_percentage = ((organic_revenue - seo_investment) / seo_investment * 100) if seo_investment > 0 else 0
        roas = organic_revenue / seo_investment if seo_investment > 0 else 0
        
        # Calculate additional metrics
        organic_clicks = organic_data.get("total_clicks", 0)
        cost_per_click = seo_investment / organic_clicks if organic_clicks > 0 else 0
        revenue_per_click = organic_revenue / organic_clicks if organic_clicks > 0 else 0
        
        return {
            "success": True,
            "data": {
                "roi_metrics": {
                    "seo_investment": seo_investment,
                    "organic_revenue": organic_revenue,
                    "net_profit": organic_revenue - seo_investment,
                    "roi_percentage": round(roi_percentage, 2),
                    "roas": round(roas, 2),
                    "payback_period": _calculate_payback_period(organic_revenue, seo_investment)
                },
                "efficiency_metrics": {
                    "cost_per_click": round(cost_per_click, 2),
                    "revenue_per_click": round(revenue_per_click, 2),
                    "organic_clicks": organic_clicks,
                    "organic_ctr": organic_data.get("overall_ctr", 0)
                },
                "benchmarks": {
                    "industry_average_roi": 122,  # Industry benchmark
                    "good_roi_threshold": 400,
                    "excellent_roi_threshold": 800,
                    "performance_rating": _rate_roi_performance(roi_percentage)
                }
            },
            "is_ga4_configured": project.ga4_configured,
            "ga4_property_id": project.ga4_property_id,
            "project_id": project_id,
            "project_name": project.name
        }
        
    except Exception as e:
        logger.error(f"ROI analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"ROI analysis failed: {str(e)}")


def _calculate_profitability_metrics(revenue_data: Dict, organic_data: Dict, funnel_data: Dict) -> Dict[str, Any]:
    """Calculate comprehensive profitability metrics."""
    
    total_revenue = revenue_data.get("total_revenue", 0)
    organic_revenue = organic_data.get("total_organic_revenue", 0)
    total_sessions = revenue_data.get("total_sessions", 0)
    conversion_rate = revenue_data.get("conversion_rate", 0)
    
    # Calculate organic share
    organic_share = (organic_revenue / total_revenue * 100) if total_revenue > 0 else 0
    
    # Calculate revenue per session
    revenue_per_session = total_revenue / total_sessions if total_sessions > 0 else 0
    
    # Calculate customer lifetime value (simplified)
    avg_order_value = total_revenue / revenue_data.get("total_conversions", 1)
    estimated_clv = avg_order_value * 2.5  # Simplified CLV calculation
    
    return {
        "total_revenue": total_revenue,
        "organic_revenue": organic_revenue,
        "organic_share_percentage": round(organic_share, 2),
        "conversion_rate": round(conversion_rate, 2),
        "revenue_per_session": round(revenue_per_session, 2),
        "average_order_value": round(avg_order_value, 2),
        "estimated_customer_lifetime_value": round(estimated_clv, 2),
        "profitability_score": _calculate_profitability_score(revenue_data, organic_data),
        "growth_trend": "positive",  # This would be calculated from historical data
        "key_insights": _generate_profitability_insights(revenue_data, organic_data)
    }


def _generate_conversion_recommendations(funnel_data: Dict, traffic_data: Dict) -> List[str]:
    """Generate conversion optimization recommendations."""
    
    recommendations = []
    conversion_rates = funnel_data.get("conversion_rates", {})
    
    # Check for funnel drop-offs
    if conversion_rates.get("add_to_cart", 0) < 10:
        recommendations.append("Product pages may need optimization - low add-to-cart rate")
    
    if conversion_rates.get("begin_checkout", 0) < 5:
        recommendations.append("Checkout process needs streamlining - high cart abandonment")
    
    if conversion_rates.get("purchase", 0) < 2:
        recommendations.append("Focus on overall conversion optimization - low purchase rate")
    
    # Device-specific recommendations
    device_breakdown = traffic_data.get("device_breakdown", {})
    mobile_percentage = device_breakdown.get("mobile", 0) / sum(device_breakdown.values()) * 100
    
    if mobile_percentage > 50:
        recommendations.append("Prioritize mobile optimization - majority of traffic is mobile")
    
    return recommendations


def _calculate_payback_period(revenue: float, investment: float) -> str:
    """Calculate payback period for SEO investment."""
    
    if investment <= 0 or revenue <= 0:
        return "Unable to calculate"
    
    if revenue >= investment:
        return "Less than 1 month"
    
    # Simplified calculation assuming consistent monthly returns
    monthly_revenue = revenue / 1  # Assuming this is monthly data
    months_to_payback = investment / monthly_revenue
    
    if months_to_payback < 12:
        return f"{int(months_to_payback)} months"
    else:
        years = months_to_payback / 12
        return f"{years:.1f} years"


def _rate_roi_performance(roi_percentage: float) -> str:
    """Rate ROI performance against industry benchmarks."""
    
    if roi_percentage >= 800:
        return "Excellent"
    elif roi_percentage >= 400:
        return "Good"
    elif roi_percentage >= 122:
        return "Average"
    elif roi_percentage >= 0:
        return "Below Average"
    else:
        return "Negative"


def _calculate_profitability_score(revenue_data: Dict, organic_data: Dict) -> int:
    """Calculate overall profitability score (0-100)."""
    
    score = 50  # Base score
    
    # Revenue performance (30 points)
    total_revenue = revenue_data.get("total_revenue", 0)
    if total_revenue > 50000:
        score += 30
    elif total_revenue > 20000:
        score += 20
    elif total_revenue > 5000:
        score += 10
    
    # Conversion rate (25 points)
    conversion_rate = revenue_data.get("conversion_rate", 0)
    if conversion_rate > 3:
        score += 25
    elif conversion_rate > 2:
        score += 20
    elif conversion_rate > 1:
        score += 15
    elif conversion_rate > 0.5:
        score += 10
    
    # Organic performance (25 points)
    organic_ctr = organic_data.get("overall_ctr", 0)
    if organic_ctr > 15:
        score += 25
    elif organic_ctr > 10:
        score += 20
    elif organic_ctr > 5:
        score += 15
    elif organic_ctr > 2:
        score += 10
    
    # Revenue per session (20 points)
    revenue_per_session = revenue_data.get("revenue_per_session", 0)
    if revenue_per_session > 10:
        score += 20
    elif revenue_per_session > 5:
        score += 15
    elif revenue_per_session > 2:
        score += 10
    elif revenue_per_session > 1:
        score += 5
    
    return min(score, 100)


def _generate_profitability_insights(revenue_data: Dict, organic_data: Dict) -> List[str]:
    """Generate key profitability insights."""
    
    insights = []
    
    # Revenue insights
    total_revenue = revenue_data.get("total_revenue", 0)
    organic_revenue = organic_data.get("total_organic_revenue", 0)
    organic_share = (organic_revenue / total_revenue * 100) if total_revenue > 0 else 0
    
    if organic_share > 50:
        insights.append(f"Organic search drives {organic_share:.1f}% of total revenue - excellent organic performance")
    elif organic_share > 30:
        insights.append(f"Organic search contributes {organic_share:.1f}% of revenue - strong SEO results")
    else:
        insights.append(f"Organic search accounts for {organic_share:.1f}% of revenue - opportunity for improvement")
    
    # Conversion insights
    conversion_rate = revenue_data.get("conversion_rate", 0)
    if conversion_rate > 3:
        insights.append("Conversion rate is excellent - focus on scaling traffic")
    elif conversion_rate < 1:
        insights.append("Conversion rate needs improvement - optimize user experience")
    # CTR insights
    organic_ctr = organic_data.get("overall_ctr", 0)
    if organic_ctr > 10:
        insights.append("Organic click-through rate is strong - good SERP presence")
    elif organic_ctr < 5:
        insights.append("Organic CTR could be improved - optimize titles and meta descriptions")
    
    return insights


# Analytics Data Endpoints


@router.get("/revenue", dependencies=[Depends(get_current_active_user)])
async def get_revenue_data(days: int = 30, current_user: UserProfile=Depends(get_current_active_user)):
    """Get revenue and profitability data from Google Analytics."""
    try:
        # Get real GA4 data
        ga_revenue_data = await ga4_service.get_revenue_metrics(
            start_date=f"{days}daysAgo",
            end_date="today"
        )
        
        return {
            "success": True,
            "data": ga_revenue_data,
            "source": "google_analytics",
            "period_days": days,
            "last_updated": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting revenue data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get revenue data: {str(e)}"
        )


@router.get("/attribution")
async def get_attribution_data(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get attribution data for organic search.
    
    This endpoint returns detailed attribution data for organic search traffic,
    including revenue, profit, and conversion metrics by channel and source.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        Detailed attribution data
    """
    try:
        # Get real GA4 data with source breakdown
        revenue_data = await ga4_service.get_revenue_metrics(
            start_date="30daysAgo",
            end_date="today"
        )
        
        # Calculate attribution from real data
        source_breakdown = revenue_data.get("source_breakdown", {})
        total_revenue = revenue_data.get("total_revenue", 0)
        total_conversions = revenue_data.get("total_conversions", 0)
        
        channels = []
        for source, data in source_breakdown.items():
            source_revenue = data.get("revenue", 0)
            source_conversions = data.get("conversions", 0)
            profit_estimate = source_revenue * 0.285  # Estimate 28.5% profit margin
            
            channels.append({
                "channel": source,
                "revenue": source_revenue,
                "profit": profit_estimate,
                "conversions": source_conversions,
                "attribution_percentage": (source_revenue / total_revenue * 100) if total_revenue > 0 else 0
            })
        
        return {
            "attribution_model": "Last Non-Direct Click",
            "total_revenue": total_revenue,
            "total_profit": total_revenue * 0.285,  # Estimate profit
            "channels": channels,
            "data_source": "Google Analytics 4"
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Attribution data error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get attribution data: {str(e)}"
        )


@router.get("/keyword-profitability")
async def get_keyword_profitability(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get profitability data for keywords.
    
    This endpoint returns profitability metrics for keywords, including revenue,
    profit, and conversion metrics.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        Keyword profitability data
    """
    try:
        # Get organic performance data from GA4
        organic_data = await ga4_service.get_organic_performance(
            start_date="30daysAgo",
            end_date="today"
        )
        
        # Process page performance data to extract keyword insights
        page_performance = organic_data.get("page_performance", [])
        
        keywords = []
        for page in page_performance[:10]:  # Top 10 pages
            page_path = page.get("page_path", "")
            # Extract potential keywords from page path
            potential_keywords = page_path.replace("/", " ").replace("-", " ").strip().split()
            
            if potential_keywords:
                keyword = " ".join(potential_keywords[-3:])  # Last 3 words as keyword
                revenue = page.get("revenue", 0)
                profit_estimate = revenue * 0.285
                
                keywords.append({
                    "keyword": keyword,
                    "search_volume": "N/A",  # Would need Search Console data
                    "position": "N/A",  # Would need Search Console data
                    "traffic": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "roi": (profit_estimate / 1000 * 100) if revenue > 0 else 0,  # Estimate ROI
                })
        
        return {
            "keywords": keywords,
            "data_source": "Google Analytics 4",
            "note": "Keyword data limited to page performance. For full keyword analysis, integrate with Google Search Console."
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Keyword profitability error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get keyword profitability: {str(e)}"
        )


@router.get("/content-profitability")
async def get_content_profitability(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get profitability data for content.
    
    This endpoint returns profitability metrics for content pages, including revenue,
    profit, and conversion metrics.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        Content profitability data
    """
    try:
        # Get organic performance data from GA4
        organic_data = await ga4_service.get_organic_performance(
            start_date="30daysAgo",
            end_date="today"
        )
        
        # Get traffic analytics for additional context
        traffic_data = await ga4_service.get_traffic_analytics(
            start_date="30daysAgo",
            end_date="today"
        )
        
        page_performance = organic_data.get("page_performance", [])
        top_pages = traffic_data.get("top_pages", [])
        
        # Combine data for comprehensive content analysis
        pages = []
        for page in page_performance[:20]:  # Top 20 pages
            page_path = page.get("page_path", "")
            revenue = page.get("revenue", 0)
            profit_estimate = revenue * 0.285
            
            # Find matching traffic data
            traffic_info = next((p for p in top_pages if p.get("path") == page_path), {})
            
            pages.append({
                "url": f"https://example.com{page_path}",  # Would need actual domain
                "title": page_path.replace("/", " ").replace("-", " ").title(),
                "traffic": page.get("clicks", 0),
                "conversions": page.get("conversions", 0),
                "revenue": revenue,
                "profit": profit_estimate,
                "roi": (profit_estimate / 1000 * 100) if revenue > 0 else 0,
                "sessions": traffic_info.get("sessions", 0),
                "users": traffic_info.get("users", 0)
            })
        
        return {
            "pages": pages,
            "data_source": "Google Analytics 4",
            "total_pages_analyzed": len(pages)
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Content profitability error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get content profitability: {str(e)}"
        )


@router.get("/sales-enablement/{lead_id}")
async def get_sales_enablement_context(
    lead_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get sales enablement context for a lead.
    
    This endpoint returns context information for a lead from organic search,
    including the keyword, landing page, and likely pain points.
    
    Args:
        lead_id: The ID of the lead
        current_user: The authenticated user
        
    Returns:
        Sales enablement context for the lead
    """
    try:
        # Get organic performance data to understand lead source
        organic_data = await ga4_service.get_organic_performance(
            start_date="7daysAgo",
            end_date="today"
        )
        
        # Get conversion funnel data for context
        funnel_data = await ga4_service.get_conversion_funnel(
            start_date="7daysAgo",
            end_date="today"
        )
        
        # This would typically query a CRM or lead database
        # For now, we'll return a structure that can be populated with real data
        return {
            "lead_id": lead_id,
            "source": "Organic Search",
            "data_available": True,
            "organic_performance": {
                "total_clicks": organic_data.get("total_clicks", 0),
                "total_impressions": organic_data.get("total_impressions", 0),
                "conversion_rate": organic_data.get("overall_ctr", 0)
            },
            "funnel_context": {
                "total_conversions": funnel_data.get("final_conversion_rate", 0),
                "funnel_steps": list(funnel_data.get("funnel_steps", {}).keys())
            },
            "note": "Lead-specific data requires CRM integration. Current data shows overall organic performance context."
        }
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Sales enablement error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sales enablement context: {str(e)}"
        )


@router.get("/roi-by-page-type")
async def get_roi_by_page_type(
    site_id: Optional[int] = Query(None, description="Site ID to get ROI data for"),
    period: str = Query("30d", description="Time period (7d, 30d, 90d)"),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get ROI data by page type.
    
    This endpoint returns ROI analysis broken down by different page types
    (product pages, blog posts, landing pages, etc.).
    
    Args:
        site_id: Optional site ID to filter data
        period: Time period for analysis (7d, 30d, 90d)
        current_user: The authenticated user
        
    Returns:
        ROI data by page type
    """
    logger.info(f"Getting ROI by page type for user {current_user.email}, site_id: {site_id}, period: {period}")
    
    try:
        # Convert period to GA4 format
        period_days = int(period.replace("d", ""))
        start_date = f"{period_days}daysAgo"
        
        # Get organic performance data from GA4
        organic_data = await ga4_service.get_organic_performance(
            start_date=start_date,
            end_date="today"
        )
        
        # Get traffic analytics for additional context
        traffic_data = await ga4_service.get_traffic_analytics(
            start_date=start_date,
            end_date="today"
        )
        
        page_performance = organic_data.get("page_performance", [])
        top_pages = traffic_data.get("top_pages", [])
        
        # Categorize pages by type based on URL patterns
        page_types = {
            "Product Pages": [],
            "Blog Posts": [],
            "Landing Pages": [],
            "Resource Pages": [],
            "Case Studies": [],
            "Category Pages": [],
            "About/Company Pages": [],
            "Contact Pages": []
        }
        
        for page in page_performance:
            page_path = page.get("page_path", "").lower()
            revenue = page.get("revenue", 0)
            profit_estimate = revenue * 0.285
            
            # Categorize based on URL patterns
            if any(keyword in page_path for keyword in ["/product/", "/buy/", "/purchase/"]):
                page_types["Product Pages"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
            elif any(keyword in page_path for keyword in ["/blog/", "/post/", "/article/"]):
                page_types["Blog Posts"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
            elif any(keyword in page_path for keyword in ["/landing/", "/lp/", "/offer/"]):
                page_types["Landing Pages"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
            elif any(keyword in page_path for keyword in ["/case-study/", "/case-studies/"]):
                page_types["Case Studies"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
            elif any(keyword in page_path for keyword in ["/about/", "/company/", "/team/"]):
                page_types["About/Company Pages"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
            elif any(keyword in page_path for keyword in ["/contact/", "/contact-us/"]):
                page_types["Contact Pages"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
            else:
                # Default to resource pages
                page_types["Resource Pages"].append({
                    "path": page.get("page_path", ""),
                    "revenue": revenue,
                    "profit": profit_estimate,
                    "clicks": page.get("clicks", 0),
                    "conversions": page.get("conversions", 0)
                })
        
        # Calculate ROI metrics for each page type
        roi_data = []
        for page_type, pages in page_types.items():
            if pages:
                total_revenue = sum(p["revenue"] for p in pages)
                total_profit = sum(p["profit"] for p in pages)
                total_clicks = sum(p["clicks"] for p in pages)
                total_conversions = sum(p["conversions"] for p in pages)
                
                # Calculate ROI (profit as percentage of revenue)
                roi_percentage = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
                conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
                
                roi_data.append({
                    "name": page_type,
                    "Revenue": total_revenue,
                    "Profit": total_profit,
                    "ROI": round(roi_percentage, 1),
                    "traffic_share": round((total_clicks / organic_data.get("total_clicks", 1)) * 100, 1),
                    "conversion_rate": round(conversion_rate, 2),
                    "pages_count": len(pages),
                    "avg_order_value": total_revenue / total_conversions if total_conversions > 0 else 0
                })
        
        # Sort by ROI descending
        roi_data.sort(key=lambda x: x["ROI"], reverse=True)
        
        # Calculate totals
        total_revenue = sum(item["Revenue"] for item in roi_data)
        total_profit = sum(item["Profit"] for item in roi_data)
        weighted_avg_roi = round((total_profit / total_revenue) * 100) if total_revenue > 0 else 0
        
        response_data = {
            "roi_by_page_type": roi_data,
            "summary": {
                "total_revenue": total_revenue,
                "total_profit": total_profit,
                "weighted_avg_roi": weighted_avg_roi,
                "best_performing_type": roi_data[0]["name"] if roi_data else None,
                "worst_performing_type": roi_data[-1]["name"] if roi_data else None
            },
            "period": period,
            "data_source": "Google Analytics 4",
            "last_updated": datetime.now().isoformat()
        }
        
        return response_data
        
    except ValueError as e:
        logger.error(f"GA4 configuration error: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Google Analytics 4 configuration required: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting ROI by page type: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ROI by page type: {str(e)}"
        )


@router.get("/ga4/properties")
async def get_ga4_properties(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get list of GA4 properties accessible to the user via OAuth.
    
    This endpoint returns all GA4 properties the user has access to through
    their Google OAuth authentication.
    
    Args:
        current_user: The authenticated user
        db: Database session
        
    Returns:
        List of GA4 properties
    """
    try:
        # Check if user has OAuth access
        access_token = await oauth_service.get_valid_access_token(db, current_user.id)
        has_analytics_scope = oauth_service.has_scope(current_user, 'https://www.googleapis.com/auth/analytics.readonly')
        
        if not access_token or not has_analytics_scope:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Google Analytics OAuth required",
                    "message": "Please authenticate with Google Analytics to access properties",
                    "oauth_url": "/api/v1/oauth/google/authorize?scopes=analytics",
                    "oauth_connected": False
                }
            )
        
        # Create GA4 service with OAuth token
        ga4_oauth_service = GoogleAnalytics4Service(access_token=access_token)
        
        # Get properties
        properties = await ga4_oauth_service.get_ga4_properties()
        
        return {
            "success": True,
            "properties": properties,
            "total_properties": len(properties)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GA4 properties: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve GA4 properties: {str(e)}"
        )


@router.post("/ga4/{project_id}/select-property")
async def select_ga4_property(
    project_id: int,
    property_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Select a GA4 property for a project.
    
    This endpoint allows the user to select which GA4 property to use for
    profitability tracking in a specific project.
    
    Args:
        project_id: The project ID
        property_id: The GA4 property ID to select
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Success status
    """
    try:
        # Get project and verify ownership
        project = await db.get(Project, project_id)
        if not project or project.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update project with GA4 property
        project.ga4_property_id = property_id
        project.ga4_configured = True
        project.analytics_enabled = True
        
        await db.commit()
        await db.refresh(project)
        
        # Log activity
        from app.services.activity_service import log_user_activity
        from app.models.activity_feed import ActivityType
        
        await log_user_activity(
            user_id=current_user.id,
            type=ActivityType.INTEGRATION_CONNECTED,
            title=f"GA4 property connected to project {project.name}",
            organization_id=current_user.organization_id,
            data={
                "project_id": project_id,
                "property_id": property_id,
                "integration": "google_analytics_4"
            }
        )
        
        return {
            "success": True,
            "message": f"GA4 property {property_id} selected for project",
            "project": {
                "id": project.id,
                "name": project.name,
                "ga4_property_id": project.ga4_property_id,
                "ga4_configured": project.ga4_configured
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting GA4 property: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to select GA4 property: {str(e)}"
        )


@router.post("/{project_id}/roi-analysis")
async def get_roi_analysis(
    project_id: int,
    payload: ProfitabilityRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get comprehensive ROI analysis for SEO campaigns.
    
    This endpoint provides detailed ROI metrics including campaign performance,
    landing page effectiveness, and revenue attribution.
    
    Args:
        project_id: The project ID
        payload: Analysis parameters
        request: The request object
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Comprehensive ROI analysis
    """
    try:
        # Get project and GA4 service
        project, project_ga4_service = await get_project_with_ga4(project_id, current_user, db)
        
        # Get ROI metrics
        roi_data = await project_ga4_service.get_roi_metrics(
            start_date=payload.start_date,
            end_date=payload.end_date
        )
        
        # Get organic performance for SEO-specific metrics
        organic_data = await project_ga4_service.get_organic_performance(
            start_date=payload.start_date,
            end_date=payload.end_date
        )
        
        # Calculate SEO ROI
        organic_revenue = organic_data.get("total_organic_revenue", 0)
        seo_investment = project.monthly_seo_budget or 5000  # Default estimate
        seo_roi = ((organic_revenue - seo_investment) / seo_investment * 100) if seo_investment > 0 else 0
        
        # Generate insights
        insights = []
        if roi_data["summary"]["overall_roi"] == "∞":
            insights.append("Infinite ROI indicates revenue with no tracked costs - excellent performance")
        elif float(roi_data["summary"]["overall_roi"]) > 500:
            insights.append("Exceptional ROI performance - your campaigns are highly profitable")
        elif float(roi_data["summary"]["overall_roi"]) > 200:
            insights.append("Strong ROI performance - campaigns are generating good returns")
        elif float(roi_data["summary"]["overall_roi"]) > 0:
            insights.append("Positive ROI - campaigns are profitable but have room for improvement")
        else:
            insights.append("Negative ROI - campaigns need optimization to become profitable")
        
        # Top performing campaigns
        if roi_data["top_campaigns"]:
            best_campaign = roi_data["top_campaigns"][0]
            insights.append(f"Best performing campaign: {best_campaign['campaign']} with ${best_campaign['revenue']:.2f} revenue")
        
        # Landing page insights
        if roi_data["top_landing_pages"]:
            best_page = roi_data["top_landing_pages"][0]
            insights.append(f"Top revenue-generating page: {best_page['page']} with ${best_page['revenue']:.2f}")
        
        return {
            "project_id": project_id,
            "period": {
                "start_date": payload.start_date,
                "end_date": payload.end_date
            },
            "roi_summary": roi_data["summary"],
            "seo_specific": {
                "organic_revenue": organic_revenue,
                "estimated_investment": seo_investment,
                "seo_roi": round(seo_roi, 2),
                "organic_clicks": organic_data.get("total_clicks", 0),
                "organic_impressions": organic_data.get("total_impressions", 0),
                "organic_ctr": organic_data.get("overall_ctr", 0)
            },
            "top_campaigns": roi_data["top_campaigns"][:5],
            "top_landing_pages": roi_data["top_landing_pages"][:5],
            "source_breakdown": roi_data["source_medium_breakdown"],
            "insights": insights,
            "currency": roi_data["currency"],
            "data_source": "Google Analytics 4",
            "last_updated": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ROI analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ROI analysis: {str(e)}"
        )