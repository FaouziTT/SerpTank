"""
API endpoints for SERP analysis using Programmable Search and SerpAPI.

This module provides endpoints for keyword research, SERP analysis,
and competitor tracking using Google's Programmable Search API and SerpAPI.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.services.programmable_search import programmable_search_service
from app.services.serpapi import SerpAPIService
from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.models.user import User
from app.models.serp_cache import SERPAnalysis, CompetitorTracking, SERPFeatureTracking
from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)
serpapi_service = SerpAPIService()


class KeywordSearchRequest(BaseModel):
    query: str
    num_results: Optional[int] = 10
    country: Optional[str] = "us"
    language: Optional[str] = "en"
    device: Optional[str] = "desktop"


class SerpAnalysisRequest(BaseModel):
    query: str
    location: Optional[str] = "United States"
    device: Optional[str] = "desktop"
    use_serpapi: Optional[bool] = True  # Prefer SerpAPI if available


class KeywordTrackingRequest(BaseModel):
    keywords: List[str]
    domain: str


class LocalSeoRequest(BaseModel):
    query: str
    location: str
    radius: Optional[int] = 25


class CompetitorAnalysisRequest(BaseModel):
    keywords: List[str]
    competitors: List[str]
    location: Optional[str] = "United States"


@router.post("/search")
async def search_keywords(
    request: KeywordSearchRequest,
    current_user: UserProfile = Depends(get_current_active_user),
):
    """
    Search for keywords and get SERP results.
    
    Args:
        request: Keyword search parameters
        current_user: Current authenticated user
        
    Returns:
        Search results with organic positions
    """
    try:
        results = await programmable_search_service.search_keywords(
            query=request.query,
            num_results=request.num_results,
            country=request.country,
            language=request.language,
            device=request.device
        )
        
        return {
            "success": True,
            "data": results,
            "is_configured": programmable_search_service.is_configured()
        }
        
    except Exception as e:
        logger.error(f"Error in keyword search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/analyze-serp")
async def analyze_serp_features(
    request: SerpAnalysisRequest,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze SERP features for a given query using SerpAPI or Google Custom Search.
    
    Args:
        request: SERP analysis parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Enhanced SERP features analysis with rich data
    """
    try:
        # Check if we have a recent analysis for this query (cache for 24 hours)
        cache_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        cached_result = await db.execute(
            select(SERPAnalysis)
            .where(
                SERPAnalysis.user_id == current_user.id,
                SERPAnalysis.query == request.query,
                SERPAnalysis.location == request.location,
                SERPAnalysis.device == request.device,
                SERPAnalysis.created_at > cache_cutoff
            )
            .order_by(desc(SERPAnalysis.created_at))
            .limit(1)
        )
        cached = cached_result.scalar_one_or_none()
        
        if cached:
            logger.info(f"Using cached SERP analysis for: {request.query}")
            return {
                "success": True,
                "data": {
                    "query": cached.query,
                    "organic_results": cached.organic_results or [],
                    "serp_features": cached.serp_features or {},
                    "competition_level": cached.competition_level,
                    "opportunity_score": cached.opportunity_score,
                    "from_cache": True
                },
                "source": "Cache",
                "is_serpapi_configured": serpapi_service.is_configured(),
                "is_google_configured": programmable_search_service.is_configured()
            }
        
        # Try SerpAPI first if configured and requested
        if request.use_serpapi and serpapi_service.is_configured():
            logger.info(f"Using SerpAPI for advanced SERP analysis: {request.query}")
            analysis = await serpapi_service.advanced_serp_analysis(
                query=request.query,
                location=request.location,
                device=request.device
            )
            
            # Calculate competition level and opportunity score
            organic_count = len(analysis.get("organic_results", []))
            paid_count = analysis.get("search_information", {}).get("ads_results_count", 0)
            feature_count = analysis.get("serp_features_count", 0)
            
            if organic_count > 8 or paid_count > 3:
                competition_level = "High"
                opportunity_score = 30
            elif organic_count > 5 or paid_count > 1:
                competition_level = "Medium"
                opportunity_score = 60
            else:
                competition_level = "Low"
                opportunity_score = 85
            
            # Bonus points for fewer SERP features
            if feature_count < 3:
                opportunity_score = min(100, opportunity_score + 15)
            
            # Save to database
            serp_analysis = SERPAnalysis(
                user_id=current_user.id,
                query=request.query,
                location=request.location,
                device=request.device,
                organic_results=analysis.get("organic_results", []),
                serp_features=analysis.get("serp_features", {}),
                competitors=[],  # Will be populated later
                organic_count=organic_count,
                paid_count=paid_count,
                feature_count=feature_count,
                competition_level=competition_level,
                opportunity_score=opportunity_score
            )
            db.add(serp_analysis)
            
            # Save competitors
            for result in analysis.get("organic_results", [])[:10]:
                domain = result.get("domain", "")
                if domain:
                    # Check if competitor exists
                    comp_result = await db.execute(
                        select(CompetitorTracking)
                        .where(
                            CompetitorTracking.user_id == current_user.id,
                            CompetitorTracking.domain == domain
                        )
                    )
                    competitor = comp_result.scalar_one_or_none()
                    
                    if not competitor:
                        competitor = CompetitorTracking(
                            user_id=current_user.id,
                            domain=domain,
                            title=result.get("title", "")
                        )
                        db.add(competitor)
            
            # Save SERP features
            for feature_type, feature_data in analysis.get("serp_features", {}).items():
                if feature_data:
                    feature = SERPFeatureTracking(
                        user_id=current_user.id,
                        query=request.query,
                        feature_name=feature_type.replace("_", " ").title(),
                        feature_type=feature_type,
                        position="Top" if feature_type in ["featured_snippet", "knowledge_panel"] else "Various",
                        description=f"{feature_type} detected in SERP"
                    )
                    db.add(feature)
            
            await db.commit()
            
            # Add calculated metrics to response
            analysis["competition_level"] = competition_level
            analysis["opportunity_score"] = opportunity_score
            
            return {
                "success": True,
                "data": analysis,
                "source": "SerpAPI",
                "is_serpapi_configured": True,
                "is_google_configured": programmable_search_service.is_configured()
            }
        
        # Fallback to Google Custom Search
        logger.info(f"Using Google Custom Search for SERP analysis: {request.query}")
        analysis = await programmable_search_service.analyze_serp_features(request.query)
        
        # Save basic analysis to database
        serp_analysis = SERPAnalysis(
            user_id=current_user.id,
            query=request.query,
            location=request.location,
            device=request.device,
            organic_results=analysis.get("results", []),
            serp_features={},
            competitors=[],
            organic_count=len(analysis.get("results", [])),
            paid_count=0,
            feature_count=0,
            competition_level="Medium",
            opportunity_score=50
        )
        db.add(serp_analysis)
        await db.commit()
        
        return {
            "success": True,
            "data": analysis,
            "source": "Google Custom Search",
            "is_serpapi_configured": serpapi_service.is_configured(),
            "is_google_configured": programmable_search_service.is_configured()
        }
        
    except Exception as e:
        logger.error(f"Error in SERP analysis: {e}")
        raise HTTPException(status_code=500, detail=f"SERP analysis failed: {str(e)}")


