"""Organization, membership and invitation use cases.

Invariants:
* Every organization always has at least one owner (last-owner guard on role changes,
  removals and leaving).
* Only owners can grant or revoke ownership (``policies.can_assign_role``).
* Invitations are bound to an email address: only a signed-in user with that verified
  email can accept, exactly once, before expiry.
"""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.audit import record_audit_event
from serptank.core.crypto import generate_token, hash_token
from serptank.core.db import bind_identity
from serptank.core.email import EmailSender, OutgoingEmail
from serptank.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from serptank.core.models import MemberRole, uuid7
from serptank.modules.billing.entitlements import plan_for, require_below_limit
from serptank.modules.identity.models import User
from serptank.modules.tenancy.deps import OrgContext
from serptank.modules.tenancy.models import Invitation, Membership, Organization
from serptank.modules.tenancy.policies import can_assign_role

INVITATION_TTL = timedelta(days=7)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class EmailVerificationRequiredError(AppError):
    status = 403
    code = "email_verification_required"
    title = "Verify your email address first"


class LastOwnerError(ConflictError):
    code = "last_owner"
    title = "An organization needs at least one owner"


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.lower()).strip("-")[:40]
    return slug or "org"


async def create_organization(db: AsyncSession, user: User, name: str) -> Organization:
    if user.email_verified_at is None:
        raise EmailVerificationRequiredError(
            "Verify your email address before creating an organization."
        )
    # Bind the new tenant *before* inserting: PostgreSQL applies the SELECT policy to
    # INSERT ... RETURNING, and a brand-new organization has no members yet.
    org = Organization(
        id=uuid7(),
        name=name.strip(),
        slug=f"{_slugify(name)}-{secrets.token_hex(3)}",
        created_by_user_id=user.id,
    )
    await bind_identity(db, organization_id=org.id)
    db.add(org)
    await db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role=MemberRole.OWNER))
    record_audit_event(
        db,
        "org.created",
        actor_user_id=user.id,
        organization_id=org.id,
        target_type="org",
        target_id=org.id,
    )
    await db.commit()
    return org


async def _owner_count(db: AsyncSession, org_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).where(
            Membership.organization_id == org_id, Membership.role == MemberRole.OWNER
        )
    )
    return int(result.scalar_one())


async def _membership(db: AsyncSession, ctx: OrgContext, membership_id: uuid.UUID) -> Membership:
    member = await db.get(Membership, membership_id)
    if member is None or member.organization_id != ctx.organization_id:
        raise NotFoundError("Member not found.")
    return member


async def change_role(
    db: AsyncSession, ctx: OrgContext, membership_id: uuid.UUID, new_role: MemberRole
) -> Membership:
    actor_role = ctx.role or MemberRole.VIEWER
    member = await _membership(db, ctx, membership_id)
    if not can_assign_role(actor_role, new_role) or not can_assign_role(actor_role, member.role):
        raise PermissionDeniedError("Only owners can grant or revoke the owner role.")
    demoting_owner = member.role is MemberRole.OWNER and new_role is not MemberRole.OWNER
    if demoting_owner and await _owner_count(db, ctx.organization_id) <= 1:
        raise LastOwnerError("Assign another owner before changing this role.")
    old = member.role
    member.role = new_role
    record_audit_event(
        db,
        "member.role_changed",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="membership",
        target_id=member.id,
        details={"from": old.value, "to": new_role.value},
    )
    await db.commit()
    return member


async def remove_member(db: AsyncSession, ctx: OrgContext, membership_id: uuid.UUID) -> None:
    member = await _membership(db, ctx, membership_id)
    is_self = ctx.user is not None and member.user_id == ctx.user.id
    actor_role = ctx.role or MemberRole.VIEWER
    if not is_self and not can_assign_role(actor_role, member.role):
        raise PermissionDeniedError("You cannot remove this member.")
    if member.role is MemberRole.OWNER and await _owner_count(db, ctx.organization_id) <= 1:
        raise LastOwnerError("Transfer ownership before removing the last owner.")
    await db.delete(member)
    record_audit_event(
        db,
        "member.left" if is_self else "member.removed",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="user",
        target_id=member.user_id,
    )
    await db.commit()


async def invite(
    db: AsyncSession,
    ctx: OrgContext,
    email: str,
    role: MemberRole,
    *,
    pepper: str,
    sender: EmailSender,
    public_origin: str,
) -> Invitation:
    actor_role = ctx.role or MemberRole.VIEWER
    if not can_assign_role(actor_role, role):
        raise PermissionDeniedError("Only owners can invite owners.")
    email = email.strip().lower()
    already = await db.execute(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == ctx.organization_id, func.lower(User.email) == email)
    )
    if already.scalar_one_or_none() is not None:
        raise ConflictError("This person is already a member.")
    plan = plan_for(ctx.organization.plan_code)
    members = await db.execute(
        select(func.count()).where(Membership.organization_id == ctx.organization_id)
    )
    require_below_limit(int(members.scalar_one()), plan.max_members, "members", plan)
    token = generate_token(32)
    invitation = Invitation(
        organization_id=ctx.organization_id,
        email=email,
        role=role,
        token_hash=hash_token(token, pepper=pepper),
        invited_by_user_id=ctx.actor_user_id,
        expires_at=datetime.now(UTC) + INVITATION_TTL,
    )
    db.add(invitation)
    await db.flush()
    record_audit_event(
        db,
        "invitation.created",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="invitation",
        target_id=invitation.id,
        details={"role": role.value},
    )
    await db.commit()
    await sender.send(
        OutgoingEmail(
            to=email,
            subject=f"You're invited to join {ctx.organization.name} on SerpTank",
            text=(
                f"You have been invited to join {ctx.organization.name} as {role.value}.\n"
                f"Accept the invitation: {public_origin.rstrip('/')}/invite?token={token}\n"
                "The link expires in 7 days."
            ),
        )
    )
    return invitation


async def accept_invitation(db: AsyncSession, user: User, token: str, pepper: str) -> uuid.UUID:
    row = (
        await db.execute(
            text(
                "SELECT id, organization_id, email, role, expires_at, accepted_at, revoked_at "
                "FROM app_lookup_invitation(:hash)"
            ),
            {"hash": hash_token(token, pepper=pepper)},
        )
    ).first()
    generic = "This invitation is invalid or has expired."
    if row is None:
        raise NotFoundError(generic)
    inv_id, org_id, email, role, expires_at, accepted_at, revoked_at = row
    if accepted_at or revoked_at or expires_at <= datetime.now(UTC):
        raise NotFoundError(generic)
    if user.email_verified_at is None:
        raise EmailVerificationRequiredError("Verify your email address to accept invitations.")
    if user.email.lower() != str(email).lower():
        raise PermissionDeniedError(
            "This invitation was sent to a different email address. Sign in with that account."
        )
    await bind_identity(db, organization_id=org_id)
    invitation = await db.get(Invitation, inv_id, with_for_update=True)
    if invitation is None or invitation.accepted_at is not None:
        raise NotFoundError(generic)
    invitation.accepted_at = datetime.now(UTC)
    db.add(Membership(organization_id=org_id, user_id=user.id, role=MemberRole(role)))
    record_audit_event(
        db,
        "invitation.accepted",
        actor_user_id=user.id,
        organization_id=org_id,
        target_type="invitation",
        target_id=inv_id,
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("You are already a member of this organization.") from exc
    return org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(str(org_id))
