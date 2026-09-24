"""Crawl engine behaviour with an in-memory sink (no database)."""

from __future__ import annotations

import httpx
import pytest

from serptank.core.http import SafeHttpClient
from serptank.modules.crawler.engine import CrawlAbortedError, CrawlConfig, Crawler, PageRecord
from serptank.modules.crawler.parser import Link


class MemorySink:
    def __init__(self) -> None:
        self.pages: dict[str, PageRecord] = {}
        self.link_map: dict[str, list[Link]] = {}

    async def page(self, record: PageRecord) -> None:
        self.pages[record.url] = record

    async def links(self, source: PageRecord, links: list[Link]) -> None:
        self.link_map[source.url] = links


async def resolver(host: str, _port: int) -> list[str]:
    # "internal.site.com" resolves to a private address (DNS rebinding style attack).
    return ["10.0.0.5"] if host.startswith("internal.") else ["93.184.215.34"]


def html(body: str) -> httpx.Response:
    return httpx.Response(
        200, headers={"content-type": "text/html"}, text=f"<html><body>{body}</body></html>"
    )


def make_crawler(
    handler: httpx.MockTransport, **config: object
) -> tuple[Crawler, MemorySink, list[float]]:
    sink = MemorySink()
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    http = SafeHttpClient(resolver=resolver, transport=handler)
    defaults: dict[str, object] = {
        "start_url": "https://site.com/",
        "hosts": frozenset({"site.com", "www.site.com", "internal.site.com"}),
        "max_pages": 50,
        "min_delay_s": 0.0,
    }
    defaults.update(config)
    crawler = Crawler(http, CrawlConfig(**defaults), sink, sleep=fake_sleep)  # type: ignore[arg-type]
    return crawler, sink, sleeps


async def test_ssrf_redirects_and_private_hosts_are_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(404)
        if path == "/":
            return html('<a href="/to-metadata">m</a><a href="https://internal.site.com/">i</a>')
        if path == "/to-metadata":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/"})
        return httpx.Response(404)

    crawler, sink, _ = make_crawler(httpx.MockTransport(handler))
    await crawler.run()
    # The redirect is recorded but its external target is never fetched.
    assert (
        sink.pages["https://site.com/to-metadata"].redirect_to == "http://169.254.169.254/latest/"
    )
    assert "http://169.254.169.254/latest/" not in sink.pages
    # A same-site host resolving to a private IP is refused by SafeHttpClient.
    assert sink.pages["https://internal.site.com/"].error == "blocked_address"


async def test_budget_depth_politeness_and_nofollow() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: serptankbot\nCrawl-delay: 30\n")
        if path == "/":
            links = "".join(f'<a href="/p{i}">p</a>' for i in range(20))
            return html(links + '<a href="/nf" rel="nofollow">nf</a>')
        return html('<a href="/deeper">d</a>')

    crawler, sink, sleeps = make_crawler(httpx.MockTransport(handler), max_pages=5, concurrency=1)
    summary = await crawler.run()
    fetched = [p for p in sink.pages.values() if p.status_code is not None]
    assert len(fetched) <= 5
    assert summary.budget_exhausted
    assert "https://site.com/nf" not in sink.pages
    # crawl-delay 30 s is honoured for our bot but capped at 10 s.
    assert sleeps
    assert max(sleeps) <= 10.0


async def test_robots_unreachable_aborts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    crawler, _, _ = make_crawler(httpx.MockTransport(handler))
    with pytest.raises(CrawlAbortedError) as exc:
        await crawler.run()
    assert exc.value.code == "robots_unreachable"


async def test_invalid_start_url() -> None:
    crawler, _, _ = make_crawler(
        httpx.MockTransport(lambda r: httpx.Response(200)), start_url="notaurl"
    )
    with pytest.raises(CrawlAbortedError):
        await crawler.run()
