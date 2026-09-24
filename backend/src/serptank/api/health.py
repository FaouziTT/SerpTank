"""Liveness and readiness probes (unauthenticated, no sensitive data).

* ``/healthz`` - the process is up (used by Docker/Caddy to restart hung containers).
* ``/readyz``  - dependencies (PostgreSQL, Redis) answer within a short deadline; used to
  keep traffic away from an instance that cannot serve requests.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from serptank import __version__
from serptank.core.errors import ServiceUnavailableError

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)
_CHECK_TIMEOUT_S = 2.0


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


async def _check_database(request: Request) -> None:
    async with request.app.state.engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _check_redis(request: Request) -> None:
    await request.app.state.redis.ping()


@router.get("/readyz", response_model=ReadinessResponse)
async def readyz(request: Request) -> ReadinessResponse:
    checks: dict[str, str] = {}
    for name, check in (("database", _check_database), ("redis", _check_redis)):
        try:
            async with asyncio.timeout(_CHECK_TIMEOUT_S):
                await check(request)
            checks[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
            logger.warning("readiness_check_failed", check=name, error=type(exc).__name__)
            checks[name] = "unavailable"
    if any(v != "ok" for v in checks.values()):
        raise ServiceUnavailableError(
            "One or more dependencies are unavailable.", extra={"checks": checks}
        )
    return ReadinessResponse(status="ok", checks=checks)
