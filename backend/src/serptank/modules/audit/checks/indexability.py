"""Can Google fetch and index the pages that matter? (Search Essentials: technical requirements)."""

from __future__ import annotations

import re
from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site
from serptank.modules.crawler.urls import host_of

REF_ROBOTS = "https://developers.google.com/search/docs/crawling-indexing/robots/intro"
REF_NOINDEX = "https://developers.google.com/search/docs/crawling-indexing/block-indexing"
REF_CANONICAL = (
    "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
)
REF_REDIRECTS = "https://developers.google.com/search/docs/crawling-indexing/301-redirects"
REF_SOFT404 = "https://developers.google.com/search/docs/crawling-indexing/http-network-errors#soft-404-errors"
_NOT_FOUND = re.compile(
    r"\b(404|not found|page (?:does not|doesn't) exist|no longer available|page not found)\b",
    re.IGNORECASE,
)


@rule(
    "robots_unreachable",
    title="robots.txt returns a server error",
    category="indexability",
    severity=Severity.CRITICAL,
    description="When robots.txt answers with a 5xx error or can't be reached, Google treats the "
    "whole host as disallowed and stops crawling it.",
    fix="Make /robots.txt return 200 (with rules) or 404 (no rules). Never 5xx.",
    effort=1,
    reference=REF_ROBOTS,
)
def robots_unreachable(site: Site) -> Iterator[Finding]:
    for host, info in site.site.get("robots", {}).items():
        status = info.get("status")
        if status is None or status >= 500:  # noqa: PLR2004
            yield Finding(info.get("url"), {"host": host, "status": status})


@rule(
    "homepage_blocked",
    title="Homepage is blocked by robots.txt",
    category="indexability",
    severity=Severity.CRITICAL,
    description="robots.txt disallows Googlebot from fetching the homepage, so Google cannot "
    "crawl the site from its most important page.",
    fix="Remove or narrow the Disallow rule that matches '/' for Googlebot (or *).",
    effort=1,
    reference=REF_ROBOTS,
)
def homepage_blocked(site: Site) -> Iterator[Finding]:
    start = site.start_page
    if start is not None and not start.allowed_google:
        yield Finding(start.url)


@rule(
    "homepage_noindex",
    title="Homepage is set to noindex",
    category="indexability",
    severity=Severity.CRITICAL,
    description="The homepage tells Google not to index it (meta robots or X-Robots-Tag).",
    fix="Remove the noindex directive from the homepage.",
    effort=1,
    reference=REF_NOINDEX,
)
def homepage_noindex(site: Site) -> Iterator[Finding]:
    start = site.start_page
    if start is not None:
        final, _, _ = site.final_page(start.url)
        if final is not None and final.is_html and final.noindex("googlebot"):
            yield Finding(final.url)


