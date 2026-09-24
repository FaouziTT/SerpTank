"""HTTP-level behaviour of the platform core (no database or Redis needed)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from serptank.core.errors import NotFoundError


class Payload(BaseModel):
    name: str


def _attach_test_routes(app: FastAPI) -> None:
    router = APIRouter()

    @router.get("/t/missing")
    async def missing() -> None:
        raise NotFoundError("Project not found.")

    @router.get("/t/boom")
    async def boom() -> None:
        msg = "database password=hunter2 at 10.0.0.5"
        raise RuntimeError(msg)

    @router.post("/t/echo")
    async def echo(payload: Payload) -> Payload:
        return payload

    app.include_router(router)


@pytest.fixture
async def test_client(app: FastAPI, client: httpx.AsyncClient) -> httpx.AsyncClient:
    _attach_test_routes(app)
    return client


async def test_healthz(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"]


async def test_security_headers_present(client: httpx.AsyncClient) -> None:
    headers = (await client.get("/healthz")).headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["cache-control"] == "no-store"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "strict-transport-security" not in headers  # http dev origin


async def test_unknown_route_is_problem_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "not_found"
    assert body["type"].endswith("/not_found")
    assert body["trace_id"] == response.headers["x-request-id"]


async def test_app_error(test_client: httpx.AsyncClient) -> None:
    body = (await test_client.get("/t/missing")).json()
    assert body["status"] == 404
    assert body["detail"] == "Project not found."


async def test_unhandled_exception_never_leaks(test_client: httpx.AsyncClient) -> None:
    response = await test_client.get("/t/boom")
    assert response.status_code == 500
    text = response.text
    assert "hunter2" not in text
    assert "10.0.0.5" not in text
    assert "RuntimeError" not in text
    assert response.json()["code"] == "internal_error"


async def test_validation_error_does_not_echo_input(test_client: httpx.AsyncClient) -> None:
    response = await test_client.post("/t/echo", json={"name": {"evil": "<script>"}})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_failed"
    assert body["errors"][0]["field"] == "name"
    assert "<script>" not in response.text


async def test_untrusted_host_rejected(app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://evil.com") as c:
        assert (await c.get("/healthz")).status_code == 400


async def test_body_size_limit(test_client: httpx.AsyncClient) -> None:
    response = await test_client.post(
        "/t/echo", content=b"x" * 2_000_000, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Referer": "https://evil.example/page"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
async def test_csrf_rejects_cross_origin_unsafe_requests(
    test_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    response = await test_client.post("/t/echo", json={"name": "a"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"


async def test_csrf_allows_same_origin_and_non_browser(test_client: httpx.AsyncClient) -> None:
    same = await test_client.post(
        "/t/echo", json={"name": "a"}, headers={"Origin": "http://localhost:3000"}
    )
    assert same.status_code == 200
    api_client = await test_client.post("/t/echo", json={"name": "a"})
    assert api_client.status_code == 200


async def test_docs_available_in_test_env(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/openapi.json")).status_code == 200


async def test_docs_disabled_in_production() -> None:
    from pydantic import SecretStr

    from serptank.core.config import Environment, Settings
    from serptank.core.crypto import Keyring
    from serptank.main import create_app

    settings = Settings(
        environment=Environment.PRODUCTION,
        public_origin="https://app.serptank.com",
        allowed_hosts=["testserver"],
        session_secret=SecretStr("s" * 40),
        csrf_secret=SecretStr("c" * 40),
        api_key_pepper=SecretStr("p" * 40),
        encryption_keys=SecretStr(f"k1:{Keyring.generate_key()}"),
        encryption_active_key_id="k1",
    )
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        assert (await c.get("/api/v1/openapi.json")).status_code == 404
        assert (await c.get("/api/v1/docs")).status_code == 404
        response = await c.get("/healthz")
        assert "max-age=" in response.headers["strict-transport-security"]
