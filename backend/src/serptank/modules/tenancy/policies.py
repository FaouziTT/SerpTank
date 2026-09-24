"""Role-based access control: the single source of truth for who may do what.

Every organization-scoped route declares the :class:`Permission` it needs; the
``org_access`` dependency (``tenancy.deps``) resolves the caller's role and checks it
here. Tests generate the authorization matrix from :data:`ROLE_PERMISSIONS`.
"""

from __future__ import annotations

from enum import StrEnum

from serptank.core.models import MemberRole


class Permission(StrEnum):
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"
    MEMBERS_READ = "members:read"
    MEMBERS_MANAGE = "members:manage"
    BILLING_MANAGE = "billing:manage"
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    API_KEYS_MANAGE = "api_keys:manage"
    AUDIT_READ = "audit:read"
    INTEGRATIONS_MANAGE = "integrations:manage"


_READ = {Permission.ORG_READ, Permission.MEMBERS_READ, Permission.PROJECT_READ}

ROLE_PERMISSIONS: dict[MemberRole, frozenset[Permission]] = {
    MemberRole.OWNER: frozenset(Permission),
    MemberRole.ADMIN: frozenset(set(Permission) - {Permission.ORG_DELETE}),
    MemberRole.EDITOR: frozenset(_READ | {Permission.PROJECT_WRITE}),
    MemberRole.VIEWER: frozenset(_READ),
    MemberRole.BILLING: frozenset({Permission.ORG_READ, Permission.BILLING_MANAGE}),
}

# Which permissions an API key may exercise, by scope. Anything absent (members,
# billing, key management, org deletion, audit, integrations) requires a human session.
API_SCOPE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "read": frozenset({Permission.ORG_READ, Permission.PROJECT_READ}),
    "write": frozenset({Permission.ORG_READ, Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
}


def role_allows(role: MemberRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]


def scopes_allow(scopes: frozenset[str], permission: Permission) -> bool:
    return any(permission in API_SCOPE_PERMISSIONS.get(scope, frozenset()) for scope in scopes)


def can_assign_role(actor: MemberRole, target: MemberRole) -> bool:
    """Only owners can grant or revoke ownership; admins manage everyone else."""
    if target is MemberRole.OWNER:
        return actor is MemberRole.OWNER
    return actor in {MemberRole.OWNER, MemberRole.ADMIN}