@router.post("/track-keywords")
async def track_keyword_positions(
    request: KeywordTrackingRequest,
    current_user: UserProfile = Depends(get_current_active_user),
):
    """
    Track keyword positions for a specific domain.
    
    Args:
        request: Keyword tracking parameters
        current_user: Current authenticated user
        
    Returns:
        Keyword position tracking results
    """
    try:
        if len(request.keywords) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 keywords allowed per request"
            )
        
        positions = await programmable_search_service.track_keyword_positions(
            keywords=request.keywords,
            domain=request.domain
        )
        
        return {
            "success": True,
            "data": {
                "domain": request.domain,
                "total_keywords": len(request.keywords),
                "positions": positions
            },
            "is_configured": programmable_search_service.is_configured()
        }
        
    except Exception as e:
        logger.error(f"Error in keyword tracking: {e}")
        raise HTTPException(status_code=500, detail=f"Keyword tracking failed: {str(e)}")


@router.get("/competitors/{domain}")
async def analyze_competitors(
    domain: str,
    keywords: List[str] = Query(..., description="Keywords to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """
    Analyze competitors for given keywords.
    
    Args:
        domain: Target domain
        keywords: Keywords to analyze
        current_user: Current authenticated user
        
    Returns:
        Competitor analysis results
    """
    try:
        competitor_data = []
        
        for keyword in keywords[:10]:  # Limit to 10 keywords
            search_results = await programmable_search_service.search_keywords(
                query=keyword,
                num_results=10
            )
            
            # Find competitors (domains that rank but aren't the target domain)
            competitors = []
            for result in search_results.get("organic_results", []):
                result_domain = result.get("domain", "")
                if result_domain and domain.lower() not in result_domain.lower():
                    competitors.append({
                        "domain": result_domain,
                        "position": result.get("position"),
                        "title": result.get("title"),
                        "url": result.get("url")
                    })
            
            competitor_data.append({
                "keyword": keyword,
                "competitors": competitors[:5],  # Top 5 competitors
                "your_position": next(
                    (r.get("position") for r in search_results.get("organic_results", [])
                     if domain.lower() in r.get("domain", "").lower()),
                    None
                )
            })
        
        return {
            "success": True,
            "data": {
                "domain": domain,
                "total_keywords": len(keywords),
                "competitor_analysis": competitor_data
            },
            "is_configured": programmable_search_service.is_configured()
        }
        
    except Exception as e:
        logger.error(f"Error in competitor analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Competitor analysis failed: {str(e)}")


@router.post("/local-seo")
async def analyze_local_seo(
    request: LocalSeoRequest,
    current_user: UserProfile = Depends(get_current_active_user),
):
    """
    Analyze local SEO results including Google My Business listings.
    
    Args:
        request: Local SEO analysis parameters
        current_user: Current authenticated user
        
    Returns:
        Local SEO analysis with map pack and local rankings
    """
    try:
        if not serpapi_service.is_configured():
            raise HTTPException(
                status_code=400,
                detail="SerpAPI is required for local SEO analysis. Please configure SERPAPI_KEY in environment variables."
            )
        
        analysis = await serpapi_service.local_seo_analysis(
            query=request.query,
            location=request.location,
            radius=request.radius
        )
        
        return {
            "success": True,
            "data": analysis,
            "source": "SerpAPI",
            "is_serpapi_configured": True
        }
        
    except Exception as e:
        logger.error(f"Error in local SEO analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Local SEO analysis failed: {str(e)}")


@router.post("/competitor-analysis")
async def advanced_competitor_analysis(
    request: CompetitorAnalysisRequest,
    current_user: UserProfile = Depends(get_current_active_user),
):
    """
    Perform advanced competitor analysis across multiple keywords.
    
    Args:
        request: Competitor analysis parameters
        current_user: Current authenticated user
        
    Returns:
        Comprehensive competitor visibility analysis
    """
    try:
        if len(request.keywords) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 keywords allowed for competitor analysis"
            )
        
        if len(request.competitors) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 competitors allowed for analysis"
            )
        
        if serpapi_service.is_configured():
            logger.info("Using SerpAPI for advanced competitor analysis")
            analysis = await serpapi_service.competitor_serp_comparison(
                queries=request.keywords,
                competitors=request.competitors,
                location=request.location
            )
            
            return {
                "success": True,
                "data": analysis,
                "source": "SerpAPI",
                "is_serpapi_configured": True
            }
        else:
            # Fallback to basic competitor analysis using Google Custom Search
            logger.info("Using Google Custom Search for basic competitor analysis")
            competitor_data = []
            
            for keyword in request.keywords:
                search_results = await programmable_search_service.search_keywords(
                    query=keyword,
                    num_results=20
                )
                
                keyword_analysis = {
                    "keyword": keyword,
                    "competitors": {}
                }
                
                for competitor in request.competitors:
                    position = None
                    for result in search_results.get("organic_results", []):
                        if competitor.lower() in result.get("domain", "").lower():
                            position = result.get("position")
                            break
                    
                    keyword_analysis["competitors"][competitor] = {
                        "position": position,
                        "ranking": position is not None
                    }
                
                competitor_data.append(keyword_analysis)
            
            return {
                "success": True,
                "data": {
                    "competitor_analysis": competitor_data,
                    "summary": {
                        "total_keywords": len(request.keywords),
                        "total_competitors": len(request.competitors)
                    }
                },
                "source": "Google Custom Search",
                "is_serpapi_configured": False
            }
        
    except Exception as e:
        logger.error(f"Error in competitor analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Competitor analysis failed: {str(e)}")


@router.get("/serp-features/overview")
async def get_serp_features_overview(
    query: str = Query(..., description="Search query to analyze"),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """
    Get an overview of SERP features for a query.
    
    Args:
        query: Search query to analyze
        current_user: Current authenticated user
        
    Returns:
        SERP features overview and recommendations
    """
    try:
        # Use SerpAPI if available for better feature detection
        if serpapi_service.is_configured():
            analysis = await serpapi_service.advanced_serp_analysis(query)
            
            features_count = analysis.get("serp_features_count", 0)
            features = analysis.get("serp_features", {})
            
            recommendations = []
            if features.get("featured_snippet"):
                recommendations.append("Optimize for featured snippet with structured content")
            if features.get("people_also_ask"):
                recommendations.append("Target PAA questions in your content")
            if features.get("local_pack"):
                recommendations.append("Optimize Google My Business listing")
            if not features.get("featured_snippet") and not features.get("people_also_ask"):
                recommendations.append("Consider creating FAQ section to target featured snippets")
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "total_serp_features": features_count,
                    "features": features,
                    "recommendations": recommendations,
                    "organic_competition": len(analysis.get("organic_results", [])) 
                },
                "source": "SerpAPI"
            }
        else:
            # Basic analysis with Google Custom Search
            analysis = await programmable_search_service.analyze_serp_features(query)
            
            return {
                "success": True,
                "data": analysis,
                "source": "Google Custom Search",
                "note": "Upgrade to SerpAPI for enhanced SERP features detection"
            }
        
    except Exception as e:
        logger.error(f"Error in SERP features overview: {e}")
        raise HTTPException(status_code=500, detail=f"SERP features analysis failed: {str(e)}")


@router.get("/overview")
async def get_overview(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get SERP analysis overview for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        SERP analysis overview data
    """
    try:
        # Get user's SERP analysis statistics
        total_analyses_result = await db.execute(
            select(func.count(SERPAnalysis.id))
            .where(SERPAnalysis.user_id == current_user.id)
        )
        total_analyses = total_analyses_result.scalar() or 0
        
        # Get unique keywords count
        keywords_result = await db.execute(
            select(func.count(func.distinct(SERPAnalysis.query)))
            .where(SERPAnalysis.user_id == current_user.id)
        )
        keywords_tracked = keywords_result.scalar() or 0
        
        # Get unique competitors count
        competitors_result = await db.execute(
            select(func.count(func.distinct(CompetitorTracking.domain)))
            .where(CompetitorTracking.user_id == current_user.id)
        )
        competitors_monitored = competitors_result.scalar() or 0
        
        # Get last analysis date
        last_analysis_result = await db.execute(
            select(SERPAnalysis.created_at)
            .where(SERPAnalysis.user_id == current_user.id)
            .order_by(desc(SERPAnalysis.created_at))
            .limit(1)
        )
        last_analysis_row = last_analysis_result.first()
        last_analysis = last_analysis_row[0].isoformat() if last_analysis_row else None
        
        # Get SERP features count
        features_result = await db.execute(
            select(func.count(func.distinct(SERPFeatureTracking.feature_name)))
            .where(SERPFeatureTracking.user_id == current_user.id)
        )
        serp_features_analyzed = features_result.scalar() or 0
        
        # Calculate average metrics from recent analyses
        recent_analyses_result = await db.execute(
            select(
                SERPAnalysis.competition_level,
                SERPAnalysis.opportunity_score,
                SERPAnalysis.organic_count,
                SERPAnalysis.paid_count
            )
            .where(SERPAnalysis.user_id == current_user.id)
            .order_by(desc(SERPAnalysis.created_at))
            .limit(10)
        )
        recent_analyses = recent_analyses_result.all()
        
        # Calculate overview metrics
        if recent_analyses:
            competition_levels = [a.competition_level for a in recent_analyses if a.competition_level]
            competition_level = max(set(competition_levels), key=competition_levels.count) if competition_levels else "Medium"
            
            opportunity_scores = [a.opportunity_score for a in recent_analyses if a.opportunity_score]
            avg_opportunity_score = sum(opportunity_scores) // len(opportunity_scores) if opportunity_scores else 0
            
            organic_counts = [a.organic_count for a in recent_analyses]
            avg_organic_results = sum(organic_counts) // len(organic_counts) if organic_counts else 0
            
            paid_counts = [a.paid_count for a in recent_analyses]
            avg_paid_results = sum(paid_counts) // len(paid_counts) if paid_counts else 0
        else:
            competition_level = "Medium"
            avg_opportunity_score = 0
            avg_organic_results = 0
            avg_paid_results = 0
        
        # Check if both Google and SerpAPI are configured
        is_configured = programmable_search_service.is_configured() or serpapi_service.is_configured()
        
        return {
            "competition_level": competition_level,
            "opportunity_score": avg_opportunity_score,
            "organic_results": avg_organic_results,
            "paid_results": avg_paid_results,
            "local_results": 0,  # TODO: Implement local results tracking
            "video_results": 0,  # TODO: Implement video results tracking
            "total_analyses": total_analyses,
            "keywords_tracked": keywords_tracked,
            "competitors_monitored": competitors_monitored,
            "last_analysis": last_analysis,
            "serp_features_analyzed": serp_features_analyzed,
            "is_configured": is_configured
        }
        
    except Exception as e:
        logger.error(f"Error getting SERP overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get SERP overview: {str(e)}")


@router.get("/competitors")
async def get_competitors(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, description="Number of competitors to return")
) -> List[dict]:
    """
    Get competitor analysis data for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Number of competitors to return
        
    Returns:
        List of competitor analysis data
    """
    try:
        # Get user's tracked competitors
        competitors_result = await db.execute(
            select(CompetitorTracking)
            .where(CompetitorTracking.user_id == current_user.id)
            .order_by(desc(CompetitorTracking.updated_at))
            .limit(limit)
        )
        competitors = competitors_result.scalars().all()
        
        # If no competitors found, return empty list
        if not competitors:
            return []
        
        # Format competitor data
        competitor_data = []
        for comp in competitors:
            # Count keywords this competitor ranks for
            keywords_count = len(comp.positions) if comp.positions else 0
            
            # Get SERP features for this competitor from recent analyses
            features_result = await db.execute(
                select(func.distinct(SERPFeatureTracking.feature_name))
                .join(SERPAnalysis, SERPAnalysis.query == SERPFeatureTracking.query)
                .where(
                    SERPFeatureTracking.user_id == current_user.id,
                    SERPAnalysis.competitors.op('@>')([{'domain': comp.domain}])
                )
                .limit(5)
            )
            features = [f[0] for f in features_result.all()]
            
            competitor_data.append({
                "domain": comp.domain,
                "title": comp.title or comp.domain,
                "authority": comp.authority or 0,
                "backlinks": comp.backlinks or 0,
                "traffic": comp.traffic or 0,
                "keywords": comp.keywords or keywords_count,
                "avg_position": comp.avg_position or 0,
                "positions": comp.positions or {},
                "serp_features": features,
                "last_updated": comp.updated_at.isoformat() if comp.updated_at else None
            })
        
        return competitor_data
        
    except Exception as e:
        logger.error(f"Error getting competitors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get competitors: {str(e)}")


@router.get("/features")
async def get_features(
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, description="Number of features to return")
) -> List[dict]:
    """
    Get SERP features analysis for the current user's keywords.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Number of features to return
        
    Returns:
        List of SERP features found in user's analyses
    """
    try:
        # Get user's SERP features from tracking
        features_result = await db.execute(
            select(
                SERPFeatureTracking.feature_name,
                SERPFeatureTracking.feature_type,
                SERPFeatureTracking.position,
                SERPFeatureTracking.description,
                SERPFeatureTracking.ctr_impact,
                SERPFeatureTracking.query,
                func.count(SERPFeatureTracking.id).label("occurrences")
            )
            .where(SERPFeatureTracking.user_id == current_user.id)
            .group_by(
                SERPFeatureTracking.feature_name,
                SERPFeatureTracking.feature_type,
                SERPFeatureTracking.position,
                SERPFeatureTracking.description,
                SERPFeatureTracking.ctr_impact,
                SERPFeatureTracking.query
            )
            .order_by(desc("occurrences"))
            .limit(limit)
        )
        features = features_result.all()
        
        # If no features found, return empty list
        if not features:
            return []
        
        # Format feature data
        feature_data = []
        for feat in features:
            feature_data.append({
                "name": feat.feature_name,
                "type": feat.feature_type,
                "position": feat.position or "varies",
                "description": feat.description or f"SERP feature: {feat.feature_name}",
                "ctr_impact": feat.ctr_impact or "Medium",
                "query": feat.query,
                "occurrences": feat.occurrences
            })
        
        return feature_data
        
    except Exception as e:
        logger.error(f"Error getting SERP features: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch SERP features: {str(e)}")
