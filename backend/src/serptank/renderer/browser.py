"""Render a page like Googlebot's Web Rendering Service would, without trusting Chromium.

Security model (the renderer is the riskiest component, plan §4.1/§5.5):

* **Chromium never talks to the network.** Every request the page makes is intercepted
  (``page.route``) and fetched by :class:`SafeHttpClient`, which resolves DNS itself,
  blocks private/loopback/metadata addresses, pins the IP and caps size and time. Redirects
  go back through Chromium and are intercepted again, so every hop is checked.
* Belt and braces: Chromium is launched with a black-hole proxy, so anything that escaped
  interception would fail to connect. WebSockets are refused, service workers blocked,
  downloads disabled, dialogs dismissed.
* Per render: a fresh browser context (no shared cookies/storage), a request cap, a byte
  cap and a wall-clock timeout.
* Only the resulting HTML and request metadata leave the renderer; nothing it fetched
  is ever shown to users as HTML.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog
from playwright.async_api import (
    Browser,
    Page,
    Playwright,
    Request,
    Route,
    ViewportSize,
    async_playwright,
)

from serptank.core.http import EgressError, EgressPolicy, EgressPolicyError, SafeHttpClient

logger = structlog.get_logger(__name__)

RESOURCE_POLICY = EgressPolicy(
    follow_redirects=False, max_response_bytes=8 * 1024 * 1024, total_timeout_s=15
)
_DROP_HEADERS = frozenset(
    {"content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive"}
)
DESKTOP_VIEWPORT = ViewportSize(width=1366, height=900)
MOBILE_VIEWPORT = ViewportSize(width=412, height=915)


@dataclass
class RenderLimits:
    timeout_s: float = 25.0
    max_requests: int = 250
    max_total_bytes: int = 40 * 1024 * 1024


@dataclass
class RenderedRequest:
    url: str
    resource_type: str
    status: int | None
    blocked: str | None = None  # why we refused it (policy, limit, network)


@dataclass
class RenderResult:
    url: str
    status: int | None
    html: str
    requests: list[RenderedRequest] = field(default_factory=list)
    timed_out: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "html": self.html,
            "timed_out": self.timed_out,
            "requests": [r.__dict__ for r in self.requests],
        }


class Renderer:
    def __init__(
        self,
        http: SafeHttpClient,
        *,
        executable_path: str | None = None,
        limits: RenderLimits | None = None,
        concurrency: int = 2,
    ) -> None:
        self.http = http
        self.executable_path = executable_path or None
        self.limits = limits or RenderLimits()
        self._semaphore = asyncio.Semaphore(concurrency)
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            executable_path=self.executable_path,
            # Nothing may reach the network directly: all traffic is intercepted.
            proxy={"server": "http://127.0.0.1:9"},
            args=[
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-domain-reliability",
                "--disable-sync",
                "--no-first-run",
                "--no-default-browser-check",
                "--metrics-recording-only",
                "--mute-audio",
            ],
        )

    async def _restart(self) -> None:
        browser, self._browser = self._browser, None
        if browser is not None:
            try:
                await asyncio.wait_for(browser.close(), timeout=5)
            except TimeoutError:
                logger.error("render_browser_close_failed")
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        await self.start()

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def render(self, url: str, *, user_agent: str, mobile: bool = False) -> RenderResult:
        if self._browser is None:
            raise RuntimeError("renderer not started")
        async with self._semaphore:
            context = await self._browser.new_context(
                user_agent=user_agent,
                viewport=MOBILE_VIEWPORT if mobile else DESKTOP_VIEWPORT,
                is_mobile=mobile,
                has_touch=mobile,
                service_workers="block",
                accept_downloads=False,
                java_script_enabled=True,
            )
            try:
                # Hard wall clock: a hostile page (e.g. an infinite loop) must never pin
                # a renderer slot, even if Chromium stops answering.
                async with asyncio.timeout(self.limits.timeout_s + 10):
                    page = await context.new_page()
                    return await self._render(page, url, user_agent)
            except TimeoutError:
                logger.info("render_hard_timeout")
                return RenderResult(url=url, status=None, html="", timed_out=True)
            finally:
                try:
                    await asyncio.wait_for(context.close(), timeout=5)
                except TimeoutError:
                    logger.warning("render_context_stuck_restarting_browser")
                    await self._restart()

    async def _render(self, page: Page, url: str, user_agent: str) -> RenderResult:
        requests: list[RenderedRequest] = []
        budget = {"requests": 0, "bytes": 0}
        main_status: dict[str, int | None] = {"status": None}

        async def handle(route: Route, request: Request) -> None:
            target = request.url
            if not target.startswith(("http://", "https://")):
                await route.continue_()  # data:, blob: - no network involved
                return
            entry = RenderedRequest(
                url=target[:500], resource_type=request.resource_type, status=None
            )
            requests.append(entry)
            budget["requests"] += 1
            if budget["requests"] > self.limits.max_requests or (
                budget["bytes"] > self.limits.max_total_bytes
            ):
                entry.blocked = "limit"
                await route.abort("blockedbyclient")
                return
            headers = {
                k: v for k, v in request.headers.items() if k.lower() not in {"host", "cookie"}
            }
            headers["user-agent"] = user_agent
            try:
                response = await self.http.request(
                    request.method if request.method in {"GET", "HEAD"} else "GET",
                    target,
                    headers=headers,
                    policy=RESOURCE_POLICY,
                )
            except EgressPolicyError:
                entry.blocked = "policy"
                await route.abort("blockedbyclient")
                return
            except EgressError:
                entry.blocked = "network"
                await route.abort("failed")
                return
            budget["bytes"] += len(response.content)
            entry.status = response.status_code
            if request.is_navigation_request() and request.frame == page.main_frame:
                main_status["status"] = response.status_code
            await route.fulfill(
                status=response.status_code,
                headers={
                    k: v for k, v in response.headers.items() if k.lower() not in _DROP_HEADERS
                },
                body=response.content,
            )

        await page.route("**/*", handle)
        await page.route_web_socket("**/*", lambda ws: ws.close())
        page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))
        timed_out = False
        try:
            await page.goto(url, wait_until="load", timeout=self.limits.timeout_s * 1000)
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:  # noqa: BLE001 - long-polling pages never go idle; that's fine
                logger.debug("render_network_not_idle")
        except Exception as exc:  # noqa: BLE001 - navigation errors are reported, not raised
            timed_out = "Timeout" in type(exc).__name__
            logger.info("render_navigation_failed", error=type(exc).__name__)
        try:
            # A page whose main thread is busy never answers; don't wait for it.
            html = await asyncio.wait_for(page.content(), timeout=3)
        except Exception:  # noqa: BLE001 - includes TimeoutError
            html = ""
            timed_out = True
        return RenderResult(
            url=url, status=main_status["status"], html=html, requests=requests, timed_out=timed_out
        )
