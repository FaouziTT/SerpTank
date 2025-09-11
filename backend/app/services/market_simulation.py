"""
Market Simulation Service for Strategic Planning

This service provides functionality for creating and analyzing market scenarios,
including "what-if" analysis, strategic playbooks, and threat response planning.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.user import User
from app.models.organization import Organization
from app.models.scenario import Scenario, Playbook, ThreatScenario
from app.services.serpapi_service import serpapi_service
from app.services.google_trends_service import google_trends_service

logger = logging.getLogger(__name__)


class MarketSimulationService:
    """Service for market simulation and strategic planning."""
    
    def __init__(self):
        """Initialize the Market Simulation service."""
        # Remove database session from constructor - will be passed to methods
        
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        # This service doesn't require external API keys, but could be extended
        return True
        
    async def create_scenario(
        self,
        scenario_data: Dict[str, Any],
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create a new market simulation scenario.
        
        Args:
            scenario_data: Scenario parameters and configuration
            user_id: ID of the user creating the scenario
            db: Database session
            
        Returns:
            Created scenario with ID and initial status
        """
        try:
            scenario_id = f"scenario_{uuid.uuid4().hex[:12]}"
            
            # Validate scenario data
            validated_data = self._validate_scenario_data(scenario_data)
            
            # Create scenario record in database
            scenario = Scenario(
                scenario_id=scenario_id,
                user_id=user_id,
                name=validated_data.get("name", "Untitled Scenario"),
                description=validated_data.get("description", ""),
                parameters=validated_data,
                status="PROCESSING"
            )
            
            db.add(scenario)
            await db.commit()
            await db.refresh(scenario)
            
            return {
                "scenario_id": scenario_id,
                "name": scenario.name,
                "status": "PROCESSING",
                "message": "Scenario creation started. This may take several minutes to complete.",
                "created_at": scenario.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating scenario: {e}")
            await db.rollback()
            raise ValueError(f"Failed to create scenario: {e}")
    
    async def get_scenario(self, scenario_id: str, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Get a scenario by ID with analysis results.
        
        Args:
            scenario_id: The scenario ID
            user_id: ID of the user requesting the scenario
            db: Database session
            
        Returns:
            Scenario details with analysis results
        """
        try:
            # Retrieve scenario from database
            result = await db.execute(select(Scenario).where(
                Scenario.scenario_id == scenario_id,
                Scenario.user_id == user_id
            ))
            scenario = result.scalars().first()
            
            if not scenario:
                raise ValueError(f"Scenario {scenario_id} not found")
            
            # Run simulation analysis if not already completed
            if scenario.status != "COMPLETED":
                analysis_results = await self._analyze_scenario(scenario, db)
                scenario.results = analysis_results
                scenario.status = "COMPLETED"
                scenario.completed_at = datetime.now()
                await db.commit()
            
            return {
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "status": scenario.status,
                "created_at": scenario.created_at.isoformat(),
                "completed_at": scenario.completed_at.isoformat() if scenario.completed_at else None,
                "parameters": scenario.parameters,
                "results": scenario.results
            }
            
        except Exception as e:
            logger.error(f"Error getting scenario: {e}")
            raise ValueError(f"Failed to get scenario: {e}")
    
    async def get_playbook(
        self,
        scenario_id: str,
        playbook_id: str,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get a strategic playbook for a scenario pathway.
        
        Args:
            scenario_id: The scenario ID
            playbook_id: The playbook ID
            user_id: ID of the user requesting the playbook
            db: Database session
            
        Returns:
            Detailed strategic playbook
        """
        try:
            # Get scenario and verify user access
            result = await db.execute(select(Scenario).where(
                Scenario.scenario_id == scenario_id,
                Scenario.user_id == user_id
            ))
            scenario = result.scalars().first()
            
            if not scenario:
                raise ValueError(f"Scenario {scenario_id} not found")
            
            # Get playbook from database
            playbook_result = await db.execute(select(Playbook).where(
                Playbook.playbook_id == playbook_id,
                Playbook.scenario_id == scenario.id
            ))
            playbook = playbook_result.scalars().first()
            
            if not playbook:
                # Generate playbook if it doesn't exist
                playbook = await self._generate_playbook(scenario, playbook_id, db)
            
            return {
                "playbook_id": playbook.playbook_id,
                "name": playbook.name,
                "description": playbook.description,
                "pathway_type": playbook.pathway_type,
                "estimated_success_probability": playbook.estimated_success_probability,
                "estimated_timeframe_months": playbook.estimated_timeframe_months,
                "estimated_resource_cost": playbook.estimated_resource_cost,
                "estimated_roi": playbook.estimated_roi,
                "strategy": playbook.strategy,
                "timeline": playbook.timeline,
                "outcomes": playbook.outcomes
            }
            
        except Exception as e:
            logger.error(f"Error getting playbook: {e}")
            raise ValueError(f"Failed to get playbook: {e}")
    
    async def create_threat_scenario(
        self,
        threat_data: Dict[str, Any],
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create a threat response scenario.
        
        Args:
            threat_data: Threat scenario parameters
            user_id: ID of the user creating the threat scenario
            db: Database session
            
        Returns:
            Created threat scenario with ID and initial status
        """
        try:
            threat_id = f"threat_{uuid.uuid4().hex[:12]}"
            
            # Validate threat data
            validated_data = self._validate_threat_data(threat_data)
            
            # Create threat scenario record in database
            threat_scenario = ThreatScenario(
                threat_id=threat_id,
                user_id=user_id,
                name=validated_data.get("name", "Untitled Threat Scenario"),
                description=validated_data.get("description", ""),
                threat_type=validated_data.get("threat_type", "competitor"),
                parameters=validated_data,
                status="PROCESSING",
                priority=validated_data.get("priority", "medium"),
                severity=validated_data.get("severity", "medium")
            )
            
            db.add(threat_scenario)
            await db.commit()
            await db.refresh(threat_scenario)
            
            return {
                "threat_id": threat_id,
                "name": threat_scenario.name,
                "status": "PROCESSING",
                "message": "Threat scenario creation started. This may take several minutes to complete.",
                "created_at": threat_scenario.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating threat scenario: {e}")
            await db.rollback()
            raise ValueError(f"Failed to create threat scenario: {e}")

    async def list_scenarios(self, user_id: int, db: AsyncSession, limit: int, offset: int) -> Dict[str, Any]:
        """List scenarios for a user."""
        try:
            result = await db.execute(
                select(Scenario)
                .where(Scenario.user_id == user_id)
                .limit(limit)
                .offset(offset)
            )
            scenarios = result.scalars().all()

            total_result = await db.execute(
                select(func.count(Scenario.id)).where(Scenario.user_id == user_id)
            )
            total = total_result.scalar_one()

            return {
                "scenarios": scenarios,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total,
                    "has_more": (offset + len(scenarios)) < total
                }
            }
        except Exception as e:
            logger.error(f"Error listing scenarios: {e}")
            raise ValueError(f"Failed to list scenarios: {e}")

    async def get_threat_scenario(self, scenario_id: str, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get a threat scenario by ID."""
        try:
            result = await db.execute(
                select(ThreatScenario).where(
                    ThreatScenario.threat_id == scenario_id,
                    ThreatScenario.user_id == user_id
                )
            )
            threat_scenario = result.scalars().first()

            if not threat_scenario:
                raise ValueError(f"Threat scenario {scenario_id} not found")

            return threat_scenario
        except Exception as e:
            logger.error(f"Error getting threat scenario: {e}")
            raise ValueError(f"Failed to get threat scenario: {e}")
    
    async def _analyze_scenario(self, scenario: Scenario, db: AsyncSession) -> Dict[str, Any]:
        """Analyze a scenario and generate pathways."""
        parameters = scenario.parameters

        # Extract key parameters
        target_keywords = parameters.get("target_keywords", [])
        market_share_goal = parameters.get("market_share_goal", 10)
        timeframe_months = parameters.get("timeframe_months", 12)
        budget = parameters.get("budget", 50000)

        # Get real-time data
        serp_data = serpapi_service.search(query=" ".join(target_keywords))
        trends_data = await google_trends_service.get_keyword_trends(keywords=target_keywords)

        # Generate strategic pathways based on parameters and real-time data
        pathways = []

        # Content-focused pathway
        if target_keywords and market_share_goal > 0:
            content_pathway = self._generate_content_pathway(
                target_keywords, market_share_goal, timeframe_months, budget, serp_data, trends_data
            )
            pathways.append(content_pathway)

        # Technical authority pathway
        technical_pathway = self._generate_technical_pathway(
            target_keywords, market_share_goal, timeframe_months, budget, serp_data, trends_data
        )
        pathways.append(technical_pathway)

        # Partnership pathway
        partnership_pathway = self._generate_partnership_pathway(
            target_keywords, market_share_goal, timeframe_months, budget, serp_data, trends_data
        )
        pathways.append(partnership_pathway)

        # Create playbooks in database
        for pathway in pathways:
            playbook = Playbook(
                playbook_id=pathway["id"],
                scenario_id=scenario.id,
                name=pathway["name"],
                description=pathway["description"],
                pathway_type=pathway["name"].lower().replace(" ", "_").replace("-", "_"),
                estimated_success_probability=pathway["estimated_success_probability"],
                estimated_timeframe_months=pathway["estimated_timeframe_months"],
                estimated_resource_cost=pathway["estimated_resource_cost"],
                estimated_roi=pathway["estimated_roi"],
                strategy=pathway.get("strategy", {}),
                timeline=pathway.get("timeline", {}),
                outcomes=pathway.get("outcomes", {})
            )
            db.add(playbook)

        await db.commit()

        return {
            "pathways": pathways,
            "analysis_summary": {
                "total_pathways": len(pathways),
                "highest_probability": max(p["estimated_success_probability"] for p in pathways) if pathways else 0,
                "fastest_timeframe": min(p["estimated_timeframe_months"] for p in pathways) if pathways else 0,
                "recommended_pathway": pathways[0]["id"] if pathways else None
            }
        }
    
    def _generate_content_pathway(
        self,
        keywords: List[str],
        market_share_goal: float,
        timeframe_months: int,
        budget: float,
        serp_data: Optional[Dict[str, Any]],
        trends_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a content-focused strategic pathway."""
        # A more realistic calculation would involve analyzing the difficulty of the keywords from serp_data
        # and the search volume from trends_data to estimate the number of content pieces required.
        content_pieces = len(keywords) * 3  # 3 pieces per keyword
        estimated_cost = content_pieces * 500  # $500 per content piece

        # Success probability could be influenced by the competition level from serp_data
        success_probability = min(85, 60 + (market_share_goal * 2))  # Higher goal = higher probability
        
        return {
            "id": f"path_{uuid.uuid4().hex[:8]}",
            "name": "Content-Focused Strategy",
            "description": f"Focus on creating comprehensive content around {', '.join(keywords[:3])} topics",
            "estimated_success_probability": success_probability,
            "estimated_timeframe_months": max(6, timeframe_months - 2),
            "estimated_resource_cost": "Medium" if estimated_cost < budget else "High",
            "estimated_roi": round((market_share_goal * 1000) / estimated_cost * 100, 1),
            "content_requirements": {
                "pillar_content": content_pieces // 2,
                "supporting_content": content_pieces // 2,
                "estimated_cost": estimated_cost
            }
        }
    
    def _generate_technical_pathway(
        self,
        keywords: List[str],
        market_share_goal: float,
        timeframe_months: int,
        budget: float
    ) -> Dict[str, Any]:
        """Generate a technical authority strategic pathway."""
        estimated_cost = 75000  # Higher cost for technical authority
        success_probability = min(75, 50 + (market_share_goal * 1.5))
        
        return {
            "id": f"path_{uuid.uuid4().hex[:8]}",
            "name": "Technical Authority Strategy",
            "description": "Establish technical authority through research papers and speaking engagements",
            "estimated_success_probability": success_probability,
            "estimated_timeframe_months": timeframe_months,
            "estimated_resource_cost": "High",
            "estimated_roi": round((market_share_goal * 800) / estimated_cost * 100, 1),
            "technical_requirements": {
                "research_papers": 3,
                "speaking_engagements": 5,
                "estimated_cost": estimated_cost
            }
        }
    
    def _generate_partnership_pathway(
        self,
        keywords: List[str],
        market_share_goal: float,
        timeframe_months: int,
        budget: float,
        serp_data: Optional[Dict[str, Any]],
        trends_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a partnership-driven strategic pathway."""
        # Partnership success depends on finding the right partners.
        # A more advanced implementation would analyze the ecosystem of the target keywords to identify potential partners.
        estimated_cost = 40000
        success_probability = min(70, 45 + (market_share_goal * 1.8))
        
        return {
            "id": f"path_{uuid.uuid4().hex[:8]}",
            "name": "Partnership-Driven Strategy",
            "description": "Partner with complementary technology providers for co-marketing",
            "estimated_success_probability": success_probability,
            "estimated_timeframe_months": max(6, timeframe_months - 4),
            "estimated_resource_cost": "Medium",
            "estimated_roi": round((market_share_goal * 900) / estimated_cost * 100, 1),
            "partnership_requirements": {
                "partners_needed": 3,
                "co_marketing_campaigns": 2,
                "estimated_cost": estimated_cost
            }
        }
    
    async def _generate_playbook(self, scenario: Scenario, playbook_id: str, db: AsyncSession) -> Playbook:
        """Generate a strategic playbook for a scenario pathway."""
        # Find the pathway that corresponds to the playbook_id
        pathway = next((p for p in scenario.results.get("pathways", []) if p["id"] == playbook_id), None)

        if not pathway:
            raise ValueError(f"Pathway {playbook_id} not found in scenario {scenario.scenario_id}")

        # Generate playbook based on the pathway
        playbook = Playbook(
            playbook_id=playbook_id,
            scenario_id=scenario.id,
            name=pathway["name"],
            description=pathway["description"],
            pathway_type=pathway["name"].lower().replace(" ", "_").replace("-", "_"),
            estimated_success_probability=pathway["estimated_success_probability"],
            estimated_timeframe_months=pathway["estimated_timeframe_months"],
            estimated_resource_cost=pathway["estimated_resource_cost"],
            estimated_roi=pathway["estimated_roi"],
            strategy=self._generate_strategy(pathway, scenario.parameters),
            timeline=self._generate_timeline(pathway["estimated_timeframe_months"]),
            outcomes=self._generate_outcomes(scenario.parameters)
        )

        db.add(playbook)
        await db.commit()
        await db.refresh(playbook)

        return playbook

    def _generate_strategy(self, pathway: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a strategy for the playbook based on the pathway type."""
        pathway_type = pathway["name"].lower().replace(" ", "_").replace("-", "_")

        if pathway_type == "content_focused_strategy":
            return self._generate_content_strategy(parameters)
        elif pathway_type == "technical_authority_strategy":
            return self._generate_technical_strategy(parameters)
        elif pathway_type == "partnership_driven_strategy":
            return self._generate_pr_strategy(parameters)
        else:
            return {}
    
    def _generate_content_strategy(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content strategy for the playbook."""
        keywords = parameters.get("target_keywords", [])
        
        return {
            "pillar_content": [
                {
                    "topic": f"{keywords[0].title()} Guide" if keywords else "Main Topic Guide",
                    "target_keywords": keywords[:2] if keywords else [],
                    "estimated_word_count": 5000,
                    "estimated_impact": "High",
                }
            ],
            "supporting_content": [
                {
                    "topic": f"{keywords[0].title()} Checklist" if keywords else "Topic Checklist",
                    "target_keywords": keywords[1:3] if len(keywords) > 1 else [],
                    "estimated_word_count": 1500,
                    "estimated_impact": "Medium",
                }
            ]
        }
    
    def _generate_technical_strategy(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical strategy for the playbook."""
        return {
            "site_structure": {
                "new_sections": [
                    {
                        "path": "/resources/guides",
                        "purpose": "Host comprehensive content",
                    }
                ],
                "internal_linking": [
                    {
                        "from": "/solutions",
                        "to": "/resources/guides",
                        "anchor_text": "comprehensive guide",
                    }
                ]
            },
            "schema_markup": [
                {
                    "type": "FAQPage",
                    "target_pages": ["/resources/guides"],
                }
            ]
        }
    
    def _generate_pr_strategy(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PR strategy for the playbook."""
        return {
            "target_publications": [
                {
                    "name": "Industry Publication",
                    "estimated_impact": "High",
                    "estimated_cost": 5000
                }
            ],
            "speaking_opportunities": [
                {
                    "event": "Industry Conference",
                    "estimated_impact": "Medium",
                    "estimated_cost": 3000
                }
            ]
        }
    
    def _generate_timeline(self, months: int) -> Dict[str, Any]:
        """Generate timeline for the playbook."""
        return {
            "months_1_3": [
                "Create and publish main pillar content",
                "Implement schema markup",
                "Begin outreach to top publications",
            ],
            "months_4_6": [
                "Create and publish supporting content",
                "Implement internal linking strategy",
                "Secure guest posting opportunities",
            ],
            "months_7_12": [
                "Update and expand content based on performance",
                "Create additional supporting content",
                "Secure speaking engagement at industry conference",
            ]
        }
    
    def _generate_outcomes(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate estimated outcomes for the playbook."""
        market_share_goal = parameters.get("market_share_goal", 10)
        
        return {
            "traffic_increase": f"+{market_share_goal * 15}%",
            "keyword_rankings": {
                "top_3": max(1, market_share_goal // 4),
                "top_10": max(3, market_share_goal // 2),
                "top_20": max(5, market_share_goal),
            },
            "leads_increase": f"+{market_share_goal * 12}%",
            "revenue_increase": f"+{market_share_goal * 9.5}%",
        }
    
    def _validate_scenario_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean scenario data."""
        required_fields = ["name", "target_keywords"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults for optional fields
        data.setdefault("market_share_goal", 10)
        data.setdefault("timeframe_months", 12)
        data.setdefault("budget", 50000)
        data.setdefault("description", "")
        
        return data
    
    def _validate_threat_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean threat data."""
        required_fields = ["name", "threat_type"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults for optional fields
        data.setdefault("severity", "medium")
        data.setdefault("timeframe_months", 6)
        data.setdefault("description", "")
        
        return data

    async def get_user_scenarios(
        self,
        user_id: int,
        limit: int = 50,
        scenario_type: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Get all scenarios for a user with optional filtering.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of scenarios to return
            scenario_type: Optional filter by scenario type
            db: Database session
            
        Returns:
            List of scenario data dictionaries
        """
        try:
            # Build query
            query = select(Scenario).where(Scenario.user_id == user_id)
            
            if scenario_type:
                query = query.where(Scenario.scenario_type == scenario_type)
            
            query = query.order_by(Scenario.created_at.desc()).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            scenarios = result.scalars().all()
            
            # Convert to response format
            scenario_list = []
            for scenario in scenarios:
                scenario_data = {
                    "scenario_id": scenario.scenario_id,
                    "scenario_name": scenario.name,
                    "scenario_type": scenario.scenario_type,
                    "status": "completed",  # All scenarios are completed once created
                    "results": scenario.results or {},
                    "confidence_intervals": scenario.results.get("confidence_intervals", {}) if scenario.results else {},
                    "recommendations": scenario.results.get("recommendations", []) if scenario.results else [],
                    "risk_assessment": scenario.results.get("risk_assessment", {}) if scenario.results else {},
                    "created_at": scenario.created_at.isoformat()
                }
                scenario_list.append(scenario_data)
            
            return scenario_list
            
        except Exception as e:
            logger.error(f"Error getting user scenarios: {e}")
            return []

    async def run_comprehensive_simulation(
        self,
        scenario_data: Any,
        scenario_id: str,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Run comprehensive simulation for a scenario.
        
        Args:
            scenario_data: Scenario parameters
            scenario_id: Unique scenario identifier
            user_id: User ID
            db: Database session
            
        Returns:
            Simulation results
        """
        try:
            # Create scenario record
            scenario = Scenario(
                scenario_id=scenario_id,
                user_id=user_id,
                name=scenario_data.scenario_name,
                scenario_type=scenario_data.scenario_type,
                parameters={
                    "base_metrics": scenario_data.base_metrics,
                    "changes": scenario_data.changes,
                    "time_horizon": scenario_data.time_horizon,
                    "confidence_level": scenario_data.confidence_level,
                    "include_competitors": scenario_data.include_competitors,
                    "market_conditions": scenario_data.market_conditions
                },
                results={}
            )
            
            db.add(scenario)
            await db.flush()  # Get the ID without committing
            
            # Run simulation based on scenario type
            if scenario_data.scenario_type == "whatif":
                simulation_results = await self._run_whatif_simulation(scenario_data)
            elif scenario_data.scenario_type == "competitor":
                simulation_results = await self._run_competitor_simulation(scenario_data)
            elif scenario_data.scenario_type == "market_change":
                simulation_results = await self._run_market_change_simulation(scenario_data)
            elif scenario_data.scenario_type == "algorithm_update":
                simulation_results = await self._run_algorithm_update_simulation(scenario_data)
            else:
                simulation_results = await self._run_default_simulation(scenario_data)
            
            # Update scenario with results
            scenario.results = simulation_results
            await db.commit()
            
            return simulation_results
            
        except Exception as e:
            logger.error(f"Error running comprehensive simulation: {e}")
            await db.rollback()
            return {"error": str(e)}
    
    async def _run_whatif_simulation(self, scenario_data: Any) -> Dict[str, Any]:
        """Run what-if scenario simulation."""
        # Simulate the impact of changes on base metrics
        results = {}
        
        for metric, change in scenario_data.changes.items():
            if metric in scenario_data.base_metrics:
                base_value = scenario_data.base_metrics[metric]
                # Apply percentage change
                if isinstance(change, (int, float)):
                    new_value = base_value * (1 + change / 100)
                    results[metric] = {
                        "current": base_value,
                        "projected": new_value,
                        "change_percent": change,
                        "absolute_change": new_value - base_value
                    }
        
        return {
            "simulation_type": "whatif",
            "projected_metrics": results,
            "confidence_intervals": {
                metric: {
                    "low": data["projected"] * 0.85,
                    "high": data["projected"] * 1.15
                }
                for metric, data in results.items()
            },
            "timeline_months": scenario_data.time_horizon
        }
    
    async def _run_default_simulation(self, scenario_data: Any) -> Dict[str, Any]:
        """Run default simulation for unknown scenario types."""
        return {
            "simulation_type": "default",
            "message": "Basic simulation completed",
            "confidence_intervals": {},
            "projected_metrics": scenario_data.base_metrics
        }

    async def generate_scenario_recommendations(
        self,
        results: Dict[str, Any],
        scenario_type: str,
        market_conditions: str
    ) -> List[str]:
        """Generate strategic recommendations based on simulation results."""
        recommendations = []
        
        if scenario_type == "whatif":
            recommendations.extend([
                "Monitor key performance indicators closely during implementation",
                "Set up A/B testing to validate assumptions",
                "Prepare contingency plans for different outcomes"
            ])
        
        if market_conditions == "volatile":
            recommendations.append("Consider shorter planning cycles due to market volatility")
        elif market_conditions == "growth":
            recommendations.append("Leverage growth conditions for accelerated expansion")
        
        return recommendations
    
    async def assess_scenario_risks(
        self,
        scenario_data: Any,
        simulation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risks for the scenario."""
        risk_level = "medium"
        
        # Determine risk level based on confidence and changes
        if scenario_data.confidence_level < 0.6:
            risk_level = "high"
        elif scenario_data.confidence_level > 0.8:
            risk_level = "low"
        
        return {
            "overall_risk": risk_level,
            "risk_factors": [
                "Market conditions may change unexpectedly",
                "Competitor responses not fully predictable",
                "Implementation challenges may arise"
            ],
            "mitigation_strategies": [
                "Regular monitoring and adjustment",
                "Phased implementation approach",
                "Stakeholder communication plan"
            ]
        }


# Create a singleton instance
market_simulation_service = MarketSimulationService() 