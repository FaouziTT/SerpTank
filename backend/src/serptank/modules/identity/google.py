"""Sign in with Google (OpenID Connect, Authorization Code + PKCE).

Fixes legacy finding H1 (OAuth login CSRF):

* ``state``, ``nonce`` and the PKCE ``code_verifier`` are generated server-side and
  stored in Redis for 10 minutes, **bound to the browser's pre-session**. The callback
  must come from the same browser, exactly once (the record is deleted on read).
* The ID token signature is verified against Google's JWKS; ``iss``, ``aud``, ``exp``,
  ``iat`` and ``nonce`` are checked, and ``email_verified`` must be true.
* Accounts are never merged automatically by email (see :mod:`.service`).
* All HTTP goes through :class:`SafeHttpClient`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import jwt
from redis.asyncio import Redis

from serptank.core.config import Settings
from serptank.core.crypto import constant_time_equals, generate_token
from serptank.core.errors import AppError
from serptank.core.http import EgressError, SafeHttpClient

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
# Endpoint URL, not a credential.
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105  # nosec B105
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_STATE_TTL_S = 600
_JWKS_TTL_S = 3600


class GoogleSignInError(AppError):
    status = 400
    code = "google_sign_in_failed"
    title = "Google sign-in failed"


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class GoogleOidcClient:
    def __init__(self, settings: Settings, redis: Redis, http: SafeHttpClient) -> None:
        self._settings = settings
        self._redis = redis
        self._http = http
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at = 0.0

    @property
    def redirect_uri(self) -> str:
        return self._settings.public_origin.rstrip("/") + "/api/v1/auth/google/callback"

    async def start(self, *, presession_key: str, mode: str, user_id: str | None) -> str:
        state = generate_token(24)
        nonce = generate_token(24)
        verifier = generate_token(48)
        record = {
            "nonce": nonce,
            "verifier": verifier,
            "presession": presession_key,
            "mode": mode,
            "user_id": user_id,
        }
        await self._redis.set(f"oidc:{state}", json.dumps(record), ex=_STATE_TTL_S)
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def complete(
        self, *, state: str, code: str, presession_key: str
    ) -> tuple[GoogleIdentity, dict[str, Any]]:
        raw = await self._redis.getdel(f"oidc:{state}") if state else None
        if not raw:
            raise GoogleSignInError("The sign-in request expired or was already used.")
        record: dict[str, Any] = json.loads(raw)
        if not presession_key or not constant_time_equals(record["presession"], presession_key):
            raise GoogleSignInError("The sign-in request did not start in this browser.")
        id_token = await self._exchange_code(code, record["verifier"])
        claims = await self._verify_id_token(id_token, record["nonce"])
        if claims.get("email_verified") is not True or not claims.get("email"):
            raise GoogleSignInError("Your Google account email is not verified.")
        identity = GoogleIdentity(
            subject=str(claims["sub"]),
            email=str(claims["email"]).lower(),
            name=str(claims.get("name") or ""),
        )
        return identity, record

    async def _exchange_code(self, code: str, verifier: str) -> str:
        body = urlencode(
            {
                "code": code,
                "client_id": self._settings.google_client_id,
                "client_secret": self._settings.google_client_secret.get_secret_value(),
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            }
        ).encode()
        try:
            response = await self._http.request(
                "POST",
                TOKEN_URL,
                headers={"content-type": "application/x-www-form-urlencoded"},
                content=body,
            )
        except EgressError as exc:
            raise GoogleSignInError("Could not reach Google. Please try again.") from exc
        if response.status_code != 200:  # noqa: PLR2004
            raise GoogleSignInError("Google rejected the sign-in request.")
        try:
            token = json.loads(response.content)["id_token"]
        except (ValueError, KeyError) as exc:
            raise GoogleSignInError("Google returned an invalid response.") from exc
        return str(token)

    async def _signing_key(self, kid: str) -> jwt.PyJWK:
        for force in (False, True):
            jwks = await self._load_jwks(force=force)
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    return jwt.PyJWK(key)
        raise GoogleSignInError("Unknown Google signing key.")

    async def _load_jwks(self, *, force: bool) -> dict[str, Any]:
        fresh = time.time() - self._jwks_fetched_at < _JWKS_TTL_S
        if self._jwks is not None and fresh and not force:
            return self._jwks
        try:
            response = await self._http.get(JWKS_URL)
            self._jwks = json.loads(response.content)
        except (EgressError, ValueError) as exc:
            raise GoogleSignInError("Could not verify the Google sign-in.") from exc
        self._jwks_fetched_at = time.time()
        return self._jwks

    async def _verify_id_token(self, id_token: str, nonce: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError as exc:
            raise GoogleSignInError("Invalid Google ID token.") from exc
        key = await self._signing_key(str(header.get("kid", "")))
        try:
            claims: dict[str, Any] = jwt.decode(
                id_token,
                key=key,
                algorithms=["RS256"],
                audience=self._settings.google_client_id,
                issuer=list(ISSUERS),
                leeway=60,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise GoogleSignInError("Invalid Google ID token.") from exc
        if not constant_time_equals(str(claims.get("nonce", "")), nonce):
            raise GoogleSignInError("Invalid Google ID token.")
        return claims
