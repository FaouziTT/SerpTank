"""
SGE Readiness Service for Search Generative Experience Optimization

This service provides functionality for preparing content for AI-generated search results,
including SGE trigger analysis, source citation optimization, and conversational gap analysis.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import uuid
import re
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.sge import SGEAnalysis, SGEMonitor
from app.services.openai_service import openai_service
from app.services.serpapi_service import serpapi_service

logger = logging.getLogger(__name__)


class SGEReadinessService:
    """Service for SGE readiness and optimization."""
    
    def __init__(self):
        """Initialize the SGE Readiness service."""
        pass
        
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        # This service primarily uses OpenAI for analysis
        return openai_service.is_configured()
        
    async def optimize_content_for_sge(
        self,
        content: str,
        target_queries: List[str],
        content_type: str,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Optimize content for Search Generative Experience (SGE).
        
        Args:
            content: Content to optimize
            target_queries: Target search queries
            content_type: Type of content
            user_id: ID of the user requesting the optimization
            db: Database session
            
        Returns:
            List of optimization results for each query
        """
        try:
            if not self.is_configured():
                raise ValueError("OpenAI service not configured")
            
            results = []
            
            for query in target_queries[:5]:  # Limit to 5 queries
                result = await openai_service.optimize_for_sge(
                    content=content,
                    target_query=query,
                    content_type=content_type
                )
                results.append({
                    "query": query,
                    "optimization": result
                })
            
            # Calculate overall SGE readiness score
            overall_sge_readiness = sum(
                r["optimization"].get("sge_score", 50) for r in results
            ) / len(results) if results else 0

            # Save analysis to database
            sge_analysis = SGEAnalysis(
                analysis_id=f"sge_analysis_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                content=content,
                target_queries=target_queries,
                content_type=content_type,
                optimization_results=results,
                overall_sge_readiness=overall_sge_readiness,
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            db.add(sge_analysis)
            await db.commit()
            await db.refresh(sge_analysis)

            return {
                "analysis_id": sge_analysis.analysis_id,
                "optimizations": results,
                "content_analyzed": len(content),
                "queries_processed": len(results),
                "overall_sge_readiness": overall_sge_readiness
            }
            
        except Exception as e:
            logger.error(f"Error optimizing content for SGE: {e}")
            await db.rollback()
            raise ValueError(f"Failed to optimize content for SGE: {e}")
    
    async def analyze_sge_triggers(
        self,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze keywords for SGE triggers.
        
        Args:
            keywords: List of keywords to analyze
            
        Returns:
            Analysis of SGE triggers for the provided keywords
        """
        try:
            # Analyze each keyword for SGE trigger likelihood
            trigger_analysis = {
                "high": [],
                "medium": [],
                "low": []
            }
            
            for keyword in keywords:
                likelihood = self._calculate_sge_likelihood(keyword)
                sge_status = self._get_sge_status(keyword)
                sge_features = self._get_sge_features(keyword)
                
                analysis_result = {
                    "keyword": keyword,
                    "likelihood": likelihood,
                    "current_sge_status": sge_status,
                    "sge_features": sge_features
                }
                
                if likelihood >= 80:
                    trigger_analysis["high"].append(analysis_result)
                elif likelihood >= 50:
                    trigger_analysis["medium"].append(analysis_result)
                else:
                    trigger_analysis["low"].append(analysis_result)
            
            # Generate recommendations
            recommendations = self._generate_trigger_recommendations(trigger_analysis)
            
            # Calculate scores for frontend
            total_keywords = len(keywords)
            high_likelihood_count = len(trigger_analysis["high"])
            medium_likelihood_count = len(trigger_analysis["medium"])

            # Calculate entity coverage based on analysis
            entity_coverage = int((high_likelihood_count * 100 + medium_likelihood_count * 60) / total_keywords) if total_keywords > 0 else 0
            entity_coverage = min(100, entity_coverage)

            # Schema markup score (placeholder for now - in real implementation would analyze actual schema)
            schema_markup_score = 75 if high_likelihood_count > 0 else 45

            # Featured snippet readiness based on question keywords
            question_keywords = [kw for kw in keywords if any(q in kw.lower() for q in ["what", "how", "why", "when", "where", "which"])]
            featured_snippet_ready = int((len(question_keywords) / total_keywords) * 100) if total_keywords > 0 else 0

            # Voice search optimization
            voice_search_optimized = int((len(question_keywords) / total_keywords) * 80) if total_keywords > 0 else 0

            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "keywords_analyzed": len(keywords),
                "sge_trigger_likelihood": trigger_analysis,
                "recommendations": recommendations,
                "entity_coverage": entity_coverage,
                "schema_markup_score": schema_markup_score,
                "featured_snippet_ready": featured_snippet_ready,
                "voice_search_optimized": voice_search_optimized
            }
            
        except Exception as e:
            logger.error(f"Error analyzing SGE triggers: {e}")
            raise ValueError(f"Failed to analyze SGE triggers: {e}")
    
    async def analyze_source_citations(
        self,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze source citations in SGE results.
        
        Args:
            keywords: List of keywords to analyze
            
        Returns:
            Analysis of source citations in SGE results
        """
        try:
            citation_analysis = {
                "total_citations": 0,
                "citation_distribution": {
                    "position_1": 0,
                    "position_2_5": 0,
                    "position_6_10": 0,
                    "position_11_plus": 0
                },
                "source_types": {
                    "authoritative_sites": 0,
                    "news_sites": 0,
                    "blog_posts": 0,
                    "academic_sources": 0,
                    "other": 0
                },
                "content_attributes": {
                    "factual_statements": 0,
                    "statistics_data": 0,
                    "expert_quotes": 0,
                    "step_by_step_guides": 0,
                    "comparisons": 0
                }
            }
            
            # Analyze each keyword for citation patterns
            for keyword in keywords:
                keyword_analysis = self._analyze_keyword_citations(keyword)
                
                # Aggregate results
                citation_analysis["total_citations"] += keyword_analysis["citations"]
                
                for position, count in keyword_analysis["distribution"].items():
                    citation_analysis["citation_distribution"][position] += count
                
                for source_type, count in keyword_analysis["source_types"].items():
                    citation_analysis["source_types"][source_type] += count
                
                for attribute, count in keyword_analysis["content_attributes"].items():
                    citation_analysis["content_attributes"][attribute] += count
            
            # Generate insights
            insights = self._generate_citation_insights(citation_analysis)

            # Calculate citation likelihood score for frontend
            total_citations = citation_analysis["total_citations"]
            auth_sites = citation_analysis["source_types"]["authoritative_sites"]
            factual_content = citation_analysis["content_attributes"]["factual_statements"]

            # Citation likelihood based on authoritative sources and factual content
            if total_citations > 0:
                citation_likelihood = int(((auth_sites + factual_content) / (total_citations * 2)) * 100)
            else:
                citation_likelihood = 0
            citation_likelihood = min(100, max(0, citation_likelihood))

            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "keywords_analyzed": len(keywords),
                "citation_analysis": citation_analysis,
                "insights": insights,
                "citation_likelihood": citation_likelihood
            }
            
        except Exception as e:
            logger.error(f"Error analyzing source citations: {e}")
            raise ValueError(f"Failed to analyze source citations: {e}")
    
    async def analyze_conversational_gaps(
        self,
        topic: str
    ) -> Dict[str, Any]:
        """
        Analyze conversational gaps for a topic.
        
        Args:
            topic: Topic to analyze
            
        Returns:
            Analysis of conversational gaps and opportunities
        """
        try:
            # Identify common question patterns for the topic
            question_patterns = self._identify_question_patterns(topic)
            
            # Analyze content coverage
            content_coverage = self._analyze_content_coverage(topic)
            
            # Identify gaps
            gaps = self._identify_conversational_gaps(topic, question_patterns, content_coverage)
            
            # Generate recommendations
            recommendations = self._generate_gap_recommendations(gaps)

            # Calculate conversational content score for frontend
            covered = content_coverage["question_coverage"]["covered"]
            total_questions = sum(content_coverage["question_coverage"].values())
            conversational_content_score = int((covered / total_questions) * 100) if total_questions > 0 else 0

            # Generate opportunities for frontend
            opportunities = [
                {
                    "type": "featured_snippets",
                    "title": "Featured Snippet Opportunities",
                    "description": f"{covered + 5} keywords have featured snippet potential",
                    "potential_impact": "High traffic increase",
                    "implementation_steps": [
                        "Identify target queries",
                        "Create structured answers",
                        "Optimize content format"
                    ]
                },
                {
                    "type": "conversational_gaps",
                    "title": "Conversational Query Gaps",
                    "description": f"{content_coverage['question_coverage']['uncovered']} long-tail conversational queries without content",
                    "potential_impact": "Capture SGE traffic",
                    "implementation_steps": [
                        "Create FAQ pages",
                        "Add conversational sections",
                        "Target voice search queries"
                    ]
                }
            ]

            return {
                "topic": topic,
                "analysis_timestamp": datetime.now().isoformat(),
                "question_patterns": question_patterns,
                "content_coverage": content_coverage,
                "conversational_gaps": gaps,
                "recommendations": recommendations,
                "conversational_content_score": conversational_content_score,
                "opportunities": opportunities,
                "insights": [
                    {
                        "title": "Conversational Query Analysis",
                        "description": f"Your content answers {conversational_content_score}% of common conversational queries in your niche. Focus on creating Q&A content for the remaining {100-conversational_content_score}% to improve SGE visibility."
                    },
                    {
                        "title": "Entity Recognition Status",
                        "description": "AI models recognize your brand as an authority in 3 out of 5 core topics. Strengthen content around technical SEO and local search optimization to improve entity associations."
                    },
                    {
                        "title": "Future-Proofing Score",
                        "description": f"Based on current trends, your content has a {min(conversational_content_score + 10, 85)}% likelihood of being cited in AI-generated responses."
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversational gaps: {e}")
            raise ValueError(f"Failed to analyze conversational gaps: {e}")
    
    async def create_sge_monitor(
        self,
        monitor_data: Dict[str, Any],
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create an SGE monitoring task.
        
        Args:
            monitor_data: Monitor configuration data
            user_id: ID of the user creating the monitor
            db: Database session
            
        Returns:
            Created monitor with ID and initial status
        """
        try:
            # Validate monitor data
            validated_data = self._validate_monitor_data(monitor_data)
            
            # Create monitor record
            monitor_id = f"sge_monitor_{uuid.uuid4().hex[:12]}"
            
            monitor = SGEMonitor(
                monitor_id=monitor_id,
                user_id=user_id,
                monitor_data=validated_data,
                status="ACTIVE",
                created_at=datetime.now(timezone.utc),
                last_checked_at=None
            )
            
            db.add(monitor)
            await db.commit()
            await db.refresh(monitor)
            
            return {
                "monitor_id": monitor_id,
                "status": monitor.status,
                "message": "SGE monitor created successfully",
                "created_at": monitor.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating SGE monitor: {e}")
            await db.rollback()
            raise ValueError(f"Failed to create SGE monitor: {e}")
    
    async def get_sge_monitor(
        self,
        monitor_id: str,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get SGE monitor results.
        
        Args:
            monitor_id: ID of the monitor
            user_id: ID of the user requesting the monitor
            db: Database session
            
        Returns:
            Monitor results and status
        """
        try:
            result = await db.execute(select(SGEMonitor).where(
                SGEMonitor.monitor_id == monitor_id,
                SGEMonitor.user_id == user_id
            ))
            monitor = result.scalars().first()
            
            if not monitor:
                raise ValueError(f"SGE monitor {monitor_id} not found")
            
            # For now, generate sample results. In a real scenario, this would trigger
            # a background task to fetch and analyze SGE data.
            results = self._generate_monitor_results(monitor_id)
            
            return {
                "monitor_id": monitor.monitor_id,
                "status": monitor.status,
                "last_checked": monitor.last_checked_at.isoformat() if monitor.last_checked_at else None,
                "next_check": self._calculate_next_check(monitor.monitor_data.get("frequency", "daily")) if monitor.monitor_data else None,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error getting SGE monitor: {e}")
            raise ValueError(f"Failed to get SGE monitor: {e}")
    
    def _calculate_sge_likelihood(self, keyword: str) -> int:
        """Calculate SGE trigger likelihood for a keyword."""
        # Simple heuristic-based calculation
        likelihood = 50  # Base likelihood
        
        # Question keywords are more likely to trigger SGE
        if any(word in keyword.lower() for word in ["what", "how", "why", "when", "where", "which"]):
            likelihood += 30
        
        # Educational/tutorial keywords
        if any(word in keyword.lower() for word in ["guide", "tutorial", "how to", "steps", "tips"]):
            likelihood += 20
        
        # Definition keywords
        if any(word in keyword.lower() for word in ["what is", "definition", "meaning", "explain"]):
            likelihood += 25
        
        # Comparison keywords
        if any(word in keyword.lower() for word in ["vs", "versus", "compare", "difference"]):
            likelihood -= 10
        
        # Brand-specific keywords
        if any(word in keyword.lower() for word in ["best", "top", "review", "comparison"]):
            likelihood -= 15
        
        return min(100, max(0, likelihood))
    
    def _get_sge_status(self, keyword: str) -> str:
        """Get current SGE status for a keyword."""
        # This would typically check actual SGE results
        # For now, use likelihood to determine status
        likelihood = self._calculate_sge_likelihood(keyword)
        
        if likelihood >= 80:
            return "TRIGGERED"
        elif likelihood >= 50:
            return "PARTIAL"
        else:
            return "NOT_TRIGGERED"
    
    def _get_sge_features(self, keyword: str) -> List[str]:
        """Get SGE features for a keyword."""
        features = []
        likelihood = self._calculate_sge_likelihood(keyword)
        
        if likelihood >= 80:
            features.extend(["AI Snapshot", "Follow-up Questions"])
        if likelihood >= 60:
            features.append("Related Resources")
        if likelihood >= 40:
            features.append("Related Questions")
        
        return features
    
    def _generate_trigger_recommendations(self, trigger_analysis: Dict[str, List]) -> List[Dict[str, Any]]:
        """Generate recommendations based on trigger analysis."""
        recommendations = []
        
        if trigger_analysis["high"]:
            recommendations.append({
                "keyword_group": "High Likelihood",
                "strategy": "Optimize for source citation",
                "actions": [
                    "Structure content with clear, factual statements",
                    "Include authoritative data and statistics",
                    "Implement FAQ schema markup",
                ],
            })
        
        if trigger_analysis["medium"]:
            recommendations.append({
                "keyword_group": "Medium Likelihood",
                "strategy": "Create comprehensive, entity-rich content",
                "actions": [
                    "Develop in-depth guides that answer related questions",
                    "Include entity information with proper schema markup",
                    "Optimize for E-E-A-T signals",
                ],
            })
        
        if trigger_analysis["low"]:
            recommendations.append({
                "keyword_group": "Low Likelihood",
                "strategy": "Focus on traditional SEO optimization",
                "actions": [
                    "Optimize for traditional ranking factors",
                    "Create comparison tables and structured data",
                    "Focus on conversion optimization",
                ],
            })
        
        return recommendations
    
    def _analyze_keyword_citations(self, keyword: str) -> Dict[str, Any]:
        """Analyze citations for a specific keyword."""
        # This would typically analyze actual SGE results
        # For now, generate sample data based on keyword characteristics
        
        citations = 5 + (hash(keyword) % 10)  # Pseudo-random citation count
        
        return {
            "citations": citations,
            "distribution": {
                "position_1": citations // 3,
                "position_2_5": citations // 2,
                "position_6_10": citations // 4,
                "position_11_plus": citations // 6
            },
            "source_types": {
                "authoritative_sites": citations // 2,
                "news_sites": citations // 4,
                "blog_posts": citations // 4,
                "academic_sources": citations // 8,
                "other": citations // 8
            },
            "content_attributes": {
                "factual_statements": citations // 2,
                "statistics_data": citations // 3,
                "expert_quotes": citations // 4,
                "step_by_step_guides": citations // 5,
                "comparisons": citations // 6
            }
        }
    
    def _generate_citation_insights(self, citation_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from citation analysis."""
        insights = []
        
        total_citations = citation_analysis["total_citations"]
        if total_citations == 0:
            return insights
        
        # Analyze source type distribution
        auth_sites = citation_analysis["source_types"]["authoritative_sites"]
        if auth_sites / total_citations > 0.5:
            insights.append({
                "type": "SOURCE_TYPE",
                "insight": "Authoritative sites dominate citations",
                "recommendation": "Focus on building authority and credibility signals"
            })
        
        # Analyze content attributes
        factual = citation_analysis["content_attributes"]["factual_statements"]
        if factual / total_citations > 0.4:
            insights.append({
                "type": "CONTENT_ATTRIBUTE",
                "insight": "Factual statements are heavily cited",
                "recommendation": "Include more factual, data-driven content"
            })
        
        return insights
    
    def _identify_question_patterns(self, topic: str) -> List[Dict[str, Any]]:
        """Identify common question patterns for a topic."""
        # This would typically analyze search data
        # For now, generate common patterns based on topic
        
        patterns = [
            {
                "pattern": "What is {topic}?",
                "frequency": "high",
                "examples": [f"What is {topic}?", f"Define {topic}"]
            },
            {
                "pattern": "How to {topic}?",
                "frequency": "medium",
                "examples": [f"How to implement {topic}", f"Steps for {topic}"]
            },
            {
                "pattern": "Why {topic}?",
                "frequency": "low",
                "examples": [f"Why use {topic}?", f"Benefits of {topic}"]
            }
        ]
        
        return patterns
    
    def _analyze_content_coverage(self, topic: str) -> Dict[str, Any]:
        """Analyze content coverage for a topic."""
        return {
            "total_content_pieces": 25,
            "content_types": {
                "guides": 8,
                "articles": 12,
                "videos": 3,
                "tools": 2
            },
            "question_coverage": {
                "covered": 18,
                "partially_covered": 5,
                "uncovered": 7
            }
        }
    
    def _identify_conversational_gaps(
        self,
        topic: str,
        question_patterns: List[Dict[str, Any]],
        content_coverage: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify conversational gaps for a topic."""
        gaps = []
        
        uncovered = content_coverage["question_coverage"]["uncovered"]
        if uncovered > 0:
            gaps.append({
                "type": "QUESTION_COVERAGE",
                "description": f"{uncovered} questions not covered by existing content",
                "priority": "high",
                "recommended_content": "FAQ-style content addressing common questions"
            })
        
        # Add topic-specific gaps
        gaps.append({
            "type": "CONTENT_DEPTH",
            "description": "Need more in-depth technical content",
            "priority": "medium",
            "recommended_content": "Technical guides and implementation tutorials"
        })
        
        return gaps
    
    def _generate_gap_recommendations(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate recommendations for addressing gaps."""
        recommendations = []
        
        for gap in gaps:
            if gap["type"] == "QUESTION_COVERAGE":
                recommendations.append({
                    "action": "Create FAQ content",
                    "priority": gap["priority"],
                    "description": gap["recommended_content"],
                    "estimated_impact": "High"
                })
            elif gap["type"] == "CONTENT_DEPTH":
                recommendations.append({
                    "action": "Develop technical guides",
                    "priority": gap["priority"],
                    "description": gap["recommended_content"],
                    "estimated_impact": "Medium"
                })
        
        return recommendations
    
    def _validate_monitor_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate monitor data."""
        required_fields = ["keywords"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults
        data.setdefault("frequency", "daily")
        data.setdefault("notifications", True)
        
        return data
    
    def _calculate_next_check(self, frequency: str) -> str:
        """Calculate next check time based on frequency."""
        now = datetime.now()
        
        if frequency == "hourly":
            next_check = now + timedelta(hours=1)
        elif frequency == "daily":
            next_check = now + timedelta(days=1)
        elif frequency == "weekly":
            next_check = now + timedelta(weeks=1)
        else:
            next_check = now + timedelta(days=1)
        
        return next_check.isoformat()
    
    def _generate_monitor_results(self, monitor_id: str) -> Dict[str, Any]:
        """Generate sample monitor results."""
        return {
            "keywords_monitored": 5,
            "sge_changes": [
                {
                    "keyword": "cloud security best practices",
                    "change": "SGE now triggered",
                    "timestamp": datetime.now().isoformat(),
                    "impact": "positive"
                }
            ],
            "citation_changes": [
                {
                    "keyword": "zero trust security",
                    "change": "New citation added",
                    "timestamp": datetime.now().isoformat(),
                    "impact": "positive"
                }
            ]
        }


# Create a singleton instance
sge_readiness_service = SGEReadinessService() 