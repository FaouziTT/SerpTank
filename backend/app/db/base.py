"""
Base module for SQLAlchemy models.

This module imports all models to make them available for Alembic migrations.
"""
from app.db.base_class import Base

# Import models in dependency order to avoid circular imports and forward reference issues

# Core models first (no dependencies)
from app.models.user import User

# Models that depend on User
from app.models.domain import Domain
from app.models.subscription import SubscriptionPlan, Subscription, UsageRecord, BillingEvent
from app.models.crawl import Site, Crawl, CrawlUrl, CrawlAnalysis
from app.models.organization import Organization, OrganizationMember, OrganizationInvitation, OrganizationDomain, OrganizationAuditLog

# Settings models that depend on User
from app.models.settings import TeamMember, Integration, NotificationSetting, UsageStatistics, ApiKey

# Add missing models for relationship registration
from app.models.activity import Activity
from app.models.scenario import Scenario, ThreatScenario

# Ensure all models are in __all__ for explicit exports
__all__ = [
    "Base",
    "User",
    "Domain", 
    "SubscriptionPlan", "Subscription", "UsageRecord", "BillingEvent",
    "Site", "Crawl", "CrawlUrl", "CrawlAnalysis",
    "Organization", "OrganizationMember", "OrganizationInvitation", "OrganizationDomain", "OrganizationAuditLog",
    "TeamMember", "Integration", "NotificationSetting", "UsageStatistics", "ApiKey",
    "Activity", "Scenario", "ThreatScenario"
]