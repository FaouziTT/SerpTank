"""Shared fixtures.

Integration tests need PostgreSQL and Redis. CI provides them as service containers
(``SERPTANK_TEST_DATABASE_URL`` / ``SERPTANK_TEST_REDIS_URL``); locally start
``docker compose -f docker-compose.dev.yml up -d`` and export the same variables.
Without them, integration tests are skipped locally but **fail** in CI.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from pydantic import SecretStr

from serptank.core.config import Environment, Settings
from serptank.main import create_app


def _service_url(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if os.environ.get("CI"):
        pytest.fail(f"{name} must be set in CI")
    return None


def _async_db_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.fixture
def settings() -> Settings:
    db = _service_url("SERPTANK_TEST_DATABASE_URL") or "postgresql://u:p@127.0.0.1:1/none"
    redis = _service_url("SERPTANK_TEST_REDIS_URL") or "redis://127.0.0.1:1/0"
    return Settings(
        environment=Environment.TEST,
        log_json=True,
        database_url=SecretStr(_async_db_url(db)),
        redis_url=SecretStr(redis),
        public_origin="http://localhost:3000",
        allowed_hosts=["testserver", "localhost"],
    )


@pytest.fixture
def services_available() -> None:
    if not (_service_url("SERPTANK_TEST_DATABASE_URL") and _service_url("SERPTANK_TEST_REDIS_URL")):
        pytest.skip("PostgreSQL/Redis not configured (set SERPTANK_TEST_* env vars)")


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with LifespanManager(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(
        app=app, client=("203.0.113.10", 5000), raise_app_exceptions=False
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
