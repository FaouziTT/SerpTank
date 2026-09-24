"""Redis-backed rate limiting using GCRA (generic cell rate algorithm).

GCRA gives smooth limits with bursts up to ``limit`` and needs one key per subject.
The whole check-and-update runs in a single Lua script, so it is atomic under
concurrency and across API replicas.

Subjects are built by the caller (per IP for anonymous routes, per user/org/API key for
authenticated ones). The client IP comes from ``request.client`` which, behind Caddy,
is set by uvicorn's proxy-headers middleware **only for trusted proxies** - we never read
``X-Forwarded-For`` directly (the legacy limiter could be bypassed by spoofing it).
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request
from redis.asyncio import Redis

from serptank.core.errors import RateLimitedError

_GCRA_LUA = """
local key = KEYS[1]
local emission = tonumber(ARGV[1])      -- ms per request
local burst = tonumber(ARGV[2])         -- ms of tolerated burst
local now = tonumber(ARGV[3])           -- ms
local tat = tonumber(redis.call('GET', key) or now)
if tat < now then tat = now end
local new_tat = tat + emission
local allow_at = new_tat - burst
if allow_at > now then
  return {0, allow_at - now, 0}
end
redis.call('SET', key, new_tat, 'PX', math.ceil(new_tat - now))
local remaining = math.floor((burst - (new_tat - now)) / emission)
return {1, 0, remaining}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_s: int
    remaining: int


@dataclass(frozen=True)
class Rate:
    """``limit`` requests per ``period_s`` seconds (bursts up to ``limit``)."""

    limit: int
    period_s: int

    def __str__(self) -> str:
        return f"{self.limit};w={self.period_s}"


class RateLimiter:
    def __init__(self, redis: Redis, *, prefix: str = "rl") -> None:
        self._redis = redis
        self._prefix = prefix
        self._script = redis.register_script(_GCRA_LUA)

    async def hit(self, bucket: str, subject: str, rate: Rate) -> RateLimitResult:
        emission_ms = rate.period_s * 1000 / rate.limit
        burst_ms = rate.period_s * 1000
        now_ms = int(await self._now_ms())
        allowed, retry_ms, remaining = await self._script(
            keys=[f"{self._prefix}:{bucket}:{subject}"],
            args=[emission_ms, burst_ms, now_ms],
        )
        return RateLimitResult(
            allowed=bool(int(allowed)),
            retry_after_s=max(1, math.ceil(float(retry_ms) / 1000)) if not int(allowed) else 0,
            remaining=max(0, int(remaining)),
        )

    async def _now_ms(self) -> float:
        # Use Redis server time so all API replicas agree on "now".
        seconds, micros = await self._redis.time()
        return seconds * 1000 + micros / 1000


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


SubjectFn = Callable[[Request], Awaitable[str] | str]


def rate_limit(
    bucket: str, *rates: Rate, subject: SubjectFn = client_ip
) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency factory enforcing one or more rates on a route.

    Example::

        @router.post("/login", dependencies=[Depends(rate_limit("login", Rate(5, 60)))])
    """

    async def dependency(request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        subject_value = subject(request)
        if not isinstance(subject_value, str):
            subject_value = await subject_value
        for rate in rates:
            result = await limiter.hit(f"{bucket}:{rate.period_s}", subject_value, rate)
            if not result.allowed:
                raise RateLimitedError(
                    "Too many requests. Please retry later.",
                    headers={
                        "Retry-After": str(result.retry_after_s),
                        "RateLimit-Policy": str(rate),
                    },
                )

    return dependency
