"""The crawl engine: breadth-first, polite, robots-aware, budgeted, SSRF-safe.

The engine is pure orchestration - no database access. It emits :class:`PageRecord`
objects to a :class:`CrawlSink` (the job handler persists them in batches), so it can be
unit-tested against a fake internet.

Behaviour
---------
* **Scope:** only the project's hosts (domain + www twin) are fetched. External links
  are recorded, never followed - we must not become an abuse vector (plan §5.6).
* **Robots:** our crawler obeys the ``serptankbot`` group (else ``*``) per host. Each
  page also records whether Googlebot and Bingbot may fetch it, for the audit.
  robots.txt 4xx = allow all; 5xx/unreachable = disallow all (RFC 9309), in which case
  the crawl stops honestly instead of guessing.
* **Politeness:** one request at a time per host, at least ``min_delay`` apart, or the
  robots ``crawl-delay`` for our bot (capped at 10 s).
* **Redirects** are followed hop by hop so every hop is recorded with its status.
* **Depth** is click depth from the start URL. Sitemap URLs not reached through links
  are fetched afterwards (orphan candidates) while budget remains.
"""

from __future__ import annotations

import asyncio
import secrets
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

from serptank.core.http import (
    DisallowedContentTypeError,
    EgressError,
    EgressPolicy,
    EgressPolicyError,
    ResponseTooLargeError,
    SafeHttpClient,
    SafeResponse,
    TooManyRedirectsError,
)
from serptank.core.models import uuid7
from serptank.modules.crawler.parser import Link, PageData, parse_html
from serptank.modules.crawler.robots import (
    AI_SEARCH_BOTS,
    AI_TRAINING_BOTS,
    ALLOW_ALL,
    BINGBOT,
    DISALLOW_ALL,
    GOOGLEBOT,
    SERPTANKBOT,
    RobotsTxt,
    parse_robots,
)
from serptank.modules.crawler.sitemaps import Sitemap, SitemapError, parse_sitemap
from serptank.modules.crawler.urls import (
    host_of,
    is_internal,
    looks_like_page,
    normalize_url,
    path_and_query,
)

logger = structlog.get_logger(__name__)

MAX_CRAWL_DELAY_S = 10.0
MAX_SITEMAPS = 50
MAX_SITEMAP_URLS = 100_000
HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
PAGE_POLICY = EgressPolicy(
    follow_redirects=False,
    max_response_bytes=16 * 1024 * 1024,  # Googlebot reads the first 15 MB of HTML
    total_timeout_s=30,
)
SMALL_POLICY = EgressPolicy(max_response_bytes=512 * 1024, total_timeout_s=15)
SITEMAP_POLICY = EgressPolicy(max_response_bytes=50 * 1024 * 1024, total_timeout_s=60)


@dataclass
class CrawlConfig:
    start_url: str
    hosts: frozenset[str]
    max_pages: int
    max_depth: int = 10
    min_delay_s: float = 1.0
    concurrency: int = 2
    mobile_user_agent: str = ""
    mobile_sample: int = 0


@dataclass
class HostRobots:
    status: int | None  # HTTP status of /robots.txt, None if unreachable
    robots: RobotsTxt
    error: str | None = None


@dataclass
class PageRecord:
    id: uuid.UUID
    url: str
    depth: int | None
    found_via: str  # "start" | "link" | "sitemap" | "redirect"
    status_code: int | None = None
    error: str | None = None  # stable code when the page could not be fetched
    content_type: str | None = None
    response_ms: int | None = None
    bytes: int | None = None
    redirect_to: str | None = None
    x_robots: list[str] = field(default_factory=list)
    allowed: dict[str, bool] = field(default_factory=dict)  # bot -> robots.txt allows
    data: PageData | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class CrawlSummary:
    robots: dict[str, dict[str, Any]] = field(default_factory=dict)  # host -> summary
    sitemaps: list[dict[str, Any]] = field(default_factory=list)
    sitemap_urls: set[str] = field(default_factory=set)
    sitemap_hreflang: dict[str, dict[str, str]] = field(default_factory=dict)
    pages_fetched: int = 0
    pages_discovered: int = 0
    budget_exhausted: bool = False
    soft404_probe: dict[str, Any] = field(default_factory=dict)
    https_redirect: dict[str, Any] = field(default_factory=dict)
    mobile: dict[str, dict[str, Any]] = field(default_factory=dict)  # url -> summary


