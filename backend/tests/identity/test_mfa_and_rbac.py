"""MFA (TOTP + recovery codes), step-up re-authentication, RBAC and API keys."""

from __future__ import annotations

import time
import uuid
from typing import Annotated

import pyotp
import pytest
from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.core.models import MemberRole
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import (
    API_SCOPE_PERMISSIONS,
    ROLE_PERMISSIONS,
    Permission,
    can_assign_role,
    role_allows,
)
from tests.support.api import (
    STRONG_PASSWORD,
    Browser,
    create_org_with_member,
    login,
    make_client,
    signed_in_browser,
)


async def _reauth(b: Browser) -> None:
    response = await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    assert response.status_code == 200, response.text


async def _enable_totp(b: Browser) -> tuple[str, list[str]]:
    await _reauth(b)
    setup = (await b.post("/api/v1/auth/mfa/totp/setup")).json()
    secret = setup["secret"]
    assert setup["otpauth_uri"].startswith("otpauth://totp/SerpTank:")
    confirm = await b.post("/api/v1/auth/mfa/totp/confirm", {"code": pyotp.TOTP(secret).now()})
    assert confirm.status_code == 200, confirm.text
    codes = confirm.json()["codes"]
    assert len(codes) == 10
    return secret, codes


async def _user_id(b: Browser) -> uuid.UUID:
    return uuid.UUID((await b.get("/api/v1/auth/session")).json()["user"]["id"])


async def test_totp_setup_requires_recent_reauth(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    response = await b.post("/api/v1/auth/mfa/totp/setup")
    assert response.status_code == 403
    assert response.json()["code"] == "reauth_required"


async def test_reauth_rejects_wrong_password(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    response = await b.post("/api/v1/auth/reauth", {"password": "not my password at all"})
    assert response.status_code == 401


async def test_totp_login_flow(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    secret, _ = await _enable_totp(b)
    async with make_client(api_app) as client:
        other = Browser(client)
        await other.refresh_csrf()
        first = await login(other, email)
        assert first.json()["status"] == "mfa_required"
        assert "totp" in first.json()["mfa_methods"]
        # An MFA-pending session cannot use the product.
        assert (await other.get("/api/v1/auth/session")).status_code == 401
        bad = await other.post("/api/v1/auth/mfa/verify", {"code": "000000"})
        assert bad.status_code == 401
        # Codes are single-use: use a step not yet consumed by the confirm call.
        code = pyotp.TOTP(secret).at(int(time.time()) + 30)
        ok = await other.post("/api/v1/auth/mfa/verify", {"code": code})
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "authenticated"
        assert (await other.get("/api/v1/auth/session")).status_code == 200
        # Replaying the same code (e.g. on re-auth) fails.
        replay = await other.post("/api/v1/auth/reauth", {"code": code})
        assert replay.status_code == 401


async def test_recovery_code_is_single_use(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    _, codes = await _enable_totp(b)
    for expected in (200, 401):
        async with make_client(api_app) as client:
            other = Browser(client)
            await other.refresh_csrf()
            await login(other, email)
            response = await other.post("/api/v1/auth/mfa/verify", {"recovery_code": codes[0]})
            assert response.status_code == expected


async def test_disable_totp(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    await _enable_totp(b)
    assert (await b.delete("/api/v1/auth/mfa/totp")).status_code == 204
    async with make_client(api_app) as client:
        other = Browser(client)
        await other.refresh_csrf()
        assert (await login(other, email)).json()["status"] == "authenticated"


# ------------------------------------------------------------------ RBAC / orgs
def test_role_matrix_invariants() -> None:
    assert ROLE_PERMISSIONS[MemberRole.OWNER] == frozenset(Permission)
    assert not role_allows(MemberRole.ADMIN, Permission.ORG_DELETE)
    assert not role_allows(MemberRole.VIEWER, Permission.PROJECT_WRITE)
    assert not role_allows(MemberRole.EDITOR, Permission.MEMBERS_MANAGE)
    assert not role_allows(MemberRole.BILLING, Permission.PROJECT_READ)
    assert can_assign_role(MemberRole.OWNER, MemberRole.OWNER)
    assert not can_assign_role(MemberRole.ADMIN, MemberRole.OWNER)
    assert not can_assign_role(MemberRole.EDITOR, MemberRole.VIEWER)
    for perms in API_SCOPE_PERMISSIONS.values():
        assert Permission.MEMBERS_MANAGE not in perms
        assert Permission.API_KEYS_MANAGE not in perms
        assert Permission.BILLING_MANAGE not in perms


def _probe_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/orgs/{org_id}/probe")

    @router.get("/read")
    async def read(
        ctx: Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))],
    ) -> dict[str, str]:
        return {"org": str(ctx.organization_id)}

    @router.post("/write")
    async def write(
        ctx: Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))],
    ) -> dict[str, str]:
        return {"org": str(ctx.organization_id)}

    return router


