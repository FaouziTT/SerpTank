"""Import every ORM model so ``Base.metadata`` is complete (Alembic, tests).

This registry lives outside ``serptank.core`` because it imports feature modules.
"""

from serptank.core.audit import AuditEvent
from serptank.core.models import Base
from serptank.modules.audit.models import AuditIssue
from serptank.modules.crawler.models import Crawl, CrawlLink, CrawlPage
from serptank.modules.identity.models import (
    ApiKey,
    EmailToken,
    MfaTotp,
    RecoveryCode,
    User,
    WebAuthnCredential,
)
from serptank.modules.integrations.models import (
    AiPerformanceDaily,
    BingDaily,
    Connection,
    Ga4Daily,
    GscDaily,
    IndexNowSubmission,
    ProjectSource,
    UrlInspection,
    VitalsDaily,
)
from serptank.modules.jobs.models import Job
from serptank.modules.llm.models import LlmUsage
from serptank.modules.onpage.models import ContentBrief, PageOptimization
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.search_data.models import (
    Competitor,
    KeywordMetrics,
    RankObservation,
    SerpSnapshot,
    SerpUsage,
    SerpValidation,
    TrackedKeyword,
    VendorUsage,
)
from serptank.modules.tenancy.models import Invitation, Membership, Organization

__all__ = [
    "AiPerformanceDaily",
    "ApiKey",
    "AuditEvent",
    "AuditIssue",
    "Base",
    "BingDaily",
    "Competitor",
    "Connection",
    "ContentBrief",
    "Crawl",
    "CrawlLink",
    "CrawlPage",
    "EmailToken",
    "Ga4Daily",
    "GscDaily",
    "IndexNowSubmission",
    "Invitation",
    "Job",
    "KeywordMetrics",
    "LlmUsage",
    "Membership",
    "MfaTotp",
    "Organization",
    "PageOptimization",
    "Project",
    "ProjectMarket",
    "ProjectSource",
    "RankObservation",
    "RecoveryCode",
    "SerpSnapshot",
    "SerpUsage",
    "SerpValidation",
    "TrackedKeyword",
    "UrlInspection",
    "User",
    "VendorUsage",
    "VitalsDaily",
    "WebAuthnCredential",
]
