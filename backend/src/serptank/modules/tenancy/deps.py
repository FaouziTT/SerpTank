"""Organization-scoped access control dependency.

``org_access(Permission.X)`` resolves the caller (session or API key) for the
``{org_id}`` path parameter and enforces, in order:

1. The caller belongs to the organization - otherwise **404** (existence is not revealed).
2. The organization is not deleted and, if it requires MFA, the user has MFA enabled.
3. The caller's role (or API-key scopes) grants the permission - otherwise 403.

On success the tenant is bound to the database session, so RLS confines every
subsequent query to this organization.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.db import bind_identity, get_session
from serptank.core.errors import (
    AppError,
    AuthenticationRequiredError,
    NotFoundError,
    PermissionDeniedError,
)
from serptank.core.models import MemberRole
from serptank.modules.identity.deps import Principal, principal, record_api_key_use
from serptank.modules.identity.models import User
from serptank.modules.tenancy.models import Membership, Organization
from serptank.modules.tenancy.policies import Permission, role_allows, scopes_allow

_NOT_FOUND = "Organization not found."


class MfaRequiredError(AppError):
    status = 403
    code = "mfa_required"
    title = "This organization requires two-factor authentication"


@dataclass(frozen=True)
class OrgContext:
    organization: Organization
    role: MemberRole | None  # None for API keys
    user: User | None
    api_key_id: uuid.UUID | None

    @property
    def organization_id(self) -> uuid.UUID:
        return self.organization.id

    @property
    def actor_user_id(self) -> uuid.UUID | None:
        return self.user.id if self.user else None


def org_access(permission: Permission) -> Callable[..., Awaitable[OrgContext]]:
    async def dependency(
        org_id: Annotated[uuid.UUID, Path()],
        who: Annotated[Principal, Depends(principal)],
        db: Annotated[AsyncSession, Depends(get_session)],
    ) -> OrgContext:
        if who.api_key is not None:
            if who.api_key.organization_id != org_id:
                raise NotFoundError(_NOT_FOUND)
            await bind_identity(db, organization_id=org_id)
            org = await db.get(Organization, org_id)
            if org is None or org.deleted_at is not None:
                raise NotFoundError(_NOT_FOUND)
            if not scopes_allow(who.api_key.scopes, permission):
                raise PermissionDeniedError("This API key is not allowed to perform this action.")
            await record_api_key_use(db, who.api_key)
            return OrgContext(org, None, None, who.api_key.key_id)

        if who.user is None:  # principal() always sets one of the two
            raise AuthenticationRequiredError
        user = who.user.user
        membership = (
            await db.execute(
                select(Membership).where(
                    Membership.organization_id == org_id, Membership.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if membership is None:
            raise NotFoundError(_NOT_FOUND)
        await bind_identity(db, organization_id=org_id)
        org = await db.get(Organization, org_id)
        if org is None or org.deleted_at is not None:
            raise NotFoundError(_NOT_FOUND)
        if org.require_mfa and not user.mfa_enabled:
            raise MfaRequiredError("Enable two-factor authentication to access this organization.")
        if not role_allows(membership.role, permission):
            raise PermissionDeniedError("Your role does not allow this action.")
        return OrgContext(org, membership.role, user, None)

    return dependency
