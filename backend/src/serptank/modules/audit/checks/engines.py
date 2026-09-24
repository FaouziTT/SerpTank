"""Engine deltas: where Bing, Yandex or Baidu behave differently from Google.

These are evaluated only for engines the project tracks and never counted as Google
errors (plan §4.5). Google remains the baseline for every other rule.
"""

from __future__ import annotations

from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site


@rule(
    "bing_blocked_pages",
    title="Pages blocked for Bingbot but open to Googlebot",
    category="engines",
    severity=Severity.HIGH,
    scope="bing",
    description="robots.txt has rules for Bingbot that block pages Google can crawl. Bing also "
    "powers Yahoo, DuckDuckGo and Copilot answers.",
    fix="Align the bingbot group in robots.txt with your Googlebot rules.",
    effort=1,
    reference="https://www.bing.com/webmasters/help/how-to-create-a-robots-txt-file-cb7c31ec",
)
def bing_blocked(site: Site) -> Iterator[Finding]:
    for page in site.pages.values():
        if page.allowed_google and not page.allowed_bing:
            yield Finding(page.url)


@rule(
    "bing_noindex_only",
    title="Pages set to noindex for Bing only",
    category="engines",
    severity=Severity.MEDIUM,
    scope="bing",
    description="A bingbot-specific noindex keeps these pages out of Bing (and Yahoo/DuckDuckGo) "
    "while Google indexes them.",
    fix="Remove the bingbot noindex unless it's intentional.",
    effort=1,
)
def bing_noindex(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if page.noindex("bingbot") and not page.noindex("googlebot"):
            yield Finding(page.url)


@rule(
    "bing_crawl_delay",
    title="crawl-delay slows Bing's crawling",
    category="engines",
    severity=Severity.LOW,
    scope="bing",
    description="Bing honours crawl-delay (Google ignores it). A high delay limits how many of "
    "your pages Bing can refresh each day.",
    fix="Lower or remove crawl-delay; use Bing Webmaster Tools' crawl control instead.",
    effort=1,
    reference="https://blogs.bing.com/webmaster/2012/05/03/to-crawl-or-not-to-crawl-that-is-bingbots-question",
)
def bing_crawl_delay(site: Site) -> Iterator[Finding]:
    for host, info in site.site.get("robots", {}).items():
        delay = (info.get("crawl_delay") or {}).get("bingbot")
        if delay:
            yield Finding(info.get("url"), {"host": host, "seconds": delay})


@rule(
    "google_ignores_crawl_delay",
    title="Google ignores crawl-delay",
    category="engines",
    severity=Severity.INFO,
    scope="google",
    description="robots.txt sets crawl-delay, which Googlebot doesn't support.",
    fix="If Google crawls too fast, reduce load with caching; Google adapts its crawl rate to "
    "server errors and response times automatically.",
    effort=1,
    reference="https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate",
)
def google_crawl_delay(site: Site) -> Iterator[Finding]:
    for host, info in site.site.get("robots", {}).items():
        delays = info.get("crawl_delay") or {}
        if delays.get("googlebot"):
            yield Finding(info.get("url"), {"host": host, "seconds": delays["googlebot"]})


@rule(
    "google_noindex_only",
    title="Pages set to noindex for Google only",
    category="engines",
    severity=Severity.HIGH,
    scope="google",
    description="A googlebot-specific noindex keeps these pages out of Google while other "
    "engines index them.",
    fix="Remove the googlebot noindex unless it's intentional.",
    effort=1,
)
def google_noindex(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        if (
            page.noindex("googlebot")
            and not page.noindex("bingbot")
            and "googlebot" in page.data.get("meta_robots", {})
        ):
            yield Finding(page.url)


@rule(
    "yandex_directives",
    title="Yandex-specific robots.txt directives",
    category="engines",
    severity=Severity.INFO,
    scope="yandex",
    description="Host and Clean-param are understood only by Yandex (Host is deprecated there "
    "too; use 301 redirects to the main mirror).",
    fix="Keep Clean-param for URL parameters Yandex should ignore; replace Host with redirects.",
    effort=1,
    reference="https://yandex.com/support/webmaster/controlling-robot/robots-txt.html",
)
def yandex_directives(site: Site) -> Iterator[Finding]:
    for host, info in site.site.get("robots", {}).items():
        if info.get("yandex_host") or info.get("clean_params"):
            yield Finding(
                info.get("url"),
                {
                    "host": host,
                    "host_directive": info.get("yandex_host"),
                    "clean_params": info.get("clean_params"),
                },
            )


@rule(
    "baidu_language",
    title="Homepage isn't marked as Chinese for Baidu",
    category="engines",
    severity=Severity.INFO,
    scope="baidu",
    description="Baidu primarily ranks Simplified Chinese content, ideally hosted in mainland "
    "China with an ICP licence.",
    fix='Serve a Simplified Chinese version (lang="zh-CN") for your Baidu market.',
    effort=3,
)
def baidu_language(site: Site) -> Iterator[Finding]:
    start = site.start_page
    if start is not None and start.is_html:
        lang = (start.data.get("lang") or "").lower()
        if not lang.startswith("zh"):
            yield Finding(start.url, {"lang": lang or None})
