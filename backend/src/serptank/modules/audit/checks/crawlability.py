"""Sitemaps, site structure, internal links (Search Essentials: crawlability)."""

from __future__ import annotations

from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site

REF_SITEMAP = "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview"
REF_LINKS = "https://developers.google.com/search/docs/crawling-indexing/links-crawlable"
MAX_DEPTH = 3


@rule(
    "sitemap_missing",
    title="No XML sitemap found",
    category="crawlability",
    severity=Severity.MEDIUM,
    description="No sitemap was declared in robots.txt or found at /sitemap.xml. Sitemaps help "
    "Google discover new and deep pages.",
    fix="Publish an XML sitemap and reference it in robots.txt and Search Console.",
    reference=REF_SITEMAP,
)
def sitemap_missing(site: Site) -> Iterator[Finding]:
    sitemaps = site.site.get("sitemaps", [])
    if not any(s.get("status") == 200 and not s.get("error") for s in sitemaps):  # noqa: PLR2004
        yield Finding()


@rule(
    "sitemap_errors",
    title="Sitemap could not be read",
    category="crawlability",
    severity=Severity.HIGH,
    description="A sitemap is declared but is unreachable, returns an error, or isn't valid XML.",
    fix="Make every sitemap URL return valid sitemap XML with status 200.",
    effort=1,
    reference=REF_SITEMAP,
)
def sitemap_errors(site: Site) -> Iterator[Finding]:
    for entry in site.site.get("sitemaps", []):
        if entry.get("error") or entry.get("status") not in (None, 200):
            yield Finding(
                entry.get("url"), {"status": entry.get("status"), "error": entry.get("error")}
            )


@rule(
    "sitemap_not_in_robots",
    title="Sitemap isn't referenced in robots.txt",
    category="crawlability",
    severity=Severity.LOW,
    description="Declaring the sitemap in robots.txt lets every search engine find it.",
    fix="Add 'Sitemap: https://…/sitemap.xml' to robots.txt.",
    effort=1,
    reference=REF_SITEMAP,
)
def sitemap_not_in_robots(site: Site) -> Iterator[Finding]:
    sitemaps = site.site.get("sitemaps", [])
    ok = [s for s in sitemaps if s.get("status") == 200]  # noqa: PLR2004
    if ok and not any(s.get("declared_in_robots") for s in ok):
        yield Finding(ok[0].get("url"))


@rule(
    "sitemap_foreign_urls",
    title="Sitemap lists URLs on other hosts",
    category="crawlability",
    severity=Severity.MEDIUM,
    description="Sitemaps may only list URLs from the same host unless cross-submission is "
    "verified; search engines ignore the others.",
    fix="Move those URLs to a sitemap on their own host.",
    effort=1,
    reference=REF_SITEMAP,
)
def sitemap_foreign_urls(site: Site) -> Iterator[Finding]:
    for entry in site.site.get("sitemaps", []):
        if entry.get("external_urls"):
            yield Finding(entry.get("url"), {"count": entry["external_urls"]})


@rule(
    "orphan_pages",
    title="Orphan pages (in sitemap, no internal links)",
    category="crawlability",
    severity=Severity.MEDIUM,
    description="These pages are only in the sitemap. Without internal links they receive no "
    "link equity and Google may consider them unimportant.",
    fix="Link to these pages from relevant pages, or remove them if obsolete.",
    reference=REF_LINKS,
)
def orphan_pages(site: Site) -> Iterator[Finding]:
    if site.budget_exhausted:
        return  # with a partial crawl we can't know that no page links to them
    for page in site.html_pages:
        if page.in_sitemap and page.inlinks == 0 and page.found_via == "sitemap":
            yield Finding(page.url)


@rule(
    "deep_pages",
    title="Pages more than 3 clicks from the homepage",
    category="crawlability",
    severity=Severity.LOW,
    description="Deeply buried pages are crawled less often and receive less internal link equity.",
    fix="Link important pages from the homepage, hubs or navigation.",
    effort=3,
)
def deep_pages(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.depth is not None and page.depth > MAX_DEPTH and page.indexable():
            yield Finding(page.url, {"depth": page.depth})


@rule(
    "broken_internal_links",
    title="Pages linking to broken URLs",
    category="links",
    severity=Severity.HIGH,
    description="These pages contain internal links to URLs that return 4xx or 5xx errors.",
    fix="Update or remove the broken links.",
    effort=1,
    reference=REF_LINKS,
)
def broken_internal_links(site: Site) -> Iterator[Finding]:
    broken: dict[str, list[str]] = {}
    for target, sources in site.inbound.items():
        page = site.pages.get(target)
        if page is not None and page.status_code is not None and page.status_code >= 400:  # noqa: PLR2004
            for source, _ in sources:
                broken.setdefault(source, []).append(target)
    for source, targets in broken.items():
        yield Finding(source, {"broken": sorted(set(targets))[:10], "count": len(set(targets))})


@rule(
    "links_to_redirects",
    title="Internal links pointing to redirects",
    category="links",
    severity=Severity.LOW,
    description="Linking straight to the final URL saves a hop for users and crawlers.",
    fix="Update internal links to the redirect destination.",
    effort=2,
)
def links_to_redirects(site: Site) -> Iterator[Finding]:
    by_source: dict[str, list[str]] = {}
    for target, sources in site.inbound.items():
        page = site.pages.get(target)
        if page is not None and page.is_redirect:
            for source, _ in sources:
                by_source.setdefault(source, []).append(target)
    for source, targets in by_source.items():
        yield Finding(
            source, {"redirecting": sorted(set(targets))[:10], "count": len(set(targets))}
        )


@rule(
    "internal_nofollow",
    title="Internal links marked nofollow",
    category="links",
    severity=Severity.LOW,
    description="nofollow on internal links stops link equity flowing to your own pages.",
    fix="Remove rel=nofollow from internal links unless the target should not be crawled.",
    effort=1,
    reference="https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links",
)
def internal_nofollow(site: Site) -> Iterator[Finding]:
    by_source: dict[str, int] = {}
    for sources in site.inbound.values():
        for source, nofollow in sources:
            if nofollow:
                by_source[source] = by_source.get(source, 0) + 1
    for source, count in by_source.items():
        yield Finding(source, {"count": count})


@rule(
    "crawl_limited",
    title="Only part of the site was audited",
    category="crawlability",
    severity=Severity.INFO,
    description="The crawl stopped at its page budget (or the shallow limit for unverified "
    "domains), so site-wide checks such as orphan pages are incomplete.",
    fix="Verify domain ownership or raise the crawl budget on your plan for a full audit.",
    effort=1,
)
def crawl_limited(site: Site) -> Iterator[Finding]:
    if site.budget_exhausted:
        yield Finding(None, {"domain_verified": site.domain_verified})
