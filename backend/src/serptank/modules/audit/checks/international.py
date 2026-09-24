"""hreflang validation (HTML link elements and sitemap alternates)."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Page, Site

REF = "https://developers.google.com/search/docs/specialty/international/localized-versions"
# ISO 639-1 language, optional script, optional ISO 3166-1 alpha-2 / UN M.49 region.
_CODE = re.compile(r"^(x-default|[a-z]{2,3}(-[a-z]{4})?(-([a-z]{2}|\d{3}))?)$")
_BAD_REGION = {"uk": "gb", "eu": None}  # common mistakes: en-UK, en-EU


def _alternates(site: Site, page: Page) -> list[tuple[str, str]]:
    pairs = [(lang, url) for lang, url in page.data.get("hreflang", [])]
    sitemap = site.site.get("sitemap_hreflang", {}).get(page.url, {})
    pairs.extend(sitemap.items())
    return pairs


@rule(
    "hreflang_invalid_code",
    title="Invalid hreflang codes",
    category="international",
    severity=Severity.MEDIUM,
    description="Google ignores hreflang annotations with invalid language or region codes "
    "(e.g. en-UK instead of en-GB).",
    fix="Use ISO 639-1 language codes with optional ISO 3166-1 alpha-2 regions, or x-default.",
    effort=1,
    reference=REF,
)
def invalid_code(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        bad = []
        for lang, _ in _alternates(site, page):
            region = lang.split("-")[-1] if "-" in lang else None
            if not _CODE.match(lang) or (region in _BAD_REGION):
                bad.append(lang)
        if bad:
            yield Finding(page.url, {"codes": sorted(set(bad))[:10]})


@rule(
    "hreflang_missing_self",
    title="hreflang set without a self-reference",
    category="international",
    severity=Severity.LOW,
    description="Each page in an hreflang set should list itself as well as its alternates.",
    fix="Add an hreflang entry pointing to the page's own URL.",
    effort=1,
    reference=REF,
)
def missing_self(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        alternates = _alternates(site, page)
        if alternates and page.url not in {url for _, url in alternates}:
            yield Finding(page.url)


@rule(
    "hreflang_missing_return",
    title="hreflang without return links",
    category="international",
    severity=Severity.MEDIUM,
    description="If page A lists page B as an alternate, B must list A. Google ignores "
    "one-way annotations.",
    fix="Add the missing reciprocal hreflang entries.",
    reference=REF,
)
def missing_return(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        missing = []
        for _, url in _alternates(site, page):
            other = site.pages.get(url)
            if url == page.url or other is None or not other.is_html:
                continue
            if page.url not in {u for _, u in _alternates(site, other)}:
                missing.append(url)
        if missing:
            yield Finding(page.url, {"no_return_from": sorted(set(missing))[:10]})


@rule(
    "hreflang_bad_target",
    title="hreflang points to redirects, errors or non-canonical pages",
    category="international",
    severity=Severity.MEDIUM,
    description="Alternates must be indexable, canonical 200 pages.",
    fix="Point hreflang at the final canonical URL of each language version.",
    effort=1,
    reference=REF,
)
def bad_target(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        bad = []
        for lang, url in _alternates(site, page):
            other = site.pages.get(url)
            if other is None:
                continue
            if other.status_code != 200 or (other.is_html and not other.indexable()):  # noqa: PLR2004
                bad.append({"hreflang": lang, "url": url, "status": other.status_code})
        if bad:
            yield Finding(page.url, {"targets": bad[:10]})


@rule(
    "hreflang_conflict",
    title="One hreflang code points to several URLs",
    category="international",
    severity=Severity.MEDIUM,
    description="The same language/region is mapped to different URLs on one page.",
    fix="Map each hreflang code to exactly one URL.",
    effort=1,
    reference=REF,
)
def conflict(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        by_code: dict[str, set[str]] = defaultdict(set)
        for lang, url in _alternates(site, page):
            by_code[lang].add(url)
        clashes = {code: sorted(urls) for code, urls in by_code.items() if len(urls) > 1}
        if clashes:
            yield Finding(page.url, {"codes": clashes})


@rule(
    "hreflang_no_x_default",
    title="hreflang set without x-default",
    category="international",
    severity=Severity.INFO,
    description="x-default tells Google which page to show users whose language isn't listed.",
    fix="Add an x-default alternate (often the language selector or main version).",
    effort=1,
    reference=REF,
)
def no_x_default(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        codes = {lang for lang, _ in _alternates(site, page)}
        if len(codes) > 1 and "x-default" not in codes:
            yield Finding(page.url)
