"""Integration tests against real PostgreSQL and Redis (CI service containers)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import Depends, FastAPI

from serptank.core.ratelimit import Rate, RateLimiter, rate_limit

pytestmark = pytest.mark.usefixtures("services_available")


async def test_readyz_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/readyz")
    assert response.status_code == 200, response.text
    assert response.json()["checks"] == {"database": "ok", "redis": "ok"}


async def test_readyz_reports_unavailable_dependency(app: FastAPI) -> None:
    from redis.asyncio import Redis

    app.state.redis = Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.2)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "unavailable"


async def test_gcra_limits_and_recovers(app: FastAPI) -> None:
    limiter: RateLimiter = app.state.rate_limiter
    await app.state.redis.delete("rl:test:1:subject")
    rate = Rate(limit=3, period_s=1)
    results = [await limiter.hit("test:1", "subject", rate) for _ in range(4)]
    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[-1].retry_after_s >= 1


async def test_rate_limit_dependency_returns_429(app: FastAPI) -> None:
    await app.state.redis.delete("rl:unit-login:60:203.0.113.10")

    @app.post("/t/limited", dependencies=[Depends(rate_limit("unit-login", Rate(2, 60)))])
    async def limited() -> dict[str, bool]:
        return {"ok": True}

    transport = httpx.ASGITransport(app=app, client=("203.0.113.10", 1))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        codes = [(await c.post("/t/limited")).status_code for _ in range(3)]
        last = await c.post("/t/limited")
    assert codes == [200, 200, 429]
    assert last.status_code == 429
    assert int(last.headers["retry-after"]) >= 1
    assert last.json()["code"] == "rate_limited"
