"""Passkeys: registration, passwordless sign-in, challenge binding, clone detection."""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from serptank.core.email import MemoryEmailSender
from tests.support.api import (
    ORIGIN,
    STRONG_PASSWORD,
    Browser,
    login,
    make_client,
    signed_in_browser,
)
from tests.support.soft_authenticator import SoftAuthenticator


async def _register_passkey(b: Browser) -> SoftAuthenticator:
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    options = (await b.post("/api/v1/auth/passkeys/register/options")).json()
    assert options["rp"]["id"] == "localhost"
    authenticator = SoftAuthenticator(ORIGIN, "localhost")
    response = await b.post(
        "/api/v1/auth/passkeys/register",
        {"credential": authenticator.create(options), "name": "Laptop"},
    )
    assert response.status_code == 200, response.text
    return authenticator


async def _passkey_login(b: Browser, authenticator: SoftAuthenticator, **kw: bool):  # type: ignore[no-untyped-def]
    options = (await b.post("/api/v1/auth/passkeys/login/options")).json()
    assert options["userVerification"] == "required"
    return await b.post(
        "/api/v1/auth/passkeys/login", {"credential": authenticator.get(options, **kw)}
    )


async def test_register_requires_reauth(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    response = await b.post("/api/v1/auth/passkeys/register/options")
    assert response.status_code == 403


async def test_passwordless_sign_in(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    authenticator = await _register_passkey(b)
    listed = (await b.get("/api/v1/auth/passkeys")).json()
    assert [p["name"] for p in listed] == ["Laptop"]
    async with make_client(api_app) as client:
        fresh = Browser(client)
        await fresh.refresh_csrf()
        response = await _passkey_login(fresh, authenticator)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "authenticated"
        assert (await fresh.get("/api/v1/auth/session")).json()["user"]["email"] == email
    # Having a passkey turns on MFA: password sign-in now needs a second factor.
    async with make_client(api_app) as client:
        pw = Browser(client)
        await pw.refresh_csrf()
        assert (await login(pw, email)).json()["status"] == "mfa_required"


async def test_passkey_requires_user_verification(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    authenticator = await _register_passkey(b)
    async with make_client(api_app) as client:
        fresh = Browser(client)
        await fresh.refresh_csrf()
        response = await _passkey_login(fresh, authenticator, user_verified=False)
        assert response.status_code == 400
        assert response.json()["code"] == "passkey_failed"


async def test_cloned_authenticator_rejected(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    authenticator = await _register_passkey(b)
    async with make_client(api_app) as client:
        fresh = Browser(client)
        await fresh.refresh_csrf()
        assert (await _passkey_login(fresh, authenticator)).status_code == 200
        await fresh.refresh_csrf()
        replayed = await _passkey_login(fresh, authenticator, reuse_count=True)
        assert replayed.status_code == 400


async def test_challenge_is_bound_to_browser_and_single_use(
    api_app: FastAPI, outbox: MemoryEmailSender
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    authenticator = await _register_passkey(b)
    async with make_client(api_app) as c1, make_client(api_app) as c2:
        first, second = Browser(c1), Browser(c2)
        await first.refresh_csrf()
        await second.refresh_csrf()
        options = (await first.post("/api/v1/auth/passkeys/login/options")).json()
        assertion = authenticator.get(options)
        stolen = await second.post("/api/v1/auth/passkeys/login", {"credential": assertion})
        assert stolen.status_code == 400
        ok = await first.post("/api/v1/auth/passkeys/login", {"credential": assertion})
        assert ok.status_code == 200
        again = await first.post("/api/v1/auth/passkeys/login", {"credential": assertion})
        assert again.status_code == 400


async def test_phishing_origin_rejected(api_app: FastAPI, outbox: MemoryEmailSender) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    await b.post("/api/v1/auth/reauth", {"password": STRONG_PASSWORD})
    options = (await b.post("/api/v1/auth/passkeys/register/options")).json()
    authenticator = SoftAuthenticator("https://serptank-login.evil", "localhost")
    response = await b.post(
        "/api/v1/auth/passkeys/register",
        {"credential": authenticator.create(options), "name": "phish"},
    )
    assert response.status_code == 400


@pytest.mark.parametrize("credential", [{}, {"rawId": "!!!"}, {"rawId": "AAAA"}])
async def test_malformed_or_unknown_credentials(
    browser: Browser, credential: dict[str, str]
) -> None:
    await browser.post("/api/v1/auth/passkeys/login/options")
    response = await browser.post("/api/v1/auth/passkeys/login", {"credential": credential})
    assert response.status_code == 400
