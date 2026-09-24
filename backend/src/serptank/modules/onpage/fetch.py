"""Polite, robots-respecting fetch of the pages an analysis compares.

* Every request goes through :class:`SafeHttpClient` (SSRF policy, size/time caps).
* robots.txt is honoured for our own user agent (SerpTankBot): a competitor that
  disallows us is skipped and reported as such - never fetched around.
* At most ``MAX_PAGES`` pages, ``MAX_CONCURRENCY`` at a time, one request per host.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlsplit

import structlog

from serptank.core.http import (
    DisallowedContentTypeError,
    EgressError,
    EgressPolicy,
    SafeHttpClient,
)
from serptank.modules.crawler.robots import SERPTANKBOT, parse_robots
from serptank.modules.onpage.text import PageContent, extract_content

logger = structlog.get_logger(__name__)

MAX_PAGES = 10
MAX_CONCURRENCY = 4
PAGE_POLICY = EgressPolicy(
    max_response_bytes=2 * 1024 * 1024,
    total_timeout_s=15,
    allowed_content_types=frozenset({"text/html", "application/xhtml+xml"}),
)
ROBOTS_POLICY = EgressPolicy(max_response_bytes=512 * 1024, total_timeout_s=10)


@dataclass
class FetchOutcome:
    url: str
    page: PageContent | None = None
    # robots | robots_error | http_<status> | unreachable | not_html
    skipped: str | None = None


async def _allowed(http: SafeHttpClient, url: str) -> bool | str:
    """True/False from robots.txt, or a skip reason (``unreachable``/``robots_error``)."""
    parts = urlsplit(url)
    try:
        response = await http.get(
            f"{parts.scheme}://{parts.netloc}/robots.txt", policy=ROBOTS_POLICY
        )
    except EgressError:
        return "unreachable"
    if response.status_code >= 500:  # noqa: PLR2004 - RFC 9309: treat as full disallow
        return "robots_error"
    if response.status_code != 200:  # noqa: PLR2004 - 4xx: no restrictions
        return True
    robots = parse_robots(response.content.decode("utf-8", errors="replace"))
    path = parts.path or "/"
    return robots.is_allowed(SERPTANKBOT, f"{path}?{parts.query}" if parts.query else path)


async def fetch_page(
    http: SafeHttpClient, url: str, hosts: frozenset[str] | None = None
) -> FetchOutcome:
    allowed = await _allowed(http, url)
    if isinstance(allowed, str):
        return FetchOutcome(url, skipped=allowed)
    if not allowed:
        return FetchOutcome(url, skipped="robots")
    try:
        response = await http.get(url, policy=PAGE_POLICY)
    except EgressError as exc:
        kind = "not_html" if isinstance(exc, DisallowedContentTypeError) else "unreachable"
        logger.info("onpage_fetch_failed", url=url, error=type(exc).__name__)
        return FetchOutcome(url, skipped=kind)
    if response.status_code != 200:  # noqa: PLR2004
        return FetchOutcome(url, skipped=f"http_{response.status_code}")
    html = response.content.decode("utf-8", errors="replace")
    return FetchOutcome(url, page=extract_content(html, response.url or url, hosts))


async def fetch_many(http: SafeHttpClient, urls: list[str]) -> list[FetchOutcome]:
    """Fetch up to MAX_PAGES distinct-host pages concurrently (order preserved)."""
    seen: set[str] = set()
    chosen: list[str] = []
    for url in urls:
        host = urlsplit(url).hostname or ""
        if host and host not in seen:
            seen.add(host)
            chosen.append(url)
        if len(chosen) >= MAX_PAGES:
            break
    gate = asyncio.Semaphore(MAX_CONCURRENCY)

    async def one(url: str) -> FetchOutcome:
        async with gate:
            return await fetch_page(http, url)

    return list(await asyncio.gather(*(one(u) for u in chosen)))
