"""Organizations, members, invitations, projects, markets and domain verification."""

from __future__ import annotations

import uuid

import dns.asyncresolver
import dns.resolver
import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.modules.projects.domains import InvalidDomainError, normalize_domain
from serptank.modules.projects.verification import check_dns, system_txt_resolver
from serptank.modules.tenancy.models import Organization
from tests.support.api import (
    STRONG_PASSWORD,
    Browser,
    FakeInternet,
    extract_token,
    make_client,
    signed_in_browser,
)


async def _create_org(b: Browser, name: str = "Acme Marketing") -> str:
    response = await b.post("/api/v1/orgs", {"name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _members(b: Browser, org: str) -> list[dict[str, object]]:
    return (await b.get(f"/api/v1/orgs/{org}/members")).json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------- organizations
async def test_create_and_list_orgs(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    orgs = (await b.get("/api/v1/orgs")).json()
    assert [(o["id"], o["role"]) for o in orgs] == [(org, "owner")]
    assert orgs[0]["slug"].startswith("acme-marketing-")
    session = (await b.get("/api/v1/auth/session")).json()
    assert session["memberships"][0]["role"] == "owner"


async def test_require_mfa_needs_own_mfa(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    response = await b.client.patch(
        f"/api/v1/orgs/{org}",
        json={"require_mfa": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf},
    )
    assert response.status_code == 403


async def test_delete_org_requires_reauth_and_hides_it(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    assert (await b.delete(f"/api/v1/orgs/{org}")).status_code == 403
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    assert (await b.delete(f"/api/v1/orgs/{org}")).status_code == 204
    assert (await b.get(f"/api/v1/orgs/{org}")).status_code == 404
    assert (await b.get("/api/v1/orgs")).json() == []


# ------------------------------------------------------------------ invitations
async def _invite(owner: Browser, org: str, email: str, role: str = "editor") -> httpx.Response:
    return await owner.post(f"/api/v1/orgs/{org}/invitations", {"email": email, "role": role})


async def test_invitation_flow(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    owner, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(owner)
    await _set_plan(owner_session, org, "pro")
    invitee, invitee_email = await signed_in_browser(api_app, outbox)
    assert (await _invite(owner, org, invitee_email)).status_code == 201
    token = extract_token(outbox.outbox[-1].text)
    accepted = await invitee.post("/api/v1/invitations/accept", {"token": token})
    assert accepted.status_code == 200, accepted.text
    roles = {m["email"]: m["role"] for m in await _members(owner, org)}
    assert roles[invitee_email] == "editor"
    # Single use.
    again = await invitee.post("/api/v1/invitations/accept", {"token": token})
    assert again.status_code == 404
    # Duplicate invite for an existing member.
    assert (await _invite(owner, org, invitee_email)).status_code == 409


async def test_invitation_bound_to_email(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    owner, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(owner)
    await _invite(owner, org, "someone-else@example.com")
    token = extract_token(outbox.outbox[-1].text)
    thief, _ = await signed_in_browser(api_app, outbox)
    response = await thief.post("/api/v1/invitations/accept", {"token": token})
    assert response.status_code == 403
    assert (await thief.get(f"/api/v1/orgs/{org}")).status_code == 404


async def test_revoked_and_expired_invitations(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    owner, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(owner)
    invitee, email = await signed_in_browser(api_app, outbox)
    invitation = (await _invite(owner, org, email)).json()
    token = extract_token(outbox.outbox[-1].text)
    assert (
        await owner.delete(f"/api/v1/orgs/{org}/invitations/{invitation['id']}")
    ).status_code == 204
    assert (await invitee.post("/api/v1/invitations/accept", {"token": token})).status_code == 404
    await _invite(owner, org, email)
    token2 = extract_token(outbox.outbox[-1].text)
    from serptank.modules.tenancy.models import Invitation

    await owner_session.execute(
        update(Invitation).where(Invitation.email == email).values(expires_at=Invitation.created_at)
    )
    await owner_session.commit()
    assert (await invitee.post("/api/v1/invitations/accept", {"token": token2})).status_code == 404


async def _set_plan(owner_session: AsyncSession, org: str, plan: str) -> None:
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code=plan)
    )
    await owner_session.commit()


async def test_member_limit_per_plan(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    owner, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(owner)
    assert (await _invite(owner, org, "one@example.com")).status_code == 201  # 1 member + 1 invite
    _, second = await signed_in_browser(api_app, outbox)
    invited, email = await signed_in_browser(api_app, outbox)
    await _invite(owner, org, email)
    await invited.post(
        "/api/v1/invitations/accept", {"token": extract_token(outbox.outbox[-1].text)}
    )
    over = await _invite(owner, org, second)  # free plan: 2 members max
    assert over.status_code == 402
    assert over.json()["code"] == "plan_upgrade_required"


async def test_admin_cannot_invite_owner(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    owner, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(owner)
    await _set_plan(owner_session, org, "pro")
    admin, admin_email = await signed_in_browser(api_app, outbox)
    await _invite(owner, org, admin_email, "admin")
    await admin.post("/api/v1/invitations/accept", {"token": extract_token(outbox.outbox[-1].text)})
    assert (await _invite(admin, org, "x@example.com", "owner")).status_code == 403
    assert (await _invite(admin, org, "y@example.com", "viewer")).status_code == 201


# --------------------------------------------------------------------- members
async def test_last_owner_guard_and_role_changes(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    owner, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(owner)
    members = await _members(owner, org)
    own_id = members[0]["id"]
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": owner.csrf}
    # Role changes are privilege changes: a recent step-up is required.
    stale = await owner.client.patch(
        f"/api/v1/orgs/{org}/members/{own_id}", json={"role": "admin"}, headers=headers
    )
    assert stale.status_code == 403
    assert stale.json()["code"] == "reauth_required"
    assert (
        await owner.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    ).status_code == 200
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": owner.csrf}
    demote = await owner.client.patch(
        f"/api/v1/orgs/{org}/members/{own_id}", json={"role": "admin"}, headers=headers
    )
    assert demote.status_code == 409
    assert demote.json()["code"] == "last_owner"
    assert (await owner.delete(f"/api/v1/orgs/{org}/members/{own_id}")).status_code == 409

    editor, editor_email = await signed_in_browser(api_app, outbox)
    await _invite(owner, org, editor_email, "editor")
    await editor.post(
        "/api/v1/invitations/accept", {"token": extract_token(outbox.outbox[-1].text)}
    )
    editor_member = next(m for m in await _members(owner, org) if m["email"] == editor_email)
    # Editors cannot manage members; they can leave.
    eh = {"Origin": "http://localhost:3000", "X-CSRF-Token": editor.csrf}
    assert (
        await editor.client.patch(
            f"/api/v1/orgs/{org}/members/{own_id}", json={"role": "viewer"}, headers=eh
        )
    ).status_code == 403
    assert (
        await editor.delete(f"/api/v1/orgs/{org}/members/{editor_member['id']}")
    ).status_code == 204
    assert (await editor.get(f"/api/v1/orgs/{org}")).status_code == 404


# -------------------------------------------------------------------- projects
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Example.COM", "example.com"),
        ("https://www.example.co.uk/path?q=1", "www.example.co.uk"),
        ("bücher.de", "xn--bcher-kva.de"),
        ("example.com:8080", "example.com"),
    ],
)
def test_normalize_domain(raw: str, expected: str) -> None:
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "localhost",
        "127.0.0.1",
        "[::1]",
        "co.uk",
        "no_underscores.com",
        "a..b.com",
        "user@host.com",
        "com",
        "shop.internal",
        "printer.local",
    ],
)
def test_rejects_bad_domains(raw: str) -> None:
    with pytest.raises(InvalidDomainError):
        normalize_domain(raw)


async def test_project_crud_and_markets(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    created = await b.post(
        f"/api/v1/orgs/{org}/projects", {"name": "Main site", "domain": "https://Example.com/"}
    )
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["primary_domain"] == "example.com"
    assert project["verified"] is False
    assert project["markets"][0]["search_engines"] == ["google"]
    # Free plan: one project, Google-only markets.
    second = await b.post(f"/api/v1/orgs/{org}/projects", {"name": "Two", "domain": "two.com"})
    assert second.status_code == 402
    assert second.json()["code"] == "plan_upgrade_required"
    # Free plan: one market per project.
    extra = await b.post(
        f"/api/v1/orgs/{org}/projects/{project['id']}/markets",
        {"country": "DE", "language": "de"},
    )
    assert extra.status_code == 402
    # The only market can't be removed: every feature is scoped to a market.
    only = project["markets"][0]["id"]
    last = await b.delete(f"/api/v1/orgs/{org}/projects/{project['id']}/markets/{only}")
    assert last.status_code == 409
    # Free plan: Google only (checked on a fresh org to isolate the engine rule).
    other_org = await _create_org(b, "Engines")
    bing = await b.post(
        f"/api/v1/orgs/{other_org}/projects",
        {
            "name": "Bing",
            "domain": "bing-test.com",
            "markets": [{"country": "DE", "language": "de", "search_engines": ["google", "bing"]}],
        },
    )
    assert bing.status_code == 402
    assert bing.json()["missing"] == ["bing"]


async def test_paid_plan_allows_engines(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    await _set_plan(owner_session, org, "pro")
    created = await b.post(
        f"/api/v1/orgs/{org}/projects",
        {
            "name": "Shop",
            "domain": "shop.example",
            "markets": [
                {
                    "country": "us",
                    "language": "en",
                    "search_engines": ["google", "bing", "yahoo"],
                    "ai_engines": ["chatgpt", "google_ai_overview"],
                },
                {"country": "GB", "language": "en-GB", "device": "mobile"},
            ],
        },
    )
    assert created.status_code == 422  # "shop.example" is not a registrable domain
    assert created.json()["code"] == "invalid_domain"
    created = await b.post(
        f"/api/v1/orgs/{org}/projects",
        {
            "name": "Shop",
            "domain": "shop.example.com",
            "markets": [
                {
                    "country": "us",
                    "language": "en",
                    "search_engines": ["google", "bing", "yahoo"],
                    "ai_engines": ["chatgpt", "google_ai_overview"],
                },
                {"country": "GB", "language": "en-GB", "device": "mobile"},
            ],
        },
    )
    assert created.status_code == 201, created.text
    markets = created.json()["markets"]
    assert markets[0]["country"] == "US"
    assert markets[0]["search_engines"] == ["bing", "google", "yahoo"]
    yandex = await b.post(
        f"/api/v1/orgs/{org}/projects/{created.json()['id']}/markets",
        {"country": "RU", "language": "ru", "search_engines": ["yandex"]},
    )
    assert yandex.status_code == 402


async def test_projects_are_tenant_isolated(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    a, _ = await signed_in_browser(api_app, outbox)
    org_a = await _create_org(a, "Org A")
    project = (
        await a.post(f"/api/v1/orgs/{org_a}/projects", {"name": "A", "domain": "a-site.com"})
    ).json()
    b, _ = await signed_in_browser(api_app, outbox)
    org_b = await _create_org(b, "Org B")
    # B cannot reach A's org or A's project through its own org.
    assert (await b.get(f"/api/v1/orgs/{org_a}/projects")).status_code == 404
    assert (await b.get(f"/api/v1/orgs/{org_b}/projects/{project['id']}")).status_code == 404
    assert (await b.delete(f"/api/v1/orgs/{org_b}/projects/{project['id']}")).status_code == 404
    assert (await a.get(f"/api/v1/orgs/{org_a}/projects/{project['id']}")).status_code == 200


async def test_domain_verification_dns_and_html(
    api_app: FastAPI, outbox: MemoryEmailSender, internet: FakeInternet
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "V", "domain": "www.verify-me.co.uk"})
    ).json()
    base = f"/api/v1/orgs/{org}/projects/{project['id']}"
    dns = (await b.post(f"{base}/verification", {"method": "dns"})).json()
    assert dns["dns_record_name"] == "verify-me.co.uk"
    assert dns["dns_record_value"] == f"serptank-site-verification={dns['token']}"

    records: dict[str, list[str]] = {}

    async def resolver(name: str) -> list[str]:
        return records.get(name, [])

    api_app.state.txt_resolver = resolver
    assert (await b.post(f"{base}/verification/check")).json()["verified"] is False
    records["verify-me.co.uk"] = ["v=spf1 -all", f'"{dns["dns_record_value"]}"']
    assert (await b.post(f"{base}/verification/check")).json()["verified"] is True
    assert (await b.get(base)).json()["verified"] is True

    # HTML method, served through the SSRF-safe client.
    project2_org = await _create_org(b, "Second")
    p2 = (
        await b.post(
            f"/api/v1/orgs/{project2_org}/projects", {"name": "H", "domain": "html-site.com"}
        )
    ).json()
    base2 = f"/api/v1/orgs/{project2_org}/projects/{p2['id']}"
    html = (await b.post(f"{base2}/verification", {"method": "html"})).json()
    assert html["file_url"] == "https://html-site.com/.well-known/serptank-verification.txt"
    internet.handlers["html-site.com"] = lambda _r: httpx.Response(200, text="wrong-token")
    assert (await b.post(f"{base2}/verification/check")).json()["verified"] is False
    internet.handlers["html-site.com"] = lambda _r: httpx.Response(200, text=html["token"] + "\n")
    assert (await b.post(f"{base2}/verification/check")).json()["verified"] is True


async def test_anonymous_cannot_create_org(api_app: FastAPI) -> None:
    async with make_client(api_app) as client:
        b = Browser(client)
        await b.refresh_csrf()
        assert (await b.post("/api/v1/orgs", {"name": "Nope"})).status_code == 401


async def test_entitlements_endpoint(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    free = (await b.get(f"/api/v1/orgs/{org}/entitlements")).json()
    assert free["search_engines"] == ["google"]
    assert free["max_projects"] == 1
    await _set_plan(owner_session, org, "agency")
    agency = (await b.get(f"/api/v1/orgs/{org}/entitlements")).json()
    assert "yandex" in agency["search_engines"]
    assert len(agency["search_engines"]) == 8


async def test_project_lifecycle_on_paid_plan(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    await _set_plan(owner_session, org, "pro")
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "Site", "domain": "life.com"})
    ).json()
    base = f"/api/v1/orgs/{org}/projects/{project['id']}"
    # Rename.
    renamed = await b.client.patch(
        base,
        json={"name": "Renamed"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf},
    )
    assert renamed.json()["name"] == "Renamed"
    # Add a second market; a duplicate is a conflict; then the extra one can be removed.
    de = {"country": "DE", "language": "de", "search_engines": ["google", "bing"]}
    added = await b.post(f"{base}/markets", de)
    assert added.status_code == 201, added.text
    assert (await b.post(f"{base}/markets", de)).status_code == 409
    assert (await b.delete(f"{base}/markets/{added.json()['id']}")).status_code == 204
    unknown = "0192f1a4-0000-7000-8000-000000000009"
    assert (await b.delete(f"{base}/markets/{unknown}")).status_code == 404
    # Regional engines need the agency plan or add-on.
    yandex = await b.post(f"{base}/markets", {**de, "search_engines": ["yandex"]})
    assert yandex.status_code == 402
    assert yandex.json()["missing"] == ["yandex"]
    # Checking before starting verification is a conflict.
    assert (await b.post(f"{base}/verification/check")).status_code == 409
    # Soft delete: gone from the API and listing, audited.
    assert (await b.delete(base)).status_code == 204
    assert (await b.get(base)).status_code == 404
    assert (await b.get(f"/api/v1/orgs/{org}/projects")).json() == []
    actions = [e["action"] for e in (await b.get(f"/api/v1/orgs/{org}/audit-events")).json()]
    assert "project.deleted" in actions


async def test_update_org_settings(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = await _create_org(b)
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": b.csrf}
    renamed = await b.client.patch(f"/api/v1/orgs/{org}", json={"name": "New"}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "New"
    # Requiring MFA for everyone needs MFA on your own account first (no self-lockout).
    mfa = await b.client.patch(f"/api/v1/orgs/{org}", json={"require_mfa": True}, headers=headers)
    assert mfa.status_code == 403
    events = (await b.get(f"/api/v1/orgs/{org}/audit-events")).json()
    assert any(e["action"] == "org.updated" and e["details"] == {"name": "New"} for e in events)


async def test_system_txt_resolver_handles_missing_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def nxdomain(*_args: object, **_kwargs: object) -> object:
        raise dns.resolver.NXDOMAIN

    monkeypatch.setattr(dns.asyncresolver, "resolve", nxdomain)
    assert await system_txt_resolver("example.com") == []

    class _Record:
        strings = (b"serptank-site-verification=", b"abc")

    async def found(*_args: object, **_kwargs: object) -> object:
        return [_Record()]

    monkeypatch.setattr(dns.asyncresolver, "resolve", found)
    assert await system_txt_resolver("example.com") == ["serptank-site-verification=abc"]
    assert await check_dns("www.example.com", "abc", system_txt_resolver) is True
