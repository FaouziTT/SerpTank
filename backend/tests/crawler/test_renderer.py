"""The isolated renderer: real headless Chromium, every request through SafeHttpClient."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from asgi_lifespan import LifespanManager
from pydantic import SecretStr

from serptank.core.config import Environment, Settings
from serptank.core.http import SafeHttpClient
from serptank.modules.crawler.rendering import RendererClient, render_summary
from serptank.modules.crawler.robots import parse_robots
from serptank.renderer.app import create_app
from serptank.renderer.browser import Renderer, RenderLimits

# A local Chromium build (e.g. this sandbox's), or Playwright's own browser when CI ran
# `playwright install chromium` and set SERPTANK_TEST_RENDERER=1.
_LOCAL = os.environ.get(
    "SERPTANK_TEST_CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
)
CHROMIUM = _LOCAL if Path(_LOCAL).exists() else None
pytestmark = pytest.mark.skipif(
    CHROMIUM is None and os.environ.get("SERPTANK_TEST_RENDERER") != "1",
    reason="Chromium not available",
)

HOME = """<!doctype html><html><head><title>Raw title</title>
<script src="/app.js" defer></script><link rel="stylesheet" href="/blocked/style.css"></head>
<body><div id="x">raw</div><a href="/raw-link">raw</a>
<img src="http://169.254.169.254/latest/meta-data/">
<img src="http://127.0.0.1:6379/">
</body></html>"""
APP_JS = """
document.title = 'Rendered title';
document.getElementById('x').textContent = 'hello from javascript ' + 'word '.repeat(80);
const a = document.createElement('a');
a.href = '/js-link'; a.textContent = 'js'; document.body.appendChild(a);
fetch('/api/data').then(r => r.text()).then(t => {
  document.body.insertAdjacentHTML('beforeend', '<p id=api>' + t + '</p>');
});
try { new WebSocket('wss://site.example.com/ws'); } catch (e) {}
"""


def site(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/":
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HOME)
    if path == "/app.js":
        return httpx.Response(200, headers={"content-type": "application/javascript"}, text=APP_JS)
    if path == "/api/data":
        return httpx.Response(200, headers={"content-type": "text/plain"}, text="api-payload")
    if path == "/blocked/style.css":
        return httpx.Response(200, headers={"content-type": "text/css"}, text="body{}")
    if path == "/slow":
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<script>while(true){}</script>"
        )
    return httpx.Response(404)


async def resolver(host: str, _port: int) -> list[str]:
    return ["93.184.215.34"]


@pytest.fixture
async def renderer() -> AsyncIterator[Renderer]:
    http = SafeHttpClient(resolver=resolver, transport=httpx.MockTransport(site))
    instance = Renderer(http, executable_path=CHROMIUM, limits=RenderLimits(timeout_s=8))
    await instance.start()
    try:
        yield instance
    finally:
        await instance.stop()
        await http.aclose()


async def test_render_runs_js_and_blocks_internal_addresses(renderer: Renderer) -> None:
    result = await renderer.render("https://site.example.com/", user_agent="SerpTankBot/1.0")
    assert result.status == 200
    assert "<title>Rendered title</title>" in result.html
    assert "api-payload" in result.html
    by_url = {r.url: r for r in result.requests}
    assert by_url["http://169.254.169.254/latest/meta-data/"].blocked == "policy"
    # Port 6379 is refused by policy too (only 80/443 are allowed).
    assert by_url["http://127.0.0.1:6379/"].blocked == "policy"
    assert by_url["https://site.example.com/app.js"].status == 200

    robots = {"site.example.com": parse_robots("User-agent: Googlebot\nDisallow: /blocked/\n")}
    summary = render_summary(
        "https://site.example.com/",
        {"https://site.example.com/raw-link"},
        result.to_json(),
        robots,
        frozenset({"site.example.com"}),
    )
    assert summary["failed"] is False
    assert summary["title"] == "Rendered title"
    assert summary["js_only_links"] == 1
    assert summary["js_only_examples"] == ["https://site.example.com/js-link"]
    assert summary["blocked_for_google"] == ["https://site.example.com/blocked/style.css"]
    assert summary["word_count"] > 80


async def test_render_timeout_is_reported(renderer: Renderer) -> None:
    renderer.limits = RenderLimits(timeout_s=2)
    result = await renderer.render("https://site.example.com/slow", user_agent="SerpTankBot/1.0")
    summary = render_summary(
        "https://site.example.com/slow", set(), result.to_json(), {}, frozenset()
    )
    assert summary["failed"] is True


def test_render_summary_without_renderer() -> None:
    assert render_summary("https://x.com/", set(), None, {}, frozenset()) == {
        "failed": True,
        "reason": "renderer_unavailable",
    }


async def test_renderer_service_requires_token(renderer: Renderer) -> None:
    settings = Settings(environment=Environment.TEST, renderer_token=SecretStr("t" * 40))
    app = create_app(settings, renderer=renderer)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://renderer") as raw:
            assert (await raw.get("/healthz")).json() == {"status": "ok"}
            body = {"url": "https://site.example.com/", "user_agent": "SerpTankBot"}
            assert (await raw.post("/render", json=body)).status_code == 401
            wrong = await raw.post("/render", json=body, headers={"authorization": "Bearer nope"})
            assert wrong.status_code == 401
            bad = await raw.post(
                "/render",
                json={"url": "file:///etc/passwd", "user_agent": "x"},
                headers={"authorization": "Bearer " + "t" * 40},
            )
            assert bad.status_code == 422
            extra = await raw.post(
                "/render", json={**body, "evil": 1}, headers={"authorization": "Bearer " + "t" * 40}
            )
            assert extra.status_code == 422
            client = RendererClient("http://renderer", "t" * 40, client=raw)
            rendered = await client.render("https://site.example.com/", user_agent="SerpTankBot")
            assert rendered is not None
            assert "Rendered title" in rendered["html"]
            unauthorised = RendererClient("http://renderer", "wrong", client=raw)
            assert await unauthorised.render("https://site.example.com/", user_agent="x") is None


async def test_renderer_client_handles_outage() -> None:
    def down(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = RendererClient(
        "http://renderer", "t", client=httpx.AsyncClient(transport=httpx.MockTransport(down))
    )
    assert await client.render("https://x.com/", user_agent="x") is None
    await client.aclose()
