"""End-to-end authentication flows through the HTTP API."""

from __future__ import annotations

from fastapi import FastAPI

from serptank.core.email import MemoryEmailSender
from tests.identity.conftest import (
    ORIGIN,
    STRONG_PASSWORD,
    Browser,
    extract_token,
    login,
    make_client,
    register_and_verify,
    signed_in_browser,
)


async def test_register_verify_login_session(browser: Browser, outbox: MemoryEmailSender) -> None:
    email = await register_and_verify(browser, outbox)
    response = await login(browser, email)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "authenticated"
    assert body["user"]["email"] == email
    cookie = response.headers["set-cookie"]
    assert "st_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie.replace("samesite", "SameSite")
    session = (await browser.get("/api/v1/auth/session")).json()
    assert session["user"]["email_verified"] is True
    assert session["memberships"] == []


async def test_login_requires_verified_email(browser: Browser) -> None:
    await browser.post(
        "/api/v1/auth/register",
        {"email": "unverified@example.com", "password": STRONG_PASSWORD, "full_name": "U"},
    )
    response = await login(browser, "unverified@example.com")
    assert response.status_code == 403
    assert response.json()["code"] == "email_not_verified"


async def test_registration_does_not_reveal_existing_accounts(
    browser: Browser, outbox: MemoryEmailSender
) -> None:
    email = await register_and_verify(browser, outbox)
    again = await browser.post(
        "/api/v1/auth/register", {"email": email, "password": STRONG_PASSWORD, "full_name": "X"}
    )
    assert again.status_code == 202
    assert again.json() == {"status": "check_email"}
    assert "already exists" in outbox.outbox[-1].text


async def test_login_errors_are_generic(browser: Browser, outbox: MemoryEmailSender) -> None:
    email = await register_and_verify(browser, outbox)
    wrong = await login(browser, email, "wrong password entirely")
    unknown = await login(browser, "nobody-here@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Incorrect email or password."


async def test_weak_password_rejected(browser: Browser) -> None:
    for password, fragment in (("short", "at least"), ("password1234", "too common")):
        response = await browser.post(
            "/api/v1/auth/register",
            {"email": "weak@example.com", "password": password, "full_name": "W"},
        )
        assert response.status_code == 422
        assert response.json()["code"] == "weak_password"
        assert fragment in response.json()["detail"]


async def test_login_requires_csrf_token_and_presession(api_app: FastAPI) -> None:
    async with make_client(api_app) as client:
        body = {"email": "a@example.com", "password": STRONG_PASSWORD}
        # No pre-session at all: rejected before credentials are checked.
        response = await client.post("/api/v1/auth/login", json=body, headers={"Origin": ORIGIN})
        assert response.status_code == 403
        assert response.json()["code"] == "csrf_failed"
        # Pre-session cookie but no token: rejected by the CSRF middleware.
        await client.get("/api/v1/auth/csrf")
        response = await client.post("/api/v1/auth/login", json=body, headers={"Origin": ORIGIN})
        assert response.status_code == 403
        # Token from ANOTHER browser: rejected (token is bound to the pre-session).
        async with make_client(api_app) as other:
            foreign = (await other.get("/api/v1/auth/csrf")).json()["csrf_token"]
        response = await client.post(
            "/api/v1/auth/login", json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": foreign}
        )
        assert response.status_code == 403


async def test_cross_site_login_is_rejected(browser: Browser) -> None:
    response = await browser.client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": STRONG_PASSWORD},
        headers={"Origin": "https://evil.example", "X-CSRF-Token": browser.csrf},
    )
    assert response.status_code == 403


async def test_session_token_rotates_and_csrf_changes_on_login(
    browser: Browser, outbox: MemoryEmailSender
) -> None:
    email = await register_and_verify(browser, outbox)
    pre_csrf = browser.csrf
    await login(browser, email)
    assert browser.csrf != pre_csrf
    first = browser.client.cookies.get("st_session")
    await login(browser, email)
    second = browser.client.cookies.get("st_session")
    assert first
    assert second
    assert first != second


