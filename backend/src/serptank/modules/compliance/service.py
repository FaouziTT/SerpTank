"""Data-subject rights and retention (GDPR Art. 15/17/20; CCPA equivalents).

* **Export** - a JSON copy of the personal data we hold about the caller: profile,
  memberships, sign-in methods (names/dates only, never secrets), active sessions, and
  their own audit trail. Organization data is exported by the org's CSV exports (M11).
* **Account deletion** - immediate: sessions revoked, memberships removed, credentials
  (password hash, passkeys, TOTP, recovery codes, pending email tokens) destroyed, and
  the profile anonymised so the email can be reused. The anonymised row is hard-deleted
  after ``deletion_grace_days``; audit events keep only a null actor.
  Refused while the user is the last owner of an active organization (transfer
  ownership or delete the organization first) so no org is left without an owner.
* **Retention** - organizations soft-deleted more than ``deletion_grace_days`` ago are
  hard-deleted (every tenant table cascades), and so are anonymised users.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.audit import AuditEvent, record_audit_event
from serptank.core.db import bind_identity
from serptank.core.errors import ConflictError
from serptank.core.models import MemberRole
from serptank.modules.identity.models import (
    EmailToken,
    MfaTotp,
    RecoveryCode,
    User,
    WebAuthnCredential,
)
from serptank.modules.reports.models import Notification
from serptank.modules.tenancy.models import Membership, Organization

logger = structlog.get_logger(__name__)
MAX_AUDIT_EVENTS = 1000


class LastOwnerError(ConflictError):
    code = "last_owner"
    title = "You are the last owner of an organization"


async def personal_data(
    db: AsyncSession, user: User, sessions: list[dict[str, Any]]
) -> dict[str, Any]:
    memberships = (
        await db.execute(
            select(Organization.id, Organization.name, Membership.role, Membership.created_at)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user.id, Organization.deleted_at.is_(None))
        )
    ).all()
    passkeys = (
        await db.execute(
            select(WebAuthnCredential.name, WebAuthnCredential.created_at).where(
                WebAuthnCredential.user_id == user.id
            )
        )
    ).all()
    events = (
        await db.execute(
            select(AuditEvent)
            .where(AuditEvent.actor_user_id == user.id, AuditEvent.organization_id.is_(None))
            .order_by(AuditEvent.created_at.desc())
            .limit(MAX_AUDIT_EVENTS)
        )
    ).scalars()
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "email_verified_at": _iso(user.email_verified_at),
            "created_at": _iso(user.created_at),
            "last_login_at": _iso(user.last_login_at),
            "password_set": user.password_hash is not None,
            "google_linked": user.google_subject is not None,
            "mfa_enabled": user.mfa_enabled,
        },
        "memberships": [
            {
                "organization_id": str(oid),
                "organization": name,
                "role": role.value,
                "since": _iso(since),
            }
            for oid, name, role, since in memberships
        ],
        "passkeys": [{"name": name, "created_at": _iso(at)} for name, at in passkeys],
        "sessions": sessions,
        "security_events": [
            {
                "action": e.action,
                "at": _iso(e.created_at),
                "ip_address": str(e.ip_address) if e.ip_address else None,
                "user_agent": e.user_agent,
            }
            for e in events
        ],
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def delete_account(db: AsyncSession, user: User) -> list[uuid.UUID]:
    """Anonymise and detach ``user``. Returns the orgs they left."""
    owned = (
        await db.execute(
            select(Organization.id, Organization.name)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(
                Membership.user_id == user.id,
                Membership.role == MemberRole.OWNER,
                Organization.deleted_at.is_(None),
            )
        )
    ).all()
    blocking = []
    for org_id, name in owned:
        await bind_identity(db, organization_id=org_id)
        owners = (
            await db.execute(
                select(func.count()).where(
                    Membership.organization_id == org_id, Membership.role == MemberRole.OWNER
                )
            )
        ).scalar_one()
        if owners <= 1:
            blocking.append(name)
    if blocking:
        raise LastOwnerError(
            "Transfer ownership or delete these organizations first: " + ", ".join(blocking) + ".",
            extra={"organizations": blocking},
        )
    orgs = list(
        (
            await db.execute(
                select(Membership.organization_id).where(Membership.user_id == user.id)
            )
        ).scalars()
    )
    for org_id in orgs:
        await bind_identity(db, organization_id=org_id)
        await db.execute(
            delete(Membership).where(
                Membership.organization_id == org_id, Membership.user_id == user.id
            )
        )
        await db.execute(
            delete(Notification).where(
                Notification.organization_id == org_id, Notification.user_id == user.id
            )
        )
        record_audit_event(
            db,
            "member.account_deleted",
            actor_user_id=None,
            organization_id=org_id,
            target_type="user",
            target_id=user.id,
        )
        await db.commit()
    for model in (WebAuthnCredential, MfaTotp, RecoveryCode, EmailToken):
        await db.execute(delete(model).where(model.user_id == user.id))
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            email=f"deleted+{user.id.hex}@deleted.invalid",
            full_name="",
            password_hash=None,
            google_subject=None,
            mfa_enabled=False,
            is_active=False,
            deleted_at=datetime.now(UTC),
        )
    )
    # The user is the actor; the reference becomes NULL when the row is purged.
    record_audit_event(
        db, "auth.account_deleted", actor_user_id=user.id, target_type="user", target_id=user.id
    )
    await db.commit()
    return orgs


async def purge_expired(
    system: AsyncSession, grace_days: int, now: datetime | None = None
) -> dict[str, int]:
    """Hard-delete orgs and anonymised users past the grace period (scheduler session)."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=grace_days)
    orgs = await system.execute(
        delete(Organization)
        .where(Organization.deleted_at.is_not(None), Organization.deleted_at < cutoff)
        .returning(Organization.id)
    )
    org_count = len(orgs.all())
    users = await system.execute(
        delete(User)
        .where(User.deleted_at.is_not(None), User.deleted_at < cutoff)
        .returning(User.id)
    )
    user_count = len(users.all())
    await system.commit()
    if org_count or user_count:
        logger.info("retention_purged", organizations=org_count, users=user_count)
    return {"organizations": org_count, "users": user_count}
