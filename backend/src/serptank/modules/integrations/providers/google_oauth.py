"""OAuth 2.0 for Google *data* access (Search Console, GA4, Google Ads).

Separate from "Sign in with Google": a different OAuth client, offline access (refresh
token) and incremental scopes. ``state`` + PKCE verifier live in Redis for 10 minutes,
bound to the organization and the user who started the flow, and are single use.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from redis.asyncio import Redis

from serptank.core.config import Settings
from serptank.core.crypto import generate_token
from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers.base import ProviderError, request_json

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
# Endpoint URL, not a credential.
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105  # nosec B105
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_TTL_S = 600

# Product feature -> OAuth scope. Requested incrementally when a feature is enabled.
SCOPES = {
    "gsc": "https://www.googleapis.com/auth/webmasters.readonly",
    "gsc_write": "https://www.googleapis.com/auth/webmasters",  # sitemap submission
    "ga4": "https://www.googleapis.com/auth/analytics.readonly",
    "ads": "https://www.googleapis.com/auth/adwords",
}
BASE_SCOPES = ("openid", "email")


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scopes: list[str]


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class GoogleDataOAuth:
    def __init__(self, settings: Settings, redis: Redis | None, http: SafeHttpClient) -> None:
        self.settings = settings
        self.redis = redis
        self.http = http

    @property
    def redirect_uri(self) -> str:
        return self.settings.public_origin.rstrip("/") + "/api/v1/integrations/google/callback"

    async def start(self, *, organization_id: str, user_id: str, features: list[str]) -> str:
        unknown = set(features) - set(SCOPES)
        if unknown or not features:
            raise ProviderError("google_bad_scope", "Unknown Google feature requested.")
        state = generate_token(24)
        verifier = generate_token(48)
        record = {
            "org": organization_id,
            "user": user_id,
            "verifier": verifier,
            "features": features,
        }
        if self.redis is None:
            raise RuntimeError("OAuth flows need Redis")
        await self.redis.set(f"gdata:state:{state}", json.dumps(record), ex=STATE_TTL_S)
        params = {
            "client_id": self.settings.google_data_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join([*BASE_SCOPES, *(SCOPES[f] for f in features)]),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
            "code_challenge": _challenge(verifier),
            "code_challenge_method": "S256",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def consume_state(self, state: str) -> dict[str, Any]:
        if self.redis is None:
            raise RuntimeError("OAuth flows need Redis")
        raw = await self.redis.getdel(f"gdata:state:{state}")
        if not raw:
            raise ProviderError(
                "google_state_invalid", "This Google authorization link expired. Please try again."
            )
        data: dict[str, Any] = json.loads(raw)
        return data

    async def exchange(self, code: str, verifier: str) -> TokenSet:
        data = await request_json(
            self.http,
            "POST",
            TOKEN_URL,
            provider="google",
            label="Google",
            form={
                "code": code,
                "client_id": self.settings.google_data_client_id,
                "client_secret": self.settings.google_data_client_secret.get_secret_value(),
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
        )
        return _tokens(data)

    async def refresh(self, refresh_token: str) -> TokenSet:
        try:
            data = await request_json(
                self.http,
                "POST",
                TOKEN_URL,
                provider="google",
                label="Google",
                form={
                    "refresh_token": refresh_token,
                    "client_id": self.settings.google_data_client_id,
                    "client_secret": self.settings.google_data_client_secret.get_secret_value(),
                    "grant_type": "refresh_token",
                },
            )
        except ProviderError as exc:
            if exc.code in {"google_request_failed", "google_unauthorized"}:
                # invalid_grant: the user revoked access or the token expired.
                raise ProviderError(
                    "google_reauth_required",
                    "Google access was revoked or expired. Reconnect your Google account.",
                    reauth=True,
                ) from exc
            raise
        return _tokens(data)

    async def account_email(self, access_token: str) -> str | None:
        data = await request_json(
            self.http,
            "GET",
            USERINFO_URL,
            provider="google",
            label="Google",
            headers={"authorization": f"Bearer {access_token}"},
        )
        email = data.get("email") if isinstance(data, dict) else None
        return str(email) if email else None

    async def revoke(self, token: str) -> None:
        # Already revoked or expired: disconnecting must still succeed.
        with contextlib.suppress(ProviderError):
            await request_json(
                self.http,
                "POST",
                REVOKE_URL,
                provider="google",
                label="Google",
                form={"token": token},
            )


def _tokens(data: Any) -> TokenSet:
    if not isinstance(data, dict) or not data.get("access_token"):
        raise ProviderError("google_bad_response", "Google returned no access token.")
    return TokenSet(
        access_token=str(data["access_token"]),
        refresh_token=str(data["refresh_token"]) if data.get("refresh_token") else None,
        expires_in=int(data.get("expires_in", 3600)),
        scopes=str(data.get("scope", "")).split(),
    )
