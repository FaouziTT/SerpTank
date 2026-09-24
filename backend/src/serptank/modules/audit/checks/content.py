"""Titles, descriptions, headings and content quality signals."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Page, Site

REF_TITLE = "https://developers.google.com/search/docs/appearance/title-link"
REF_SNIPPET = "https://developers.google.com/search/docs/appearance/snippet"
TITLE_MAX = 60  # beyond this Google usually truncates the title link (pixel-based)
TITLE_MIN = 15
DESC_MAX = 160
THIN_WORDS = 200


def _indexable(site: Site) -> list[Page]:
    return [p for p in site.html_pages if p.indexable()]


def _duplicates(pages: list[Page], key: str) -> Iterator[Finding]:
    groups: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        value = (page.data.get(key) or "").strip().lower()
        if value:
            groups[value].append(page.url)
    for urls in groups.values():
        if len(urls) > 1:
            for url in urls:
                yield Finding(
                    url, {"shared_with": [u for u in urls if u != url][:5], "group_size": len(urls)}
                )


@rule(
    "title_missing",
    title="Missing title",
    category="content",
    severity=Severity.HIGH,
    description="Pages without a <title> force Google to invent a title link from other text.",
    fix="Give every page a unique, descriptive <title>.",
    effort=1,
    reference=REF_TITLE,
)
def title_missing(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        if not (page.title or "").strip():
            yield Finding(page.url)


@rule(
    "title_duplicate",
    title="Duplicate titles",
    category="content",
    severity=Severity.MEDIUM,
    description="Several indexable pages share the same title, which makes them hard to tell "
    "apart in results and can indicate duplicate content.",
    fix="Write a distinct title for each page that reflects its main topic.",
    reference=REF_TITLE,
)
def title_duplicate(site: Site) -> Iterator[Finding]:
    yield from _duplicates(_indexable(site), "title")


@rule(
    "title_too_long",
    title="Titles likely to be truncated",
    category="content",
    severity=Severity.LOW,
    description=f"Titles over ~{TITLE_MAX} characters are usually cut off in Google results.",
    fix="Put the most important words first and keep titles concise.",
    effort=1,
    reference=REF_TITLE,
)
def title_too_long(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        if len(page.title or "") > TITLE_MAX:
            yield Finding(page.url, {"length": len(page.title or ""), "title": page.title})


@rule(
    "title_too_short",
    title="Very short titles",
    category="content",
    severity=Severity.LOW,
    description="Very short titles rarely describe a page well enough to earn the click.",
    fix="Describe the page's topic (and brand, if useful) in the title.",
    effort=1,
    reference=REF_TITLE,
)
def title_too_short(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        title = (page.title or "").strip()
        if title and len(title) < TITLE_MIN:
            yield Finding(page.url, {"title": title})


@rule(
    "title_multiple",
    title="Multiple <title> elements",
    category="content",
    severity=Severity.LOW,
    description="Only one title is used; extra <title> elements usually come from template bugs.",
    fix="Keep a single <title> in the <head>.",
    effort=1,
)
def title_multiple(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if int(page.data.get("title_count", 0)) > 1:
            yield Finding(page.url, {"count": page.data["title_count"]})


@rule(
    "description_missing",
    title="Missing meta description",
    category="content",
    severity=Severity.LOW,
    description="Without a meta description Google builds the snippet from page text, which may "
    "not sell the page well.",
    fix="Add a concise, unique meta description summarising the page.",
    effort=1,
    reference=REF_SNIPPET,
)
def description_missing(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        if not (page.data.get("meta_description") or "").strip():
            yield Finding(page.url)


@rule(
    "description_duplicate",
    title="Duplicate meta descriptions",
    category="content",
    severity=Severity.LOW,
    description="Identical descriptions across pages are less useful as snippets.",
    fix="Write a unique description for each important page.",
    reference=REF_SNIPPET,
)
def description_duplicate(site: Site) -> Iterator[Finding]:
    yield from _duplicates(_indexable(site), "meta_description")


@rule(
    "description_too_long",
    title="Long meta descriptions",
    category="content",
    severity=Severity.INFO,
    description=f"Descriptions over ~{DESC_MAX} characters are usually truncated in snippets.",
    fix="Front-load the key message.",
    effort=1,
    reference=REF_SNIPPET,
)
def description_too_long(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        if len(page.data.get("meta_description") or "") > DESC_MAX:
            yield Finding(page.url, {"length": len(page.data["meta_description"])})


@rule(
    "h1_missing",
    title="Missing H1 heading",
    category="content",
    severity=Severity.LOW,
    description="A clear main heading helps users and search engines understand the page topic.",
    fix="Add one descriptive <h1> near the top of the main content.",
    effort=1,
)
def h1_missing(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        if not page.data.get("h1"):
            yield Finding(page.url)


@rule(
    "thin_content",
    title="Thin content",
    category="content",
    severity=Severity.LOW,
    description=f"Indexable pages with fewer than {THIN_WORDS} words. Short pages can be fine, "
    "but many thin pages can signal low value.",
    fix="Expand pages with genuinely helpful content, merge them, or noindex utility pages.",
    effort=3,
    reference="https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
)
def thin_content(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        words = int(page.data.get("word_count") or 0)
        if words < THIN_WORDS and page.found_via != "start":
            yield Finding(page.url, {"words": words})


@rule(
    "duplicate_content",
    title="Exact duplicate pages",
    category="content",
    severity=Severity.MEDIUM,
    description="These indexable URLs serve identical content. Google will pick one canonical "
    "and may not choose the one you want.",
    fix="Consolidate duplicates with 301 redirects or rel=canonical to one preferred URL.",
    reference="https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
)
def duplicate_content(site: Site) -> Iterator[Finding]:
    groups: dict[str, list[str]] = defaultdict(list)
    for page in _indexable(site):
        if page.content_hash and int(page.data.get("word_count") or 0) > 0:
            groups[page.content_hash].append(page.url)
    for urls in groups.values():
        if len(urls) > 1:
            for url in urls:
                yield Finding(url, {"duplicates": [u for u in urls if u != url][:5]})


@rule(
    "images_missing_alt",
    title="Images without alt text",
    category="content",
    severity=Severity.LOW,
    description="Alt text describes images for screen readers and Google Images.",
    fix='Add descriptive alt attributes (use alt="" for purely decorative images).',
    effort=2,
    reference="https://developers.google.com/search/docs/appearance/google-images",
)
def images_missing_alt(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        missing = int(page.data.get("images_missing_alt") or 0)
        if missing:
            yield Finding(page.url, {"images": missing})


@rule(
    "lang_missing",
    title="Missing lang attribute",
    category="content",
    severity=Severity.LOW,
    description="The <html lang> attribute declares the page language for browsers, assistive "
    "technology and some search engines.",
    fix='Add lang (e.g. <html lang="en">) to your templates.',
    effort=1,
)
def lang_missing(site: Site) -> Iterator[Finding]:
    for page in _indexable(site):
        if not page.data.get("lang"):
            yield Finding(page.url)