@pytest.fixture
def probe(api_app: FastAPI) -> FastAPI:
    api_app.include_router(_probe_router())
    return api_app


@pytest.mark.parametrize(
    ("role", "read", "write", "keys"),
    [
        (MemberRole.OWNER, 200, 200, 200),
        (MemberRole.ADMIN, 200, 200, 200),
        (MemberRole.EDITOR, 200, 200, 403),
        (MemberRole.VIEWER, 200, 403, 403),
        (MemberRole.BILLING, 403, 403, 403),
    ],
)
async def test_org_access_matrix(
    probe: FastAPI,
    outbox: MemoryEmailSender,
    owner_session: AsyncSession,
    role: MemberRole,
    read: int,
    write: int,
    keys: int,
) -> None:
    b, _ = await signed_in_browser(probe, outbox)
    org_id = await create_org_with_member(owner_session, await _user_id(b), role)
    assert (await b.get(f"/api/v1/orgs/{org_id}/probe/read")).status_code == read
    assert (await b.post(f"/api/v1/orgs/{org_id}/probe/write")).status_code == write
    assert (await b.get(f"/api/v1/orgs/{org_id}/api-keys")).status_code == keys


async def test_non_member_gets_404(
    probe: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    owner, _ = await signed_in_browser(probe, outbox)
    org_id = await create_org_with_member(owner_session, await _user_id(owner), MemberRole.OWNER)
    stranger, _ = await signed_in_browser(probe, outbox)
    for path in ("probe/read", "api-keys", "audit-events"):
        response = await stranger.get(f"/api/v1/orgs/{org_id}/{path}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Organization not found."
    missing = await stranger.get(f"/api/v1/orgs/{uuid.uuid4()}/probe/read")
    assert missing.status_code == 404


async def test_org_requiring_mfa(
    probe: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(probe, outbox)
    org_id = await create_org_with_member(
        owner_session, await _user_id(b), MemberRole.OWNER, require_mfa=True
    )
    response = await b.get(f"/api/v1/orgs/{org_id}/probe/read")
    assert response.status_code == 403
    assert response.json()["code"] == "mfa_required"
    await _enable_totp(b)
    assert (await b.get(f"/api/v1/orgs/{org_id}/probe/read")).status_code == 200


async def test_api_key_lifecycle(
    probe: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(probe, outbox)
    org_id = await create_org_with_member(owner_session, await _user_id(b), MemberRole.OWNER)
    other_org = await create_org_with_member(owner_session, await _user_id(b), MemberRole.OWNER)
    # Creating keys requires step-up re-authentication.
    denied = await b.post(f"/api/v1/orgs/{org_id}/api-keys", {"name": "ci", "scopes": ["read"]})
    assert denied.status_code == 403
    await _reauth(b)
    created = await b.post(f"/api/v1/orgs/{org_id}/api-keys", {"name": "ci", "scopes": ["read"]})
    assert created.status_code == 201, created.text
    key = created.json()["key"]
    assert key.startswith("stk_live_")
    listed = (await b.get(f"/api/v1/orgs/{org_id}/api-keys")).json()
    assert "key" not in listed[0]

    async with make_client(probe) as machine:
        auth = {"Authorization": f"Bearer {key}"}
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/probe/read", headers=auth)
        ).status_code == 200
        # Read-only scope cannot write; keys never manage keys or read audit logs.
        assert (
            await machine.post(f"/api/v1/orgs/{org_id}/probe/write", headers=auth)
        ).status_code == 403
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/api-keys", headers=auth)
        ).status_code == 403
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/audit-events", headers=auth)
        ).status_code == 403
        # A key is confined to its own organization.
        assert (
            await machine.get(f"/api/v1/orgs/{other_org}/probe/read", headers=auth)
        ).status_code == 404
        # Tampered secret or unknown key.
        tampered = {"Authorization": f"Bearer {key[:-4]}AAAA"}
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/probe/read", headers=tampered)
        ).status_code == 401
        garbage = {"Authorization": "Bearer stk_live_nope"}
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/probe/read", headers=garbage)
        ).status_code == 401
        basic = {"Authorization": "Basic dXNlcjpwYXNz"}
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/probe/read", headers=basic)
        ).status_code == 401

        key_id = created.json()["id"]
        assert (await b.delete(f"/api/v1/orgs/{org_id}/api-keys/{key_id}")).status_code == 204
        assert (
            await machine.get(f"/api/v1/orgs/{org_id}/probe/read", headers=auth)
        ).status_code == 401

    events = [e["action"] for e in (await b.get(f"/api/v1/orgs/{org_id}/audit-events")).json()]
    assert events[:2] == ["api_key.revoked", "api_key.created"]
