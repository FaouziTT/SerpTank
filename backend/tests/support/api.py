"""Shared API test harness (pytest plugin): the API runs as the RLS-restricted app role."""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.config import Environment, Settings
from serptank.core.crypto import Keyring
from serptank.core.email import MemoryEmailSender
from serptank.core.http import SafeHttpClient
from serptank.core.models import MemberRole
from serptank.main import create_app
from serptank.modules.identity.passwords import NoBreachChecker
from serptank.modules.tenancy.models import Membership, Organization
from serptank.workers.runtime import default_http_factory
from tests.conftest import DatabaseUrls, _service_url

ORIGIN = "http://localhost:3000"
STRONG_PASSWORD = "correct horse battery staple 42"

Handler = Callable[[httpx.Request], httpx.Response]


@dataclass
class FakeInternet:
    """Routes outbound requests (by Host) to in-test handlers."""

    handlers: dict[str, Handler] = field(default_factory=dict)
    requests: list[httpx.Request] = field(default_factory=list)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        handler = self.handlers.get(request.headers["host"])
        if handler is None:
            return httpx.Response(503)
        return handler(request)


async def _public_resolver(_host: str, _port: int) -> list[str]:
    return ["93.184.215.34"]


@pytest.fixture
def internet() -> FakeInternet:
    return FakeInternet()


@pytest.fixture
def outbox() -> MemoryEmailSender:
    return MemoryEmailSender()


@pytest.fixture
def api_settings(test_database: DatabaseUrls) -> Settings:
    redis = _service_url("SERPTANK_TEST_REDIS_URL")
    if not redis:
        pytest.skip("Redis not configured")
    return Settings(
        environment=Environment.TEST,
        database_url=SecretStr(test_database.app_url),
        redis_url=SecretStr(redis),
        public_origin=ORIGIN,
        allowed_hosts=["testserver", "localhost"],
        session_secret=SecretStr("s" * 40),
        csrf_secret=SecretStr("c" * 40),
        api_key_pepper=SecretStr("p" * 40),
        google_client_id="client-123.apps.googleusercontent.com",
        google_client_secret=SecretStr("google-secret"),
        webauthn_rp_id="localhost",
        encryption_keys=SecretStr(f"k1:{Keyring.generate_key()}"),
        encryption_active_key_id="k1",
        crawl_min_delay_s=0.0,
        google_data_client_id="data-client.apps.googleusercontent.com",
        google_data_client_secret=SecretStr("data-secret"),
        google_api_key=SecretStr("crux-key"),
        google_ads_developer_token=SecretStr("dev-token"),
        crawl_mobile_sample=3,
    )


@pytest.fixture
async def api_app(
    api_settings: Settings, internet: FakeInternet, outbox: MemoryEmailSender
) -> AsyncIterator[FastAPI]:
    app = create_app(api_settings)
    app.state.identity_overrides = {
        "email": outbox,
        "breach_checker": NoBreachChecker(),
        "http": SafeHttpClient(resolver=_public_resolver, transport=httpx.MockTransport(internet)),
    }
    # Crawls fetch through the same fake internet (never the real network in tests).
    app.state.jobs_overrides = {
        "http_factory": default_http_factory(_public_resolver, httpx.MockTransport(internet)),
        "email": outbox,
    }
    async with LifespanManager(app):
        await app.state.redis.flushdb()
        yield app


class Browser:
    """A cookie-keeping API client that behaves like the SerpTank frontend."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.csrf = ""

    async def refresh_csrf(self) -> str:
        response = await self.client.get("/api/v1/auth/csrf")
        assert response.status_code == 200
        self.csrf = response.json()["csrf_token"]
        return self.csrf

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Origin": ORIGIN, "X-CSRF-Token": self.csrf}
        headers.update(extra or {})
        return headers

    async def post(self, path: str, json: object = None, **kw: object) -> httpx.Response:
        response = await self.client.post(path, json=json, headers=self._headers(), **kw)  # type: ignore[arg-type]
        self._capture(response)
        return response

    async def delete(self, path: str) -> httpx.Response:
        response = await self.client.delete(path, headers=self._headers())
        self._capture(response)
        return response

    async def get(self, path: str, **kw: object) -> httpx.Response:
        return await self.client.get(path, **kw)  # type: ignore[arg-type]

    def _capture(self, response: httpx.Response) -> None:
        if response.content and response.headers.get("content-type", "").startswith(
            "application/json"
        ):
            body = response.json()
            if isinstance(body, dict) and "csrf_token" in body:
                self.csrf = body["csrf_token"]


def make_client(app: FastAPI, ip: str = "198.51.100.7") -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(ip, 4000), raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://localhost")


@pytest.fixture
async def browser(api_app: FastAPI) -> AsyncIterator[Browser]:
    async with make_client(api_app) as client:
        b = Browser(client)
        await b.refresh_csrf()
        yield b


def extract_token(text: str) -> str:
    match = re.search(r"token=([A-Za-z0-9_-]+)", text)
    assert match, text
    return match.group(1)


async def register_and_verify(
    browser: Browser, outbox: MemoryEmailSender, email: str | None = None
) -> str:
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = await browser.post(
        "/api/v1/auth/register",
        {"email": email, "password": STRONG_PASSWORD, "full_name": "Test User"},
    )
    assert response.status_code == 202, response.text
    token = extract_token(outbox.outbox[-1].text)
    assert (await browser.post("/api/v1/auth/verify-email", {"token": token})).status_code == 204
    return email


async def login(browser: Browser, email: str, password: str = STRONG_PASSWORD) -> httpx.Response:
    return await browser.post("/api/v1/auth/login", {"email": email, "password": password})


async def signed_in_browser(api_app: FastAPI, outbox: MemoryEmailSender) -> tuple[Browser, str]:
    client = make_client(api_app, ip=f"198.51.100.{uuid.uuid4().int % 200 + 1}")
    b = Browser(client)
    await b.refresh_csrf()
    email = await register_and_verify(b, outbox)
    assert (await login(b, email)).json()["status"] == "authenticated"
    return b, email


async def create_org_with_member(
    owner_session: AsyncSession, user_id: uuid.UUID, role: MemberRole, **org_kwargs: object
) -> uuid.UUID:
    org = Organization(
        name="Org", slug=f"org-{uuid.uuid4().hex[:8]}", created_by_user_id=user_id, **org_kwargs
    )
    owner_session.add(org)
    await owner_session.flush()
    owner_session.add(Membership(organization_id=org.id, user_id=user_id, role=role))
    await owner_session.commit()
    return org.id
