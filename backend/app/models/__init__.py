"""
Models Package

This file exposes all SQLAlchemy ORM models from a single, convenient import point.
It uses explicit imports to avoid namespace pollution and improve clarity.
"""

from .activity import Activity
from .activity_feed import ActivityFeed, ActivitySummary
from .audit_log import AuditLog
from .background_task import BackgroundTask, TaskType, TaskStatus
from .content import ContentBrief, ContentEnhancement
from .crawl import Crawl, CrawlUrl, CrawlAnalysis, Site
from .domain import Domain
from .file import File, FileCategory, FileStatus, StorageBackend
from .knowledge import ( 
    CapturedKnowledge,
    CompetitiveIntelligence,
    PersonalizedRecommendation,
    StrategicLedger,
    TuningInsight,
)
from .notification import Notification, NotificationType, NotificationCategory
from .organization import (
    Organization,
    OrganizationAuditLog,
    OrganizationDomain,
    OrganizationInvitation,
    OrganizationMember,
    MemberRole,
    MemberStatus,
    OrganizationStatus,
)
from .performance import PerformanceMetric, PerformanceBenchmark, PerformanceAlert
from .project import Project
from .project_team_member import ProjectTeamMember
from .scenario import Scenario, Playbook, ThreatScenario
from .serp_cache import SERPAnalysis, CompetitorTracking, SERPFeatureTracking
from .settings import (
    ApiKey,
    Integration,
    NotificationSetting,
    TeamMember,
    UsageStatistics,
)
from .sge import SGEAnalysis, SGEMonitor
from .subscription import Subscription, BillingEvent # Assuming these models exist
from .user import User
from .password_reset import PasswordResetToken
from .social_media_credential import SocialMediaCredential
from .webhook import Webhook
from .domain_verification import DomainVerification

# __all__ defines the public API for this package.
# When a user does `from app.models import *`, only these names will be imported.
__all__ = [
    "Activity",
    "ActivityFeed",
    "ActivitySummary",
    "ApiKey",
    "AuditLog",
    "BackgroundTask",
    "BillingEvent",
    "CapturedKnowledge",
    "CompetitiveIntelligence",
    "CompetitorTracking",
    "ContentBrief",
    "ContentEnhancement",
    "Crawl",
    "CrawlAnalysis",
    "CrawlUrl",
    "Domain",
    "DomainVerification",
    "File",
    "FileCategory",
    "FileStatus",
    "Integration",
    "MemberRole",
    "MemberStatus",
    "Notification",
    "NotificationCategory",
    "NotificationSetting",
    "NotificationType",
    "Organization",
    "OrganizationAuditLog",
    "OrganizationDomain",
    "OrganizationInvitation",
    "OrganizationMember",
    "OrganizationStatus",
    "PasswordResetToken",
    "PerformanceAlert",
    "PerformanceBenchmark",
    "PerformanceMetric",
    "PersonalizedRecommendation",
    "Playbook",
    "Project",
    "ProjectTeamMember",
    "Scenario",
    "SERPAnalysis",
    "SERPFeatureTracking",
    "SGEAnalysis",
    "SGEMonitor",
    "Site",
    "SocialMediaCredential",
    "StorageBackend",
    "StrategicLedger",
    "Subscription",
    "TaskStatus",
    "TaskType",
    "TeamMember",
    "ThreatScenario",
    "TuningInsight",
    "UsageStatistics",
    "User",
    "Webhook",
]