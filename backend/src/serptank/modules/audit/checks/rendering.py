"""Raw HTML vs rendered HTML (how Google's renderer sees JavaScript sites).

Only a sample of pages is rendered (it's expensive). Findings compare what our crawler
saw in the raw HTML with the DOM after JavaScript ran in the isolated renderer.
"""

from __future__ import annotations

from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site

REF_JS = (
    "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics"
)
JS_CONTENT_RATIO = 1.5
JS_CONTENT_MIN_WORDS = 50


@rule(
    "js_changes_critical_tags",
    title="JavaScript changes title, canonical or robots directives",
    category="rendering",
    severity=Severity.HIGH,
    description="Google may use the raw or the rendered value. Changing critical tags with "
    "JavaScript leads to unpredictable indexing (and a noindex in raw HTML stops rendering).",
    fix="Output the final title, canonical and robots meta in the server HTML.",
    effort=2,
    reference=REF_JS,
)
def js_changes_critical(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        rendered = page.rendered
        if not rendered or rendered.get("failed"):
            continue
        changed = []
        if (rendered.get("title") or "") != (page.title or ""):
            changed.append("title")
        if rendered.get("canonical") != page.canonical:
            changed.append("canonical")
        if bool(rendered.get("noindex")) != page.noindex("googlebot"):
            changed.append("robots")
        if changed:
            yield Finding(page.url, {"changed": changed})


@rule(
    "js_dependent_content",
    title="Main content only appears after JavaScript",
    category="rendering",
    severity=Severity.MEDIUM,
    description="Most of the text is added by JavaScript. Google can render it, but with delay, "
    "and other search engines and AI crawlers often can't.",
    fix="Server-render (or pre-render) the main content.",
    effort=3,
    reference=REF_JS,
)
def js_dependent_content(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        rendered = page.rendered
        if not rendered or rendered.get("failed"):
            continue
        raw_words = int(page.data.get("word_count") or 0)
        js_words = int(rendered.get("word_count") or 0)
        if js_words >= JS_CONTENT_MIN_WORDS and js_words > raw_words * JS_CONTENT_RATIO:
            yield Finding(page.url, {"raw_words": raw_words, "rendered_words": js_words})


@rule(
    "js_only_links",
    title="Internal links that only exist after JavaScript",
    category="rendering",
    severity=Severity.LOW,
    description="Links injected by JavaScript are discovered later (after rendering) or not at "
    "all by some crawlers.",
    fix="Render navigation links as <a href> in the server HTML.",
    effort=2,
    reference="https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
)
def js_only_links(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        rendered = page.rendered
        if rendered and int(rendered.get("js_only_links") or 0) > 0:
            yield Finding(
                page.url,
                {
                    "links": rendered["js_only_links"],
                    "examples": rendered.get("js_only_examples", [])[:5],
                },
            )


@rule(
    "resources_blocked_google",
    title="Resources needed for rendering are blocked by robots.txt",
    category="rendering",
    severity=Severity.MEDIUM,
    description="Googlebot can't fetch these scripts or styles, so it may render the page "
    "incorrectly (for example, judging it not mobile-friendly).",
    fix="Allow Googlebot to fetch CSS, JavaScript and images the page needs.",
    effort=1,
    reference=REF_JS,
)
def resources_blocked(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        rendered = page.rendered
        blocked = (rendered or {}).get("blocked_for_google") or []
        if blocked:
            yield Finding(page.url, {"resources": blocked[:10], "count": len(blocked)})


@rule(
    "render_failed",
    title="Pages failed to render",
    category="rendering",
    severity=Severity.LOW,
    description="The page timed out or errored in a headless browser; Google's renderer may "
    "have the same problem.",
    fix="Check the page for long-running scripts or failing resources.",
    effort=2,
    reference=REF_JS,
)
def render_failed(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.rendered and page.rendered.get("failed"):
            yield Finding(page.url, {"reason": page.rendered.get("reason")})
