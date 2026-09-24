"""Import every ORM model so ``Base.metadata`` is complete (Alembic, tests).

This registry lives outside ``serptank.core`` because it imports feature modules.
"""

from serptank.core.audit import AuditEvent
from serptank.core.models import Base
from serptank.modules.identity.models import (
    ApiKey,
    EmailToken,
    MfaTotp,
    RecoveryCode,
    User,
    WebAuthnCredential,
)
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.tenancy.models import Membership, Organization

__all__ = [
    "ApiKey",
    "AuditEvent",
    "Base",
    "EmailToken",
    "Membership",
    "MfaTotp",
    "Organization",
    "Project",
    "ProjectMarket",
    "RecoveryCode",
    "User",
    "WebAuthnCredential",
]
