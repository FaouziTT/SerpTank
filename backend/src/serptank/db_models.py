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
from serptank.modules.jobs.models import Job
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.tenancy.models import Invitation, Membership, Organization

__all__ = [
    "ApiKey",
    "AuditEvent",
    "AuditIssue",
    "Base",
    "Crawl",
    "CrawlLink",
    "CrawlPage",
    "EmailToken",
    "Invitation",
    "Job",
    "Membership",
    "MfaTotp",
    "Organization",
    "Project",
    "ProjectMarket",
    "RecoveryCode",
    "User",
    "WebAuthnCredential",
]
