"""Organizations, members and invitations API (``/api/v1/orgs``, ``/api/v1/invitations``)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update

from serptank.core.audit import record_audit_event
from serptank.core.errors import NotFoundError, PermissionDeniedError
from serptank.core.models import AIEngine, SearchEngine
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.billing.entitlements import plan_for
from serptank.modules.identity.deps import CurrentUser, DbSession, Identity, RecentlyReauthenticated
from serptank.modules.identity.models import User
from serptank.modules.tenancy import service
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.models import Invitation, Membership, Organization
from serptank.modules.tenancy.policies import Permission
from serptank.modules.tenancy.schemas import (
    InvitationAccept,
    InvitationCreate,
    InvitationOut,
    MemberOut,
    MemberUpdate,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    OrganizationWithRole,
)

router = APIRouter(tags=["organizations"])

OrgRead = Annotated[OrgContext, Depends(org_access(Permission.ORG_READ))]
OrgUpdate = Annotated[OrgContext, Depends(org_access(Permission.ORG_UPDATE))]
OrgDelete = Annotated[OrgContext, Depends(org_access(Permission.ORG_DELETE))]
MembersRead = Annotated[OrgContext, Depends(org_access(Permission.MEMBERS_READ))]
MembersManage = Annotated[OrgContext, Depends(org_access(Permission.MEMBERS_MANAGE))]

_INVITE_RATE = rate_limit("invite", Rate(20, 3600))


@router.post("/orgs", response_model=OrganizationOut, status_code=201)
async def create_org(body: OrganizationCreate, auth: CurrentUser, db: DbSession) -> Organization:
    return await service.create_organization(db, auth.user, body.name)


@router.get("/orgs", response_model=list[OrganizationWithRole])
async def list_orgs(auth: CurrentUser, db: DbSession) -> list[OrganizationWithRole]:
    rows = await db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == auth.user.id, Organization.deleted_at.is_(None))
        .order_by(Organization.name)
    )
    return [
        OrganizationWithRole(**OrganizationOut.model_validate(org).model_dump(), role=role)
        for org, role in rows
    ]


@router.get("/orgs/{org_id}", response_model=OrganizationWithRole)
async def get_org(ctx: OrgRead) -> OrganizationWithRole:
    out = OrganizationOut.model_validate(ctx.organization).model_dump()
    return OrganizationWithRole(**out, role=ctx.role or "viewer")  # type: ignore[arg-type]


@router.patch("/orgs/{org_id}", response_model=OrganizationOut)
async def update_org(body: OrganizationUpdate, ctx: OrgUpdate, db: DbSession) -> Organization:
    org = ctx.organization
    changes: dict[str, object] = {}
    if body.name is not None:
        org.name = body.name
        changes["name"] = body.name
    if body.require_mfa is not None:
        if body.require_mfa and ctx.user is not None and not ctx.user.mfa_enabled:
            raise PermissionDeniedError(
                "Enable two-factor authentication on your own account first."
            )
        org.require_mfa = body.require_mfa
        changes["require_mfa"] = body.require_mfa
    record_audit_event(
        db, "org.updated", actor_user_id=ctx.actor_user_id, organization_id=org.id, details=changes
    )
    await db.commit()
    return org


@router.delete("/orgs/{org_id}", status_code=204)
async def delete_org(ctx: OrgDelete, auth: RecentlyReauthenticated, db: DbSession) -> None:
    """Soft delete; data is purged after a 30-day grace period (Module 13 retention job)."""
    ctx.organization.deleted_at = datetime.now(UTC)
    record_audit_event(
        db, "org.deleted", actor_user_id=auth.user.id, organization_id=ctx.organization_id
    )
    await db.commit()


# ------------------------------------------------------------------------ members
@router.get("/orgs/{org_id}/members", response_model=list[MemberOut])
async def list_members(ctx: MembersRead, db: DbSession) -> list[MemberOut]:
    rows = await db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == ctx.organization_id)
        .order_by(Membership.created_at)
    )
    return [
        MemberOut(
            id=m.id,
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=m.role,
            mfa_enabled=u.mfa_enabled,
            joined_at=m.created_at,
        )
        for m, u in rows
    ]


@router.patch("/orgs/{org_id}/members/{membership_id}", status_code=204)
async def update_member(
    membership_id: uuid.UUID,
    body: MemberUpdate,
    ctx: MembersManage,
    _auth: RecentlyReauthenticated,
    db: DbSession,
) -> None:
    # Role changes are privilege changes: they require a recent step-up (plan §5.1).
    await service.change_role(db, ctx, membership_id, body.role)


@router.delete("/orgs/{org_id}/members/{membership_id}", status_code=204)
async def remove_member(membership_id: uuid.UUID, ctx: OrgRead, db: DbSession) -> None:
    # Any member may remove themselves; removing others is checked in the service.
    await service.remove_member(db, ctx, membership_id)


# -------------------------------------------------------------------- invitations
@router.get("/orgs/{org_id}/invitations", response_model=list[InvitationOut])
async def list_invitations(ctx: MembersRead, db: DbSession) -> list[Invitation]:
    rows = await db.execute(
        select(Invitation)
        .where(
            Invitation.organization_id == ctx.organization_id,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .order_by(Invitation.created_at.desc())
    )
    return list(rows.scalars())


@router.post(
    "/orgs/{org_id}/invitations",
    response_model=InvitationOut,
    status_code=201,
    dependencies=[Depends(_INVITE_RATE)],
)
async def create_invitation(
    body: InvitationCreate, ctx: MembersManage, db: DbSession, identity: Identity
) -> Invitation:
    return await service.invite(
        db,
        ctx,
        str(body.email),
        body.role,
        pepper=identity.settings.api_key_pepper.get_secret_value(),
        sender=identity.email,
        public_origin=identity.settings.public_origin,
    )


@router.delete("/orgs/{org_id}/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(invitation_id: uuid.UUID, ctx: MembersManage, db: DbSession) -> None:
    result = await db.execute(
        update(Invitation)
        .where(
            Invitation.id == invitation_id,
            Invitation.organization_id == ctx.organization_id,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
        .returning(Invitation.id)
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("Invitation not found.")
    record_audit_event(
        db,
        "invitation.revoked",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_id=invitation_id,
    )
    await db.commit()


@router.post("/invitations/accept", response_model=OrganizationOut)
async def accept_invitation(
    body: InvitationAccept, auth: CurrentUser, db: DbSession, identity: Identity
) -> Organization:
    org_id = await service.accept_invitation(
        db, auth.user, body.token, identity.settings.api_key_pepper.get_secret_value()
    )
    org = await db.get(Organization, org_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    return org


class EntitlementsOut(BaseModel):
    plan_code: str
    plan_name: str
    search_engines: list[SearchEngine]
    ai_engines: list[AIEngine]
    max_projects: int
    max_markets_per_project: int
    max_members: int
    max_tracked_keywords: int
    max_crawl_pages_per_month: int
    ai_prompts_per_month: int
    rank_check_interval_hours: int


@router.get("/orgs/{org_id}/entitlements", response_model=EntitlementsOut)
async def get_entitlements(ctx: OrgRead) -> EntitlementsOut:
    """What the organization's plan includes (the UI uses this for upgrade prompts)."""
    plan = plan_for(ctx.organization.plan_code)
    return EntitlementsOut(
        plan_code=plan.code,
        plan_name=plan.name,
        search_engines=sorted(plan.search_engines, key=lambda e: e.value),
        ai_engines=sorted(plan.ai_engines, key=lambda e: e.value),
        max_projects=plan.max_projects,
        max_markets_per_project=plan.max_markets_per_project,
        max_members=plan.max_members,
        max_tracked_keywords=plan.max_tracked_keywords,
        max_crawl_pages_per_month=plan.max_crawl_pages_per_month,
        ai_prompts_per_month=plan.ai_prompts_per_month,
        rank_check_interval_hours=plan.rank_check_interval_hours,
    )
