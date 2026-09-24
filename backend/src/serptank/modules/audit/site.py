"""In-memory view of one crawl that audit rules evaluate (pure data, no I/O)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from serptank.modules.crawler.parser import PageData, robots_directives

HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
HTTP_OK = 200
REDIRECT_MIN, REDIRECT_MAX = 300, 399


@dataclass
class Page:
    id: uuid.UUID
    url: str
    depth: int | None = None
    found_via: str = "link"
    status_code: int | None = None
    error: str | None = None
    content_type: str | None = None
    response_ms: int | None = None
    bytes: int | None = None
    redirect_to: str | None = None
    in_sitemap: bool = False
    allowed_google: bool = True
    allowed_bing: bool = True
    x_robots: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None
    simhash: int | None = None
    inlinks: int = 0
    rendered: dict[str, Any] | None = None
    mobile: dict[str, Any] | None = None

    @property
    def is_html(self) -> bool:
        return self.status_code == HTTP_OK and self.content_type in HTML_TYPES and bool(self.data)

    @property
    def is_redirect(self) -> bool:
        return (
            self.status_code is not None
            and REDIRECT_MIN <= self.status_code <= REDIRECT_MAX
            and bool(self.redirect_to)
        )

    def directives(self, bot: str) -> set[str]:
        meta = PageData(meta_robots=self.data.get("meta_robots", {}))
        return robots_directives(meta, self.x_robots, bot)

    def noindex(self, bot: str = "googlebot") -> bool:
        return "noindex" in self.directives(bot)

    @property
    def canonicals(self) -> list[str]:
        return list(self.data.get("canonicals", []))

    @property
    def canonical(self) -> str | None:
        return self.canonicals[0] if self.canonicals else None

    def indexable(self, bot: str = "googlebot") -> bool:
        allowed = self.allowed_google if bot == "googlebot" else self.allowed_bing
        canonical = self.canonical
        return (
            self.is_html
            and allowed
            and not self.noindex(bot)
            and (canonical is None or canonical == self.url)
        )

    @property
    def title(self) -> str | None:
        value = self.data.get("title")
        return value if isinstance(value, str) else None


@dataclass
class Site:
    start_url: str
    hosts: frozenset[str]
    engines: frozenset[str]
    pages: dict[str, Page]
    # target URL -> [(source URL, nofollow)] for internal links
    inbound: dict[str, list[tuple[str, bool]]] = field(default_factory=lambda: defaultdict(list))
    site: dict[str, Any] = field(default_factory=dict)  # robots, sitemaps, probes
    budget_exhausted: bool = False
    domain_verified: bool = True
    render_available: bool = False

    @property
    def html_pages(self) -> list[Page]:
        return [p for p in self.pages.values() if p.is_html]

    @property
    def start_page(self) -> Page | None:
        return self.pages.get(self.start_url) or next(
            (p for p in self.pages.values() if p.found_via == "start"), None
        )

    def final_page(self, url: str, max_hops: int = 10) -> tuple[Page | None, int, bool]:
        """Follow recorded redirects: (final page, hops, looped)."""
        seen: set[str] = set()
        page = self.pages.get(url)
        hops = 0
        while page is not None and page.is_redirect and hops <= max_hops:
            if page.url in seen:
                return page, hops, True
            seen.add(page.url)
            target = page.redirect_to or ""
            hops += 1
            nxt = self.pages.get(target)
            if nxt is None:
                return None, hops, False
            page = nxt
        return page, hops, False
