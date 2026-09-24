"""Mobile-first indexing and page experience (HTTPS, speed, parity)."""

from __future__ import annotations

from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site

REF_MOBILE = "https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing"
REF_HTTPS = "https://developers.google.com/search/docs/appearance/page-experience"
SLOW_MS = 1500
MAX_HTML_BYTES = 15 * 1024 * 1024
PARITY_WORDS = 0.8
PARITY_LINKS = 0.7


@rule(
    "viewport_missing",
    title="No mobile viewport",
    category="page_experience",
    severity=Severity.HIGH,
    description="Google indexes the mobile version of pages. Without a viewport meta tag, pages "
    "render as a zoomed-out desktop layout on phones.",
    fix='Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
    effort=1,
    reference=REF_MOBILE,
)
def viewport_missing(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.indexable() and not page.data.get("viewport"):
            yield Finding(page.url)


@rule(
    "not_https",
    title="Pages served over HTTP",
    category="page_experience",
    severity=Severity.HIGH,
    description="HTTPS is part of Google's page experience signals and browsers mark HTTP pages "
    "as not secure.",
    fix="Serve every page over HTTPS and redirect HTTP to HTTPS.",
    reference=REF_HTTPS,
)
def not_https(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.url.startswith("http:"):
            yield Finding(page.url)


@rule(
    "http_not_redirected",
    title="HTTP doesn't redirect to HTTPS",
    category="page_experience",
    severity=Severity.MEDIUM,
    description="The http:// homepage does not permanently redirect to https://, leaving "
    "duplicate, insecure URLs.",
    fix="Redirect all HTTP requests to HTTPS with a 301 or 308.",
    effort=1,
    reference=REF_HTTPS,
)
def http_not_redirected(site: Site) -> Iterator[Finding]:
    probe = site.site.get("https_redirect", {})
    status, location = probe.get("status"), probe.get("location") or ""
    if status is None:
        return  # port 80 closed: nothing served over HTTP
    if status not in {301, 308} or not location.startswith("https://"):
        yield Finding(None, {"status": status, "location": location or None})


@rule(
    "mixed_content",
    title="Mixed content",
    category="page_experience",
    severity=Severity.MEDIUM,
    description="HTTPS pages load scripts, styles or media over HTTP; browsers block or warn.",
    fix="Load every resource over HTTPS.",
    effort=2,
)
def mixed_content(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        insecure = page.data.get("insecure_resources") or []
        if insecure:
            yield Finding(page.url, {"resources": insecure[:5], "count": len(insecure)})


@rule(
    "slow_response",
    title="Slow server responses",
    category="page_experience",
    severity=Severity.MEDIUM,
    description=f"HTML took longer than {SLOW_MS / 1000:.1f} s to download from our crawler. "
    "Slow responses hurt Largest Contentful Paint and reduce crawl rate.",
    fix="Add caching, reduce server work or use a CDN. Field Core Web Vitals come with the "
    "PageSpeed/CrUX integration.",
    effort=3,
)
def slow_response(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.response_ms is not None and page.response_ms > SLOW_MS:
            yield Finding(page.url, {"ms": page.response_ms})


@rule(
    "html_too_large",
    title="HTML larger than 15 MB",
    category="page_experience",
    severity=Severity.HIGH,
    description="Googlebot only processes the first 15 MB of an HTML file.",
    fix="Reduce inline data and markup; load large content separately.",
    reference="https://developers.google.com/search/docs/crawling-indexing/googlebot",
)
def html_too_large(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.error == "too_large" or (page.bytes or 0) > MAX_HTML_BYTES:
            yield Finding(page.url, {"bytes": page.bytes})


@rule(
    "mobile_parity",
    title="Mobile version is missing content",
    category="page_experience",
    severity=Severity.MEDIUM,
    description="With mobile-first indexing, content, links, structured data and meta tags that "
    "only exist on desktop are invisible to Google.",
    fix="Serve the same primary content, links, structured data and meta tags to mobile users.",
    reference=REF_MOBILE,
)
def mobile_parity(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        mobile = page.mobile
        if not mobile or mobile.get("status") != 200:  # noqa: PLR2004
            continue
        problems: list[str] = []
        desktop_words = int(page.data.get("word_count") or 0)
        desktop_links = int(page.data.get("links_count", 0))
        if desktop_words and mobile.get("word_count", 0) < desktop_words * PARITY_WORDS:
            problems.append("less text")
        if desktop_links and mobile.get("links", 0) < desktop_links * PARITY_LINKS:
            problems.append("fewer links")
        if page.data.get("json_ld") and not mobile.get("json_ld"):
            problems.append("no structured data")
        if (mobile.get("title") or "") != (page.title or ""):
            problems.append("different title")
        if mobile.get("canonical") != page.canonical:
            problems.append("different canonical")
        if mobile.get("noindex") and not page.noindex("googlebot"):
            problems.append("noindex on mobile")
        if problems:
            yield Finding(page.url, {"differences": problems})


REF_CWV = "https://developers.google.com/search/docs/appearance/core-web-vitals"


def _vitals(site: Site, scope: str) -> list[dict[str, object]]:
    return [v for v in site.site.get("vitals", []) if v.get("scope") == scope]


def _cwv_details(v: dict[str, object]) -> dict[str, object]:
    return {k: v.get(k) for k in ("form_factor", "lcp_ms", "inp_ms", "cls")}


@rule(
    "cwv_origin_poor",
    title="Core Web Vitals are poor for real users",
    category="page_experience",
    severity=Severity.HIGH,
    description="Chrome UX Report field data (p75 of real visits) rates the site poor on "
    "LCP, INP or CLS. Core Web Vitals are part of Google's page experience signals.",
    fix="Start with the worst metric: LCP (server time, render-blocking resources, image "
    "size), INP (long JavaScript tasks) or CLS (reserve space for media and ads).",
    effort=3,
    reference=REF_CWV,
)
def cwv_origin_poor(site: Site) -> Iterator[Finding]:
    for v in _vitals(site, "origin"):
        if v.get("assessment") == "poor":
            yield Finding(str(v.get("target")), _cwv_details(v))


@rule(
    "cwv_origin_needs_improvement",
    title="Core Web Vitals need improvement",
    category="page_experience",
    severity=Severity.MEDIUM,
    description="Real-user Core Web Vitals miss Google's 'good' thresholds (LCP 2.5 s, INP "
    "200 ms, CLS 0.1) on at least one metric.",
    fix="Improve the metrics above their threshold; re-check after 28 days of new data.",
    effort=3,
    reference=REF_CWV,
)
def cwv_origin_needs_improvement(site: Site) -> Iterator[Finding]:
    for v in _vitals(site, "origin"):
        if v.get("assessment") == "needs_improvement":
            yield Finding(str(v.get("target")), _cwv_details(v))


@rule(
    "cwv_pages_poor",
    title="Key pages with poor Core Web Vitals",
    category="page_experience",
    severity=Severity.MEDIUM,
    description="Important URLs with enough traffic for their own field data score poor.",
    fix="Profile these pages in PageSpeed Insights and fix the failing metric.",
    effort=3,
    reference=REF_CWV,
)
def cwv_pages_poor(site: Site) -> Iterator[Finding]:
    for v in _vitals(site, "url"):
        if v.get("assessment") == "poor":
            yield Finding(str(v.get("target")), _cwv_details(v))
