"""Sign in with Google: state/nonce/PKCE binding, ID-token verification, no auto-linking."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI

from serptank.core.email import MemoryEmailSender
from tests.identity.conftest import (
    Browser,
    FakeInternet,
    make_client,
    register_and_verify,
    signed_in_browser,
)

CLIENT_ID = "client-123.apps.googleusercontent.com"


class FakeGoogle:
    def __init__(self, internet: FakeInternet) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        # Key used to sign ID tokens; tests swap it to simulate forged tokens.
        self.signing_key = self.key
        self.kid = "test-kid"
        self.claims: dict[str, object] = {}
        self.last_token_request: dict[str, list[str]] = {}
        self.expected_verifier_challenge: str | None = None
        internet.handlers["oauth2.googleapis.com"] = self._token
        internet.handlers["www.googleapis.com"] = self._jwks

    def _jwks(self, _request: httpx.Request) -> httpx.Response:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        jwk.update({"kid": self.kid, "use": "sig", "alg": "RS256"})
        return httpx.Response(200, json={"keys": [jwk]})

    def _token(self, request: httpx.Request) -> httpx.Response:
        self.last_token_request = parse_qs(request.content.decode())
        verifier = self.last_token_request["code_verifier"][0]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        if challenge.rstrip(b"=").decode() != self.expected_verifier_challenge:
            return httpx.Response(400, json={"error": "invalid_grant"})
        token = jwt.encode(
            self.claims, self.signing_key, algorithm="RS256", headers={"kid": self.kid}
        )
        return httpx.Response(200, json={"id_token": token, "access_token": "x"})

    def prepare(self, location: str, **overrides: object) -> str:
        params = parse_qs(urlparse(location).query)
        self.expected_verifier_challenge = params["code_challenge"][0]
        now = int(time.time())
        self.claims = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": overrides.pop("sub", "google-sub-1"),
            "email": overrides.pop("email", "gina@example.com"),
            "email_verified": True,
            "name": "Gina Google",
            "nonce": params["nonce"][0],
            "iat": now,
            "exp": now + 600,
        }
        self.claims.update(overrides)
        return params["state"][0]


@pytest.fixture
def google(internet: FakeInternet) -> FakeGoogle:
    return FakeGoogle(internet)


async def _start(b: Browser, mode: str = "login") -> str:
    response = await b.client.get(f"/api/v1/auth/google/start?mode={mode}")
    assert response.status_code == 303, response.text
    location = response.headers["location"]
    params = parse_qs(urlparse(location).query)
    assert params["code_challenge_method"] == ["S256"]
    assert params["client_id"] == [CLIENT_ID]
    return location


async def _callback(b: Browser, state: str) -> httpx.Response:
    return await b.client.get(f"/api/v1/auth/google/callback?state={state}&code=auth-code")


async def test_google_sign_in_creates_verified_user(browser: Browser, google: FakeGoogle) -> None:
    state = google.prepare(await _start(browser), email="new-google@example.com", sub="sub-new")
    response = await _callback(browser, state)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/dashboard")
    session = (await browser.get("/api/v1/auth/session")).json()
    assert session["user"]["email"] == "new-google@example.com"
    assert session["user"]["email_verified"] is True
    assert session["user"]["google_linked"] is True
    assert session["user"]["has_password"] is False


async def test_state_is_single_use(browser: Browser, google: FakeGoogle) -> None:
    state = google.prepare(await _start(browser), sub="sub-replay", email="replay@example.com")
    assert (await _callback(browser, state)).headers["location"].endswith("/dashboard")
    replay = await _callback(browser, state)
    assert "error=google_failed" in replay.headers["location"]


async def test_state_bound_to_originating_browser(
    api_app: FastAPI, browser: Browser, google: FakeGoogle
) -> None:
    state = google.prepare(await _start(browser), sub="sub-csrf", email="csrf@example.com")
    async with make_client(api_app) as client:
        victim = Browser(client)
        await victim.refresh_csrf()
        response = await _callback(victim, state)  # attacker's state in victim's browser
    assert "error=google_failed" in response.headers["location"]
    assert "st_session" not in response.headers.get("set-cookie", "")


@pytest.mark.parametrize(
    "override",
    [
        {"email_verified": False},
        {"aud": "someone-else"},
        {"iss": "https://evil.example"},
        {"exp": int(time.time()) - 3600},
        {"nonce": "wrong-nonce"},
    ],
)
async def test_invalid_id_tokens_rejected(
    browser: Browser, google: FakeGoogle, override: dict[str, object]
) -> None:
    state = google.prepare(await _start(browser), sub=f"sub-{len(str(override))}", **override)
    response = await _callback(browser, state)
    assert "error=google_failed" in response.headers["location"]


async def test_bad_signature_rejected(browser: Browser, google: FakeGoogle) -> None:
    state = google.prepare(await _start(browser), sub="sub-sig", email="sig@example.com")
    # Token signed by an attacker key while Google's JWKS still publishes the real key.
    google.signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    response = await _callback(browser, state)
    assert "error=google_failed" in response.headers["location"]


async def test_existing_email_is_never_auto_linked(
    browser: Browser, google: FakeGoogle, outbox: MemoryEmailSender
) -> None:
    email = await register_and_verify(browser, outbox)
    state = google.prepare(await _start(browser), email=email, sub="sub-takeover")
    response = await _callback(browser, state)
    assert "error=google_account_exists" in response.headers["location"]


async def test_link_then_sign_in_with_google(
    api_app: FastAPI, google: FakeGoogle, outbox: MemoryEmailSender
) -> None:
    b, email = await signed_in_browser(api_app, outbox)
    state = google.prepare(await _start(b, "link"), email="other@gmail.com", sub="sub-linked")
    response = await _callback(b, state)
    assert response.headers["location"].endswith("/settings/security?linked=google")
    assert (await b.get("/api/v1/auth/session")).json()["user"]["google_linked"] is True
    async with make_client(api_app) as client:
        fresh = Browser(client)
        await fresh.refresh_csrf()
        state = google.prepare(await _start(fresh), email="other@gmail.com", sub="sub-linked")
        assert (await _callback(fresh, state)).headers["location"].endswith("/dashboard")
        assert (await fresh.get("/api/v1/auth/session")).json()["user"]["email"] == email