async def test_authenticated_requests_need_session_bound_csrf(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    stale = await b.client.post(
        "/api/v1/auth/logout-all", headers={"Origin": ORIGIN, "X-CSRF-Token": "x" * 64}
    )
    assert stale.status_code == 403
    assert (await b.post("/api/v1/auth/logout-all")).status_code == 204


async def test_logout_invalidates_session(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    token = b.client.cookies.get("st_session")
    assert (await b.post("/api/v1/auth/logout")).status_code == 204
    async with make_client(api_app) as attacker:
        attacker.cookies.set("st_session", token or "")
        assert (await attacker.get("/api/v1/auth/session")).status_code == 401


async def test_list_and_revoke_sessions(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    async with make_client(api_app) as other_client:
        other = Browser(other_client)
        await other.refresh_csrf()
        assert (await login(other, email)).json()["status"] == "authenticated"
        sessions = (await b.get("/api/v1/auth/sessions")).json()
        assert len(sessions) == 2
        foreign = next(s for s in sessions if not s["current"])
        assert (await b.delete(f"/api/v1/auth/sessions/{foreign['id']}")).status_code == 204
        assert (await other.get("/api/v1/auth/session")).status_code == 401
        assert (await b.get("/api/v1/auth/session")).status_code == 200


async def test_password_reset_flow_revokes_sessions(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    async with make_client(api_app) as anon_client:
        anon = Browser(anon_client)
        await anon.refresh_csrf()
        assert (
            await anon.post("/api/v1/auth/password/forgot", {"email": email})
        ).status_code == 202
        token = extract_token(outbox.outbox[-1].text)
        new_password = "a completely different passphrase 7"
        reset = await anon.post(
            "/api/v1/auth/password/reset", {"token": token, "new_password": new_password}
        )
        assert reset.status_code == 204
        replay = await anon.post(
            "/api/v1/auth/password/reset", {"token": token, "new_password": new_password}
        )
        assert replay.status_code == 400
        assert replay.json()["code"] == "invalid_token"
        assert (await b.get("/api/v1/auth/session")).status_code == 401  # revoked
        assert (await login(anon, email, STRONG_PASSWORD)).status_code == 401
        assert (await login(anon, email, new_password)).json()["status"] == "authenticated"
    assert "password was changed" in outbox.outbox[-1].subject + outbox.outbox[-1].text


async def test_forgot_password_unknown_email_is_silent(
    browser: Browser, outbox: MemoryEmailSender
) -> None:
    before = len(outbox.outbox)
    response = await browser.post("/api/v1/auth/password/forgot", {"email": "ghost@example.com"})
    assert response.status_code == 202
    assert len(outbox.outbox) == before


async def test_change_password_revokes_other_sessions(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    async with make_client(api_app) as other_client:
        other = Browser(other_client)
        await other.refresh_csrf()
        await login(other, email)
        response = await b.post(
            "/api/v1/auth/password/change",
            {"current_password": STRONG_PASSWORD, "new_password": "another strong passphrase 99"},
        )
        assert response.status_code == 200, response.text
        assert (await b.get("/api/v1/auth/session")).status_code == 200
        assert (await other.get("/api/v1/auth/session")).status_code == 401


async def test_brute_force_throttles_account_from_ip(
    browser: Browser, outbox: MemoryEmailSender
) -> None:
    email = await register_and_verify(browser, outbox)
    codes = [(await login(browser, email, f"wrong-{i}-password")).status_code for i in range(12)]
    assert codes[:5] == [401] * 5
    assert 429 in codes
    # The legitimate owner from ANOTHER network is not locked out.
    async with make_client(browser.client._transport.app, ip="192.0.2.200") as other_client:  # type: ignore[attr-defined]
        other = Browser(other_client)
        await other.refresh_csrf()
        assert (await login(other, email)).json()["status"] == "authenticated"


async def test_session_endpoint_requires_auth(api_app: FastAPI) -> None:
    async with make_client(api_app) as client:
        response = await client.get("/api/v1/auth/session")
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


async def test_security_events_recorded(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    actions = [e["action"] for e in (await b.get("/api/v1/auth/security-events")).json()]
    assert "auth.login" in actions
    assert "user.registered" in actions
