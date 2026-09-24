"""Server-side browser sessions (the only browser authentication mechanism).

Design (docs/execution-plan.md §5.1):

* The cookie holds an opaque 256-bit random token. Redis stores the session under
  ``HMAC(token, session_secret)``, so a Redis dump cannot be replayed as cookies.
* Cookie: ``__Host-st_session`` (Secure, HttpOnly, SameSite=Lax, Path=/, no Domain) in
  HTTPS deployments; ``st_session`` on plain-HTTP localhost development.
* Idle timeout and absolute lifetime are both enforced server-side.
* A new token is issued (and the old one destroyed) on login, MFA completion and
  privilege changes - session fixation is impossible.
* ``usess:<user_id>`` indexes a user's sessions for listing and O(n-sessions)
  "log out everywhere" (the legacy code SCANned every session in Redis).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from redis.asyncio import Redis
from starlette.responses import Response

from serptank.core.config import Settings
from serptank.core.crypto import generate_token, hash_token

_TOUCH_INTERVAL_S = 60


def session_cookie_name(settings: Settings) -> str:
    return "__Host-st_session" if settings.cookie_secure else "st_session"


def presession_cookie_name(settings: Settings) -> str:
    return "__Host-st_pre" if settings.cookie_secure else "st_pre"


@dataclass
class SessionData:
    user_id: str
    created_at: float
    last_seen_at: float
    absolute_expires_at: float
    remember: bool = False
    # True between a correct password and a completed second factor. Such a session
    # can only call the MFA verification endpoints.
    mfa_pending: bool = False
    reauth_at: float | None = None
    auth_methods: list[str] = field(default_factory=list)
    ip: str | None = None
    user_agent: str | None = None
    # Populated when loaded; never persisted.
    key: str = ""

    @property
    def public_id(self) -> str:
        """Identifier safe to show in the UI (a prefix of the storage key, not the token)."""
        return self.key[:16]

    @property
    def user_uuid(self) -> uuid.UUID:
        return uuid.UUID(self.user_id)

    def recently_reauthenticated(self, window_s: int, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        return self.reauth_at is not None and now - self.reauth_at <= window_s


class SessionStore:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self._redis = redis
        self._settings = settings
        self._pepper = settings.session_secret.get_secret_value()

    def _key(self, token: str) -> str:
        return hash_token(token, pepper=self._pepper)

    def _ttl(self, data: SessionData, now: float) -> int:
        remaining = data.absolute_expires_at - now
        return max(1, int(min(self._settings.session_idle_timeout_s, remaining)))

    async def _save(self, data: SessionData, now: float) -> None:
        payload = {k: v for k, v in asdict(data).items() if k != "key"}
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(f"sess:{data.key}", json.dumps(payload), ex=self._ttl(data, now))
            pipe.sadd(f"usess:{data.user_id}", data.key)
            pipe.expire(f"usess:{data.user_id}", self._settings.session_remember_absolute_timeout_s)
            await pipe.execute()

    async def create(
        self,
        user_id: uuid.UUID,
        *,
        remember: bool = False,
        mfa_pending: bool = False,
        auth_methods: list[str] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, SessionData]:
        now = time.time()
        lifetime = (
            self._settings.session_remember_absolute_timeout_s
            if remember
            else self._settings.session_absolute_timeout_s
        )
        token = generate_token(32)
        data = SessionData(
            user_id=str(user_id),
            created_at=now,
            last_seen_at=now,
            absolute_expires_at=now + lifetime,
            remember=remember,
            mfa_pending=mfa_pending,
            auth_methods=auth_methods or [],
            ip=ip,
            user_agent=(user_agent or "")[:200] or None,
            key=self._key(token),
        )
        await self._save(data, now)
        return token, data

    async def get(self, token: str) -> SessionData | None:
        if not token or len(token) > 128:  # noqa: PLR2004
            return None
        key = self._key(token)
        raw = await self._redis.get(f"sess:{key}")
        if raw is None:
            return None
        data = self._load(key, str(raw))
        now = time.time()
        if data is None or now >= data.absolute_expires_at:
            await self.revoke_key(key, data.user_id if data else None)
            return None
        if now - data.last_seen_at >= _TOUCH_INTERVAL_S:
            data.last_seen_at = now
            await self._save(data, now)
        return data

    @staticmethod
    def _load(key: str, raw: str) -> SessionData | None:
        try:
            values: dict[str, Any] = json.loads(raw)
            return SessionData(**values, key=key)
        except (TypeError, ValueError):
            return None

    async def update(self, data: SessionData) -> None:
        await self._save(data, time.time())

    async def rotate(self, data: SessionData, **changes: Any) -> tuple[str, SessionData]:
        """Replace the session with a fresh token (anti-fixation), applying ``changes``."""
        await self.revoke_key(data.key, data.user_id)
        token = generate_token(32)
        values = {k: v for k, v in asdict(data).items() if k != "key"}
        values.update(changes)
        new = SessionData(**values, key=self._key(token))
        await self._save(new, time.time())
        return token, new

    async def revoke_key(self, key: str, user_id: str | None) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(f"sess:{key}")
            if user_id:
                pipe.srem(f"usess:{user_id}", key)
            await pipe.execute()

    async def list_for_user(self, user_id: uuid.UUID) -> list[SessionData]:
        keys = {str(k) for k in await self._redis.smembers(f"usess:{user_id}")}
        sessions: list[SessionData] = []
        for key in keys:
            raw = await self._redis.get(f"sess:{key}")
            data = self._load(key, str(raw)) if raw else None
            if data is None or time.time() >= data.absolute_expires_at:
                await self._redis.srem(f"usess:{user_id}", key)
                continue
            sessions.append(data)
        return sorted(sessions, key=lambda s: s.last_seen_at, reverse=True)

    async def revoke_all(self, user_id: uuid.UUID, *, except_key: str | None = None) -> int:
        keys = {str(k) for k in await self._redis.smembers(f"usess:{user_id}")}
        revoked = 0
        for key in keys:
            if key == except_key:
                continue
            await self.revoke_key(key, str(user_id))
            revoked += 1
        return revoked


def set_session_cookie(
    response: Response, settings: Settings, token: str, data: SessionData
) -> None:
    max_age = int(data.absolute_expires_at - time.time()) if data.remember else None
    response.set_cookie(
        session_cookie_name(settings),
        token,
        max_age=max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        session_cookie_name(settings),
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
