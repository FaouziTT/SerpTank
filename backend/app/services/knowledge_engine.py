"""
Knowledge Engine Service for Institutional Knowledge Management

This service provides functionality for creating a compounding competitive advantage
through strategic ledger tracking, private tuning loops, and evolving intelligence.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import uuid
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.knowledge import StrategicLedger, TuningInsight, PersonalizedRecommendation, CapturedKnowledge, CompetitiveIntelligence
from app.services.openai_service import openai_service
from app.services.serpapi import serpapi_service

logger = logging.getLogger(__name__)


class KnowledgeEngineService:
    """Service for institutional knowledge management and strategic insights."""
    
    def __init__(self):
        """Initialize the Knowledge Engine service."""
        pass
        
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        # This service primarily uses OpenAI for insights
        return openai_service.is_configured()
        
    async def generate_seo_insights(
        self,
        website_data: Dict[str, Any],
        competitor_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered SEO insights and recommendations.
        
        Args:
            website_data: Website analysis data
            competitor_data: Optional competitor analysis data
            
        Returns:
            AI-generated SEO insights and recommendations
        """
        try:
            if not self.is_configured():
                raise ValueError("OpenAI service not configured")
            
            # Prepare context for AI analysis
            analysis_context = {
                "website_data": website_data,
                "competitor_data": competitor_data,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Generate insights using OpenAI
            insights = await openai_service.generate_seo_insights(
                website_data=website_data,
                competitor_data=competitor_data
            )
            
            # Store insights in knowledge base (placeholder)
            await self._store_insights(insights, analysis_context)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating SEO insights: {e}")
            raise ValueError(f"Failed to generate SEO insights: {e}")
    
    async def get_strategic_ledger(
        self,
        timeframe: str,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get the strategic ledger for tracking executed strategies.
        
        Args:
            timeframe: Timeframe filter (all, year, quarter, month)
            user_id: ID of the user requesting the ledger
            db: Database session
            
        Returns:
            Strategic ledger with executed strategies and outcomes
        """
        try:
            # Calculate date range based on timeframe
            start_date, end_date = self._calculate_date_range(timeframe)
            
            # Retrieve strategies from database
            query = select(StrategicLedger).where(
                StrategicLedger.user_id == user_id,
                StrategicLedger.created_at >= start_date,
                StrategicLedger.created_at <= end_date
            )
            result = await db.execute(query)
            strategies = result.scalars().all()
            
            # Calculate aggregate insights
            aggregate_insights = self._calculate_aggregate_insights(strategies)
            
            return {
                "timeframe": timeframe,
                "date_range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "total_strategies": len(strategies),
                "strategies": [s.to_dict() for s in strategies],
                "aggregate_insights": aggregate_insights
            }
            
        except Exception as e:
            logger.error(f"Error getting strategic ledger: {e}")
            raise ValueError(f"Failed to get strategic ledger: {e}")
    
    async def get_tuning_insights(
        self,
        model_type: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get tuning insights for model optimization.
        
        Args:
            model_type: Type of model insights (all, content, keyword, audience)
            user_id: ID of the user requesting insights
            
        Returns:
            Tuning insights and optimization recommendations
        """
        try:
            # Retrieve model performance data (placeholder)
            model_data = await self._get_model_performance_data(user_id, model_type)
            
            # Generate tuning recommendations
            tuning_recommendations = self._generate_tuning_recommendations(model_data)
            
            return {
                "model_type": model_type,
                "performance_metrics": model_data,
                "tuning_recommendations": tuning_recommendations,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting tuning insights: {e}")
            raise ValueError(f"Failed to get tuning insights: {e}")
    
    async def get_personalized_recommendations(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get personalized recommendations based on user's historical data.
        
        Args:
            user_id: ID of the user requesting recommendations
            db: Database session
            
        Returns:
            Personalized recommendations and insights
        """
        try:
            # Get user's historical performance data
            user_data = await self._get_user_performance_data(user_id, db)
            
            # Generate personalized recommendations
            recommendations = self._generate_personalized_recommendations(user_data)

            # Store personalized recommendations
            personalized_rec = PersonalizedRecommendation(
                recommendation_id=f"rec_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                recommendations=recommendations,
                confidence_scores=self._calculate_confidence_scores(recommendations),
                generated_at=datetime.now(timezone.utc)
            )
            db.add(personalized_rec)
            await db.commit()
            await db.refresh(personalized_rec)
            
            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "confidence_scores": self._calculate_confidence_scores(recommendations),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            raise ValueError(f"Failed to get personalized recommendations: {e}")
    
    async def capture_knowledge(
        self,
        knowledge_data: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Capture new knowledge and insights.
        
        Args:
            knowledge_data: Knowledge data to capture
            user_id: ID of the user capturing knowledge
            
        Returns:
            Confirmation of knowledge capture
        """
        try:
            # Validate knowledge data
            validated_data = self._validate_knowledge_data(knowledge_data)
            
            # Store knowledge in database (placeholder)
            knowledge_id = await self._store_knowledge(validated_data, user_id)
            
            # Update related models if needed
            await self._update_related_models(knowledge_id, validated_data)
            
            return {
                "knowledge_id": knowledge_id,
                "status": "CAPTURED",
                "message": "Knowledge captured successfully",
                "captured_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error capturing knowledge: {e}")
            raise ValueError(f"Failed to capture knowledge: {e}")
    
    async def get_competitive_intelligence(
        self,
        competitors: List[str],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get competitive intelligence analysis.
        
        Args:
            competitors: List of competitor domains to analyze
            user_id: ID of the user requesting intelligence
            
        Returns:
            Competitive intelligence analysis
        """
        try:
            # Analyze competitors (placeholder implementation)
            intelligence_data = await self._analyze_competitors(competitors)
            
            # Generate insights from competitive data
            insights = self._generate_competitive_insights(intelligence_data)
            
            return {
                "competitors_analyzed": competitors,
                "intelligence_data": intelligence_data,
                "insights": insights,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting competitive intelligence: {e}")
            raise ValueError(f"Failed to get competitive intelligence: {e}")
    
    def _calculate_date_range(self, timeframe: str) -> Dict[str, str]:
        """Calculate date range based on timeframe."""
        now = datetime.now()
        
        if timeframe == "month":
            start_date = now.replace(day=1)
        elif timeframe == "quarter":
            quarter_start = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=quarter_start, day=1)
        elif timeframe == "year":
            start_date = now.replace(month=1, day=1)
        else:  # all
            start_date = now - timedelta(days=365*2)  # 2 years back
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat()
        }
    
    async def _get_strategies_from_db(self, user_id: int, date_range: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get strategies from database (placeholder)."""
        # This would typically query the database
        # For now, return sample data
        return [
            {
                "id": f"strat_{uuid.uuid4().hex[:8]}",
                "name": "Enterprise Cloud Security Content Pillar",
                "type": "CONTENT_STRATEGY",
                "status": "COMPLETED",
                "execution_period": {
                    "start_date": "2025-01-15",
                    "end_date": "2025-04-30",
                },
                "key_metrics": {
                    "traffic_change": "+135%",
                    "keyword_rankings": {
                        "top_3": 8,
                        "top_10": 24,
                        "top_20": 42,
                    },
                    "leads_generated": 156,
                    "revenue_attributed": 780000,
                    "roi": 420,
                },
                "learnings": [
                    {
                        "category": "CONTENT_FORMAT",
                        "learning": "Long-form guides (4000+ words) with interactive elements outperformed shorter content by 3x",
                        "confidence": "HIGH",
                        "supporting_data": "Comparison of 5 long-form vs 8 short-form pieces",
                    }
                ],
            }
        ]
    
    def _calculate_aggregate_insights(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregate insights from strategies."""
        if not strategies:
            return {}
        
        # Calculate average ROI by strategy type
        strategy_types = {}
        for strategy in strategies:
            strategy_type = strategy.get("type", "UNKNOWN")
            roi = strategy.get("key_metrics", {}).get("roi", 0)
            
            if strategy_type not in strategy_types:
                strategy_types[strategy_type] = {"total_roi": 0, "count": 0}
            
            strategy_types[strategy_type]["total_roi"] += roi
            strategy_types[strategy_type]["count"] += 1
        
        # Calculate averages
        most_effective_strategies = []
        for strategy_type, data in strategy_types.items():
            avg_roi = data["total_roi"] / data["count"]
            most_effective_strategies.append({
                "type": strategy_type,
                "average_roi": round(avg_roi, 1)
            })
        
        # Sort by average ROI
        most_effective_strategies.sort(key=lambda x: x["average_roi"], reverse=True)
        
        return {
            "most_effective_strategy_types": most_effective_strategies[:3],
            "total_revenue_attributed": sum(
                s.get("key_metrics", {}).get("revenue_attributed", 0) for s in strategies
            ),
            "average_roi": round(
                sum(s.get("key_metrics", {}).get("roi", 0) for s in strategies) / len(strategies), 1
            ) if strategies else 0
        }
    
    async def _get_model_performance_data(self, user_id: int, model_type: str) -> Dict[str, Any]:
        """Get model performance data (placeholder)."""
        return {
            "content_model": {
                "accuracy": 0.87,
                "precision": 0.82,
                "recall": 0.91,
                "f1_score": 0.86,
                "training_samples": 1250,
                "last_updated": "2025-06-15T10:30:00Z"
            },
            "keyword_model": {
                "accuracy": 0.79,
                "precision": 0.75,
                "recall": 0.83,
                "f1_score": 0.79,
                "training_samples": 890,
                "last_updated": "2025-06-10T14:20:00Z"
            },
            "audience_model": {
                "accuracy": 0.84,
                "precision": 0.81,
                "recall": 0.88,
                "f1_score": 0.84,
                "training_samples": 1100,
                "last_updated": "2025-06-12T09:15:00Z"
            }
        }
    
    def _generate_tuning_recommendations(self, model_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tuning recommendations based on model performance."""
        recommendations = []
        
        for model_name, metrics in model_data.items():
            if metrics["f1_score"] < 0.85:
                recommendations.append({
                    "model": model_name,
                    "issue": "Low F1 Score",
                    "recommendation": f"Increase training data for {model_name} model",
                    "priority": "HIGH",
                    "estimated_impact": "15-20% improvement in accuracy"
                })
            
            if metrics["precision"] < 0.80:
                recommendations.append({
                    "model": model_name,
                    "issue": "Low Precision",
                    "recommendation": f"Adjust classification thresholds for {model_name}",
                    "priority": "MEDIUM",
                    "estimated_impact": "10-15% improvement in precision"
                })
        
        return recommendations
    
    async def _get_user_performance_data(self, user_id: int) -> Dict[str, Any]:
        """Get user's historical performance data (placeholder)."""
        return {
            "total_campaigns": 24,
            "successful_campaigns": 18,
            "average_roi": 320,
            "best_performing_channels": ["Organic Search", "LinkedIn"],
            "content_performance": {
                "long_form": {"avg_traffic": 1500, "avg_conversions": 45},
                "short_form": {"avg_traffic": 800, "avg_conversions": 25},
                "video": {"avg_traffic": 2200, "avg_conversions": 65}
            },
            "keyword_performance": {
                "high_volume": {"avg_rank": 8, "avg_traffic": 1200},
                "medium_volume": {"avg_rank": 12, "avg_traffic": 600},
                "long_tail": {"avg_rank": 5, "avg_traffic": 300}
            }
        }
    
    def _generate_personalized_recommendations(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate personalized recommendations based on user data."""
        recommendations = []
        
        # Content recommendations
        if user_data["content_performance"]["video"]["avg_conversions"] > 50:
            recommendations.append({
                "category": "CONTENT_STRATEGY",
                "recommendation": "Increase video content production - your video content converts 2.6x better than other formats",
                "priority": "HIGH",
                "expected_impact": "+40% conversion rate improvement"
            })
        
        # Channel recommendations
        if "Organic Search" in user_data["best_performing_channels"]:
            recommendations.append({
                "category": "CHANNEL_OPTIMIZATION",
                "recommendation": "Focus on technical SEO improvements - organic search is your top performing channel",
                "priority": "HIGH",
                "expected_impact": "+25% organic traffic growth"
            })
        
        # ROI recommendations
        if user_data["average_roi"] > 300:
            recommendations.append({
                "category": "BUDGET_ALLOCATION",
                "recommendation": "Increase budget allocation to high-ROI campaigns - your average ROI of 320% is excellent",
                "priority": "MEDIUM",
                "expected_impact": "+15% overall revenue growth"
            })
        
        return recommendations
    
    def _calculate_confidence_scores(self, recommendations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate confidence scores for recommendations."""
        confidence_scores = {}
        
        for rec in recommendations:
            # Simple confidence calculation based on data availability
            base_confidence = 0.7
            
            if rec["category"] == "CONTENT_STRATEGY":
                base_confidence += 0.1  # Content data is usually more reliable
            elif rec["category"] == "CHANNEL_OPTIMIZATION":
                base_confidence += 0.05
            
            if rec["priority"] == "HIGH":
                base_confidence += 0.1
            
            confidence_scores[rec["recommendation"][:50]] = min(0.95, base_confidence)
        
        return confidence_scores
    
    def _validate_knowledge_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean knowledge data."""
        required_fields = ["title", "category", "insights"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults for optional fields
        data.setdefault("confidence_level", "MEDIUM")
        data.setdefault("tags", [])
        data.setdefault("source", "manual_entry")
        
        return data
    
    async def _store_knowledge(self, knowledge_data: Dict[str, Any], user_id: int) -> str:
        """Store knowledge in database (placeholder)."""
        knowledge_id = f"knowledge_{uuid.uuid4().hex[:12]}"
        # This would typically store in database
        return knowledge_id
    
    async def _update_related_models(self, knowledge_id: str, knowledge_data: Dict[str, Any]) -> None:
        """Update related models with new knowledge (placeholder)."""
        # This would typically update ML models with new insights
        pass
    
    async def _analyze_competitors(self, competitors: List[str]) -> Dict[str, Any]:
        """Analyze competitors (placeholder)."""
        return {
            "competitors": {
                competitor: {
                    "domain_authority": 75 + (hash(competitor) % 25),  # Pseudo-random
                    "organic_keywords": 1000 + (hash(competitor) % 5000),
                    "organic_traffic": 50000 + (hash(competitor) % 100000),
                    "content_analysis": {
                        "avg_content_length": 1800 + (hash(competitor) % 1000),
                        "content_frequency": "weekly",
                        "top_content_types": ["blog_posts", "guides", "case_studies"]
                    }
                }
                for competitor in competitors
            }
        }
    
    def _generate_competitive_insights(self, intelligence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from competitive intelligence data."""
        insights = []
        
        competitors = intelligence_data.get("competitors", {})
        if not competitors:
            return insights
        
        # Analyze content strategies
        avg_content_length = sum(
            comp["content_analysis"]["avg_content_length"] 
            for comp in competitors.values()
        ) / len(competitors)
        
        insights.append({
            "category": "CONTENT_STRATEGY",
            "insight": f"Competitors average {round(avg_content_length)} words per content piece",
            "recommendation": "Consider increasing content depth to match competitor standards",
            "confidence": "HIGH"
        })
        
        # Analyze traffic patterns
        traffic_values = [comp["organic_traffic"] for comp in competitors.values()]
        max_traffic = max(traffic_values)
        
        insights.append({
            "category": "TRAFFIC_ANALYSIS",
            "insight": f"Top competitor generates {max_traffic:,} monthly organic visits",
            "recommendation": "Focus on high-volume keywords to compete for traffic",
            "confidence": "MEDIUM"
        })
        
        return insights
    
    async def _store_insights(self, insights: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Store insights in knowledge base (placeholder)."""
        # This would typically store insights for future reference
        pass


# Create a singleton instance
knowledge_engine_service = KnowledgeEngineService() 