class CrawlSink(Protocol):
    async def page(self, record: PageRecord) -> None: ...

    async def links(self, source: PageRecord, links: list[Link]) -> None: ...


class CrawlAbortedError(Exception):
    """The crawl cannot continue (e.g. robots.txt unreachable). Message is user-safe."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ProgressFn = Callable[[CrawlSummary], Awaitable[None]]


def mobile_summary(data: PageData) -> dict[str, Any]:
    return {
        "title": data.title,
        "word_count": data.word_count,
        "links": len(data.links),
        "h1": len(data.h1),
        "json_ld": len(data.json_ld),
        "canonical": data.canonicals[0] if data.canonicals else None,
        "viewport": data.viewport,
        "noindex": "noindex" in data.meta_robots.get("robots", []),
    }


class Crawler:
    def __init__(
        self,
        http: SafeHttpClient,
        config: CrawlConfig,
        sink: CrawlSink,
        *,
        progress: ProgressFn | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        summary: CrawlSummary | None = None,
    ) -> None:
        self.http = http
        self.config = config
        self.sink = sink
        self.progress = progress
        self._sleep = sleep
        self.summary = summary or CrawlSummary()
        self._robots: dict[str, HostRobots] = {}
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._last_fetch: dict[str, float] = {}
        self._seen: set[str] = set()
        self._queue: deque[tuple[str, int | None, str]] = deque()
        self._html_pages: list[str] = []

    # ------------------------------------------------------------------ robots
    async def robots_for(self, host: str, scheme: str = "https") -> HostRobots:
        if host in self._robots:
            return self._robots[host]
        url = f"{scheme}://{host}/robots.txt"
        try:
            response = await self.http.get(url, policy=SMALL_POLICY)
        except EgressPolicyError:
            # The host itself is off-limits (e.g. resolves to a private address).
            entry = HostRobots(None, DISALLOW_ALL, error="blocked_address")
        except EgressError as exc:
            entry = HostRobots(None, DISALLOW_ALL, error=type(exc).__name__)
        else:
            if 200 <= response.status_code < 300:  # noqa: PLR2004
                entry = HostRobots(response.status_code, parse_robots(response.text()))
            elif 400 <= response.status_code < 500:  # noqa: PLR2004
                entry = HostRobots(response.status_code, ALLOW_ALL)
            else:
                entry = HostRobots(response.status_code, DISALLOW_ALL)
        self._robots[host] = entry
        robots = entry.robots
        self.summary.robots[host] = {
            "url": url,
            "status": entry.status,
            "error": entry.error,
            "sitemaps": robots.sitemaps[:50],
            "crawl_delay": {
                bot: robots.crawl_delay(bot) for bot in (GOOGLEBOT, BINGBOT, SERPTANKBOT)
            },
            "yandex_host": robots.yandex_host,
            "clean_params": robots.clean_params[:20],
            "invalid_lines": robots.invalid_lines,
            "home_allowed": {bot: robots.is_allowed(bot, "/") for bot in (GOOGLEBOT, BINGBOT)},
            "ai_bots_allowed": {
                bot: robots.is_allowed(bot, "/") for bot in (*AI_SEARCH_BOTS, *AI_TRAINING_BOTS)
            },
        }
        return entry

    # --------------------------------------------------------------- politeness
    async def _polite(self, host: str) -> None:
        robots = self._robots.get(host)
        delay = self.config.min_delay_s
        if robots is not None:
            declared = robots.robots.crawl_delay(SERPTANKBOT)
            if declared:
                delay = max(delay, min(declared, MAX_CRAWL_DELAY_S))
        wait = self._last_fetch.get(host, 0.0) + delay - time.monotonic()
        if wait > 0:
            await self._sleep(wait)
        self._last_fetch[host] = time.monotonic()

    async def _fetch(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> tuple[SafeResponse | None, str | None, int]:
        host = host_of(url)
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            await self._polite(host)
            started = time.monotonic()
            try:
                response = await self.http.request("GET", url, headers=headers, policy=PAGE_POLICY)
            except ResponseTooLargeError:
                return None, "too_large", _ms(started)
            except DisallowedContentTypeError:
                return None, "content_type", _ms(started)
            except TooManyRedirectsError:
                return None, "redirect_loop", _ms(started)
            except EgressPolicyError:
                return None, "blocked_address", _ms(started)
            except EgressError:
                return None, "network_error", _ms(started)
            return response, None, _ms(started)

    # ----------------------------------------------------------------- sitemaps
    async def _load_sitemaps(self, start_host: str) -> None:  # noqa: PLR0912
        robots = await self.robots_for(start_host)
        candidates = [
            u
            for s in robots.robots.sitemaps
            if (u := normalize_url(s)) and is_internal(u, self.config.hosts)
        ]
        declared = bool(candidates)
        if not candidates:
            candidates = [f"https://{start_host}/sitemap.xml"]
        pending = deque(candidates)
        seen: set[str] = set()
        while pending and len(seen) < MAX_SITEMAPS:
            url = pending.popleft()
            if url in seen:
                continue
            seen.add(url)
            entry: dict[str, Any] = {"url": url, "declared_in_robots": declared, "urls": 0}
            try:
                response = await self.http.get(url, policy=SITEMAP_POLICY)
            except EgressError as exc:
                entry["error"] = "unreachable"
                logger.info("sitemap_fetch_failed", error=type(exc).__name__)
                self.summary.sitemaps.append(entry)
                continue
            entry["status"] = response.status_code
            if response.status_code != 200:  # noqa: PLR2004
                if declared or response.status_code != 404:  # noqa: PLR2004
                    self.summary.sitemaps.append(entry)
                continue
            try:
                sitemap: Sitemap = parse_sitemap(response.content)
            except SitemapError as exc:
                entry["error"] = str(exc)
                self.summary.sitemaps.append(entry)
                continue
            entry["urls"] = len(sitemap.urls)
            entry["truncated"] = sitemap.truncated
            entry["children"] = len(sitemap.children)
            external = 0
            for item in sitemap.urls:
                loc = normalize_url(item.loc)
                if loc is None or not is_internal(loc, self.config.hosts):
                    external += 1
                    continue
                if len(self.summary.sitemap_urls) < MAX_SITEMAP_URLS:
                    self.summary.sitemap_urls.add(loc)
                    if item.alternates:
                        self.summary.sitemap_hreflang[loc] = item.alternates
            entry["external_urls"] = external
            self.summary.sitemaps.append(entry)
            for child in sitemap.children:
                child_url = normalize_url(child)
                if child_url and is_internal(child_url, self.config.hosts):
                    pending.append(child_url)

    # --------------------------------------------------------------------- crawl
    def _enqueue(self, url: str, depth: int | None, via: str) -> None:
        if url in self._seen or not is_internal(url, self.config.hosts):
            return
        self._seen.add(url)
        self._queue.append((url, depth, via))

    async def _visit(self, url: str, depth: int | None, via: str) -> None:
        host = host_of(url)
        scheme = url.split(":", 1)[0]
        robots = await self.robots_for(host, scheme)
        path = path_and_query(url)
        record = PageRecord(id=uuid7(), url=url, depth=depth, found_via=via)
        record.allowed = {
            bot: robots.robots.is_allowed(bot, path) for bot in (GOOGLEBOT, BINGBOT, SERPTANKBOT)
        }
        if robots.error == "blocked_address":
            record.error = "blocked_address"
            await self.sink.page(record)
            return
        if not record.allowed[SERPTANKBOT]:
            record.error = "blocked_by_robots"
            await self.sink.page(record)
            return
        response, error, elapsed = await self._fetch(url)
        record.response_ms = elapsed
        self.summary.pages_fetched += 1
        if response is None:
            record.error = error
            await self.sink.page(record)
            return
        record.status_code = response.status_code
        record.content_type = response.content_type or None
        record.bytes = len(response.content)
        record.x_robots = response.headers.get_list("x-robots-tag")[:10]
        record.headers = {
            k: response.headers[k][:300]
            for k in ("content-type", "last-modified", "strict-transport-security", "link")
            if k in response.headers
        }
        location = response.headers.get("location")
        if 300 <= response.status_code < 400 and location:  # noqa: PLR2004
            target = normalize_url(location, url)
            record.redirect_to = target
            await self.sink.page(record)
            if target:
                self._enqueue(target, depth, "redirect")
            return
        if response.status_code == 200 and record.content_type in HTML_TYPES:  # noqa: PLR2004
            record.data = parse_html(response.text(), url)
            self._html_pages.append(url)
        await self.sink.page(record)
        if record.data is None:
            return
        await self.sink.links(record, record.data.links)
        nofollow_page = "nofollow" in record.data.meta_robots.get("robots", [])
        if depth is not None and depth < self.config.max_depth and not nofollow_page:
            for link in record.data.links:
                if not link.nofollow and looks_like_page(link.url):
                    self._enqueue(link.url, depth + 1, "link")
        # Canonical and hreflang targets are discovered too (as Google does), so the audit
        # can check that they resolve to indexable pages.
        hinted = [*record.data.canonicals, *(url for _, url in record.data.hreflang)]
        for target in hinted:
            self._enqueue(target, None if depth is None else depth + 1, "hint")

    async def _drain(self) -> None:
        workers = max(1, self.config.concurrency)
        running: set[asyncio.Task[None]] = set()
        while self._queue or running:
            while self._queue and len(running) < workers:
                if self.summary.pages_fetched + len(running) >= self.config.max_pages:
                    self.summary.budget_exhausted = True
                    self._queue.clear()
                    break
                url, depth, via = self._queue.popleft()
                running.add(asyncio.create_task(self._visit(url, depth, via)))
            if not running:
                break
            done, running = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()  # re-raise unexpected errors (and cancellation)
            if self.progress is not None:
                await self.progress(self.summary)

    async def run(self) -> CrawlSummary:
        start = normalize_url(self.config.start_url)
        if start is None:
            raise CrawlAbortedError("invalid_start_url", "The site address is not valid.")
        start_host = host_of(start)
        robots = await self.robots_for(start_host, start.split(":", 1)[0])
        if robots.robots is DISALLOW_ALL:
            raise CrawlAbortedError(
                "robots_unreachable",
                "Your robots.txt could not be fetched (server error or unreachable). Search "
                "engines treat this as 'do not crawl', so we stopped too. Fix robots.txt and "
                "run the audit again.",
            )
        await self._load_sitemaps(start_host)
        self._enqueue(start, 0, "start")
        await self._drain()
        # Sitemap URLs never reached through links (orphan candidates), while budget lasts.
        for url in sorted(self.summary.sitemap_urls - self._seen):
            if looks_like_page(url):
                self._enqueue(url, None, "sitemap")
        await self._drain()
        self.summary.pages_discovered = len(self._seen)
        await self._probes(start)
        await self._mobile_sample()
        return self.summary

    # ------------------------------------------------------------ extra checks
    async def _probes(self, start: str) -> None:
        host = host_of(start)
        # Soft 404: a URL that cannot exist must not answer 200.
        probe = f"https://{host}/serptank-missing-{secrets.token_hex(6)}"
        response, error, _ = await self._fetch(probe)
        self.summary.soft404_probe = {
            "url": probe,
            "status": response.status_code if response else None,
            "error": error,
            "content_hash": (
                parse_html(response.text(), probe).content_hash
                if response is not None and response.content_type in HTML_TYPES
                else None
            ),
        }
        # HTTP should permanently redirect to HTTPS.
        response, error, _ = await self._fetch(f"http://{host}/")
        location = response.headers.get("location") if response else None
        self.summary.https_redirect = {
            "status": response.status_code if response else None,
            "error": error,
            "location": normalize_url(location, f"http://{host}/") if location else None,
        }

    async def _mobile_sample(self) -> None:
        if not self.config.mobile_sample or not self.config.mobile_user_agent:
            return
        for url in self._html_pages[: self.config.mobile_sample]:
            response, _, _ = await self._fetch(
                url, headers={"user-agent": self.config.mobile_user_agent}
            )
            if response is None or response.status_code != 200:  # noqa: PLR2004
                self.summary.mobile[url] = {"status": response.status_code if response else None}
                continue
            if response.content_type in HTML_TYPES:
                self.summary.mobile[url] = mobile_summary(parse_html(response.text(), url)) | {
                    "status": 200
                }

    def robots_rules(self) -> dict[str, RobotsTxt]:
        return {host: entry.robots for host, entry in self._robots.items()}

    @property
    def html_pages(self) -> list[str]:
        return list(self._html_pages)


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