@rule(
    "server_errors",
    title="Pages return server errors (5xx)",
    category="indexability",
    severity=Severity.HIGH,
    description="Google slows crawling and eventually drops URLs that keep returning 5xx errors.",
    fix="Check the server logs for these URLs and fix the underlying errors.",
    reference="https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
)
def server_errors(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.status_code is not None and page.status_code >= 500:  # noqa: PLR2004
            yield Finding(page.url, {"status": page.status_code})


@rule(
    "broken_pages",
    title="Linked pages return 4xx errors",
    category="indexability",
    severity=Severity.HIGH,
    description="These URLs are linked from your site or listed in your sitemap but return a "
    "client error, wasting crawl budget and link equity.",
    fix="Restore the pages, redirect them (301) to the best replacement, or remove the links.",
)
def broken_pages(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.status_code is not None and 400 <= page.status_code < 500:  # noqa: PLR2004
            sources = [s for s, _ in site.inbound.get(page.url, [])]
            if sources or page.in_sitemap:
                yield Finding(
                    page.url,
                    {
                        "status": page.status_code,
                        "linked_from": sources[:5],
                        "in_sitemap": page.in_sitemap,
                    },
                )


@rule(
    "fetch_errors",
    title="Pages could not be fetched",
    category="indexability",
    severity=Severity.MEDIUM,
    description="The request failed (timeout, connection error, oversized response, or an "
    "address we refuse to contact). Search engines likely see the same failure.",
    fix="Check that these URLs load quickly and reliably from the public internet.",
)
def fetch_errors(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.error and page.error != "blocked_by_robots":
            yield Finding(page.url, {"error": page.error})


@rule(
    "noindex_in_sitemap",
    title="Sitemap lists noindex pages",
    category="indexability",
    severity=Severity.MEDIUM,
    description="Sitemaps should list only canonical, indexable URLs. Listing noindex pages "
    "sends Google mixed signals.",
    fix="Remove these URLs from the sitemap, or remove the noindex if they should rank.",
    effort=1,
)
def noindex_in_sitemap(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.in_sitemap and page.is_html and page.noindex("googlebot"):
            yield Finding(page.url)


@rule(
    "blocked_in_sitemap",
    title="Sitemap lists URLs blocked by robots.txt",
    category="indexability",
    severity=Severity.MEDIUM,
    description="Googlebot is not allowed to crawl these sitemap URLs.",
    fix="Either allow them in robots.txt or remove them from the sitemap.",
    effort=1,
)
def blocked_in_sitemap(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.in_sitemap and not page.allowed_google:
            yield Finding(page.url)


@rule(
    "non_200_in_sitemap",
    title="Sitemap lists redirected or broken URLs",
    category="indexability",
    severity=Severity.MEDIUM,
    description="Sitemap URLs should answer 200 directly. Redirects and errors waste crawl budget.",
    fix="Replace redirected URLs with their final destination and remove broken ones.",
    effort=1,
)
def non_200_in_sitemap(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.in_sitemap and page.status_code is not None and page.status_code != 200:  # noqa: PLR2004
            yield Finding(page.url, {"status": page.status_code, "redirect_to": page.redirect_to})


@rule(
    "non_canonical_in_sitemap",
    title="Sitemap lists non-canonical URLs",
    category="indexability",
    severity=Severity.LOW,
    description="These sitemap URLs declare a different canonical URL.",
    fix="List the canonical URL in the sitemap instead.",
    effort=1,
    reference=REF_CANONICAL,
)
def non_canonical_in_sitemap(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.in_sitemap and page.is_html and page.canonical and page.canonical != page.url:
            yield Finding(page.url, {"canonical": page.canonical})


@rule(
    "canonical_to_bad_target",
    title="Canonical points to a redirect, error or noindex page",
    category="indexability",
    severity=Severity.HIGH,
    description="The canonical target must be an indexable 200 page, otherwise Google ignores "
    "the hint or picks a canonical itself.",
    fix="Point rel=canonical at the final, indexable URL.",
    effort=1,
    reference=REF_CANONICAL,
)
def canonical_to_bad_target(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        target = page.canonical
        if not target or target == page.url:
            continue
        other = site.pages.get(target)
        if other is None:
            continue
        if other.status_code != 200 or (other.is_html and other.noindex("googlebot")):  # noqa: PLR2004
            yield Finding(
                page.url,
                {
                    "canonical": target,
                    "target_status": other.status_code,
                    "target_noindex": other.is_html and other.noindex("googlebot"),
                },
            )


@rule(
    "canonical_conflict",
    title="Conflicting canonical tags",
    category="indexability",
    severity=Severity.MEDIUM,
    description="The page declares more than one different canonical URL; Google may ignore "
    "all of them.",
    fix="Keep exactly one rel=canonical per page.",
    effort=1,
    reference=REF_CANONICAL,
)
def canonical_conflict(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if len(set(page.canonicals)) > 1:
            yield Finding(page.url, {"canonicals": sorted(set(page.canonicals))[:5]})


@rule(
    "canonical_missing",
    title="Indexable pages without a canonical tag",
    category="indexability",
    severity=Severity.LOW,
    description="A self-referencing canonical helps Google consolidate URL variants "
    "(tracking parameters, trailing slashes, http/https).",
    fix='Add <link rel="canonical" href="…"> pointing to the page\'s preferred URL.',
    effort=1,
    reference=REF_CANONICAL,
)
def canonical_missing(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if not page.canonicals and not page.noindex("googlebot") and page.allowed_google:
            yield Finding(page.url)


@rule(
    "canonical_cross_domain",
    title="Canonical points to another domain",
    category="indexability",
    severity=Severity.INFO,
    description="These pages hand their ranking signals to a URL on another host. That's "
    "correct for syndicated content, but a mistake otherwise.",
    fix="Confirm the cross-domain canonicals are intentional.",
    effort=1,
)
def canonical_cross_domain(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.canonical and host_of(page.canonical) not in site.hosts:
            yield Finding(page.url, {"canonical": page.canonical})


@rule(
    "redirect_chains",
    title="Redirect chains",
    category="indexability",
    severity=Severity.MEDIUM,
    description="URLs that redirect more than once. Each hop adds latency and Google stops "
    "following after 10 hops.",
    fix="Redirect straight to the final URL and update internal links to it.",
    effort=1,
    reference=REF_REDIRECTS,
)
def redirect_chains(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.is_redirect:
            final, hops, looped = site.final_page(page.url)
            if not looped and hops > 1:
                yield Finding(page.url, {"hops": hops, "final": final.url if final else None})


@rule(
    "redirect_loops",
    title="Redirect loops",
    category="indexability",
    severity=Severity.HIGH,
    description="These URLs redirect in a circle and never resolve.",
    fix="Fix the redirect rules so each URL ends on a 200 page.",
    effort=1,
    reference=REF_REDIRECTS,
)
def redirect_loops(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.error == "redirect_loop":
            yield Finding(page.url)
        elif page.is_redirect:
            _, _, looped = site.final_page(page.url)
            if looped:
                yield Finding(page.url)


@rule(
    "temporary_redirects",
    title="Temporary redirects (302/307)",
    category="indexability",
    severity=Severity.LOW,
    description="Temporary redirects tell Google the original URL will come back, so it may "
    "keep the old URL indexed.",
    fix="Use 301 or 308 for permanent moves.",
    effort=1,
    reference=REF_REDIRECTS,
)
def temporary_redirects(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.is_redirect and page.status_code in {302, 303, 307}:
            yield Finding(page.url, {"status": page.status_code, "redirect_to": page.redirect_to})


@rule(
    "soft_404_site",
    title="Missing pages return 200 (soft 404)",
    category="indexability",
    severity=Severity.HIGH,
    description="A URL that cannot exist answered 200 OK. Google classifies such pages as soft "
    "404s and they waste crawl budget.",
    fix="Return a real 404 or 410 status for URLs that don't exist.",
    effort=2,
    reference=REF_SOFT404,
)
def soft_404_site(site: Site) -> Iterator[Finding]:
    probe = site.site.get("soft404_probe", {})
    if probe.get("status") == 200:  # noqa: PLR2004
        yield Finding(probe.get("url"))


@rule(
    "soft_404_pages",
    title="Pages that look like error pages",
    category="indexability",
    severity=Severity.MEDIUM,
    description="These pages answer 200 but look like 'not found' pages, so Google will likely "
    "treat them as soft 404s.",
    fix="Return 404/410 for missing content, or add real content to these pages.",
    reference=REF_SOFT404,
)
def soft_404_pages(site: Site) -> Iterator[Finding]:
    probe_hash = site.site.get("soft404_probe", {}).get("content_hash")
    for page in site.html_pages:
        if page.found_via == "start":
            continue
        title = page.title or ""
        if (probe_hash and page.content_hash == probe_hash) or _NOT_FOUND.search(title):
            yield Finding(page.url, {"title": title})


@rule(
    "meta_refresh",
    title="Meta refresh redirects",
    category="indexability",
    severity=Severity.LOW,
    description="Meta refresh redirects are slow and not universally supported.",
    fix="Replace them with server-side 301 redirects.",
    effort=1,
    reference=REF_REDIRECTS,
)
def meta_refresh(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        content = page.data.get("meta_refresh") or ""
        if "url=" in content.lower():
            yield Finding(page.url, {"content": content})
