"""Shared fixtures.

Integration tests need PostgreSQL and Redis. CI provides them as service containers
(``SERPTANK_TEST_DATABASE_URL`` / ``SERPTANK_TEST_REDIS_URL``); locally start
``docker compose -f docker-compose.dev.yml up -d`` and export the same variables.
Without them, integration tests are skipped locally but **fail** in CI.
"""

from __future__ import annotations

import asyncio
import os
import secrets as _secrets
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

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


# ---------------------------------------------------------------------------
# Database fixtures: a fresh, migrated database per test session.
# ---------------------------------------------------------------------------


BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_TEST_ROLE = "serptank_api_test"


@dataclass(frozen=True)
class DatabaseUrls:
    owner_url: str  # schema owner / superuser (seeding, migrations)
    app_url: str  # login role in serptank_app: subject to RLS like production


def _replace_db(url: str, db: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db}"


async def _prepare_cluster(admin_url: str, db_name: str, app_password: str) -> None:
    conn = await asyncpg.connect(admin_url)
    try:
        await conn.execute(
            """
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'serptank_app') THEN
                CREATE ROLE serptank_app NOLOGIN; END IF;
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'serptank_system') THEN
                CREATE ROLE serptank_system NOLOGIN BYPASSRLS; END IF;
            END $$;
            """
        )
        exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", APP_TEST_ROLE)
        verb = "ALTER" if exists else "CREATE"
        await conn.execute(f"{verb} ROLE {APP_TEST_ROLE} LOGIN PASSWORD '{app_password}'")
        await conn.execute(f"GRANT serptank_app TO {APP_TEST_ROLE}")
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()
    conn = await asyncpg.connect(_replace_db(admin_url, db_name))
    try:
        for ext in ("timescaledb", "citext", "pgcrypto", "vector"):
            await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
    finally:
        await conn.close()


async def _drop_database(admin_url: str, db_name: str) -> None:
    conn = await asyncpg.connect(admin_url)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
    finally:
        await conn.close()


def run_migrations(async_url: str, revision: str = "head", *, downgrade: bool = False) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = async_url
    if downgrade:
        command.downgrade(cfg, revision)
    else:
        command.upgrade(cfg, revision)


@pytest.fixture(scope="session")
def test_database() -> Iterator[DatabaseUrls]:
    admin = _service_url("SERPTANK_TEST_DATABASE_URL")
    if not admin:
        pytest.skip("PostgreSQL not configured (set SERPTANK_TEST_DATABASE_URL)")
    db_name = f"serptank_test_{_secrets.token_hex(4)}"
    app_password = _secrets.token_urlsafe(16)
    asyncio.run(_prepare_cluster(admin, db_name, app_password))
    owner_url = _async_db_url(_replace_db(admin, db_name))
    run_migrations(owner_url)
    user_host = admin.split("://", 1)[1].split("@", 1)[1]
    app_url = f"postgresql+asyncpg://{APP_TEST_ROLE}:{app_password}@{user_host}"
    yield DatabaseUrls(owner_url=owner_url, app_url=_replace_db(app_url, db_name))
    asyncio.run(_drop_database(admin, db_name))


@pytest.fixture
async def owner_engine(test_database: DatabaseUrls) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(test_database.owner_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def app_engine(test_database: DatabaseUrls) -> AsyncIterator[AsyncEngine]:
    # pool_size=1 makes connection reuse deterministic (GUC leak tests rely on it).
    engine = create_async_engine(test_database.app_url, pool_size=1, max_overflow=0)
    yield engine
    await engine.dispose()


@pytest.fixture
async def owner_session(owner_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(owner_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
async def app_session(app_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(app_engine, expire_on_commit=False) as session:
        yield session
