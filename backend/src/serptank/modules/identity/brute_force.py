"""Login brute-force protection without account lockout (OWASP A07:2025).

Layers:

1. **Per IP** limits on every login attempt (stops single-source spraying).
2. **Per account** failure counter (15-minute window, keyed by a hash of the email).
   After ``CAPTCHA_AFTER`` failures, a CAPTCHA is required when Turnstile is configured;
   otherwise attempts for that *account from that IP* are throttled. Throttling is per
   (account, IP) so an attacker cannot lock a victim out from everywhere.
3. **Progressive delay** after a few failures slows automated guessing further.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Protocol
from urllib.parse import urlencode

import structlog
from redis.asyncio import Redis

from serptank.core.errors import AppError, RateLimitedError
from serptank.core.http import EgressError, SafeHttpClient
from serptank.core.ratelimit import Rate, RateLimiter

logger = structlog.get_logger(__name__)

CAPTCHA_AFTER = 5
_WINDOW_S = 15 * 60
_IP_RATES = (Rate(20, 60), Rate(200, 3600))
_ACCOUNT_IP_RATE = Rate(5, _WINDOW_S)
_TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class CaptchaRequiredError(AppError):
    status = 400
    code = "captcha_required"
    title = "Please complete the security check"


class CaptchaVerifier(Protocol):
    enabled: bool

    async def verify(self, token: str, remote_ip: str | None) -> bool: ...


class DisabledCaptcha:
    enabled = False

    async def verify(self, token: str, remote_ip: str | None) -> bool:
        return False


class TurnstileVerifier:
    enabled = True

    def __init__(self, http: SafeHttpClient, secret: str) -> None:
        self._http = http
        self._secret = secret

    async def verify(self, token: str, remote_ip: str | None) -> bool:
        body = {"secret": self._secret, "response": token}
        if remote_ip:
            body["remoteip"] = remote_ip
        try:
            response = await self._http.request(
                "POST",
                _TURNSTILE_URL,
                headers={"content-type": "application/x-www-form-urlencoded"},
                content=urlencode(body).encode(),
            )
        except EgressError as exc:
            logger.warning("turnstile_unavailable", error=type(exc).__name__)
            return False
        try:
            return bool(json.loads(response.content).get("success"))
        except ValueError:
            return False


def _account_key(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]


class LoginThrottle:
    def __init__(self, redis: Redis, limiter: RateLimiter, captcha: CaptchaVerifier) -> None:
        self._redis = redis
        self._limiter = limiter
        self._captcha = captcha

    async def before_attempt(self, email: str, ip: str, captcha_token: str | None) -> None:
        for rate in _IP_RATES:
            result = await self._limiter.hit(f"login-ip:{rate.period_s}", ip, rate)
            if not result.allowed:
                raise RateLimitedError(
                    "Too many sign-in attempts. Please wait and try again.",
                    headers={"Retry-After": str(result.retry_after_s)},
                )
        failures = await self.failures(email)
        if failures < CAPTCHA_AFTER:
            return
        if self._captcha.enabled:
            if not captcha_token or not await self._captcha.verify(captcha_token, ip):
                raise CaptchaRequiredError(extra={"captcha": "turnstile"})
        else:
            result = await self._limiter.hit(
                "login-acct-ip", f"{_account_key(email)}:{ip}", _ACCOUNT_IP_RATE
            )
            if not result.allowed:
                raise RateLimitedError(
                    "Too many failed sign-in attempts. Please wait and try again.",
                    headers={"Retry-After": str(result.retry_after_s)},
                )
        # Progressive delay: 0.5s, 1s, 2s ... capped at 4s.
        await asyncio.sleep(min(4.0, 0.5 * 2 ** (failures - CAPTCHA_AFTER)))

    async def failures(self, email: str) -> int:
        value = await self._redis.get(f"lf:{_account_key(email)}")
        return int(value) if value else 0

    async def record_failure(self, email: str) -> None:
        key = f"lf:{_account_key(email)}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, _WINDOW_S)
            await pipe.execute()

    async def record_success(self, email: str) -> None:
        await self._redis.delete(f"lf:{_account_key(email)}")
