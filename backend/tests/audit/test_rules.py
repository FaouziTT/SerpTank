"""Rule-level tests on hand-built sites (no database, no network)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any

import pytest

from serptank.modules.audit.evaluate import applicable, evaluate
from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import CATEGORIES, RULES, rule
from serptank.modules.audit.scoring import WEIGHTS, priority, reach, score
from serptank.modules.audit.site import Page, Site
from serptank.modules.crawler.parser import parse_html
from serptank.modules.crawler.similarity import to_signed

BASE = "https://example.com"


def html_page(path: str, html: str = "", **kw: Any) -> Page:
    url = BASE + path
    data = parse_html(html or f"<title>{path}</title><meta name=viewport content=x><h1>x</h1>", url)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "url": url,
        "status_code": 200,
        "content_type": "text/html",
        "data": data.to_json(),
        "content_hash": data.content_hash,
        "simhash": to_signed(data.simhash),
        "depth": 1,
    }
    defaults.update(kw)
    return Page(**defaults)


def make_site(*pages: Page, engines: frozenset[str] = frozenset({"google"}), **kw: Any) -> Site:
    return Site(
        start_url=f"{BASE}/",
        hosts=frozenset({"example.com", "www.example.com"}),
        engines=engines,
        pages={p.url: p for p in pages},
        **kw,
    )


def findings(site: Site, rule_id: str) -> list[str | None]:
    return [f.url for f in RULES[rule_id].check(site)]


def test_every_rule_has_complete_metadata() -> None:
    assert len(RULES) >= 60
    for r in RULES.values():
        assert r.category in CATEGORIES
        assert r.title
        assert r.description
        assert r.fix
        assert 1 <= r.effort <= 3
        assert r.scope in {"all", "google", "bing", "yandex", "baidu"}
    with pytest.raises(ValueError, match="duplicate"):
        rule(
            "title_missing",
            title="x",
            category="content",
            severity=Severity.LOW,
            description="x",
            fix="x",
        )(lambda s: [])
    with pytest.raises(ValueError, match="unknown category"):
        rule("new", title="x", category="nope", severity=Severity.LOW, description="x", fix="x")


def test_canonical_rules() -> None:
    target_redirect = Page(
        id=uuid.uuid4(), url=f"{BASE}/moved", status_code=301, redirect_to=f"{BASE}/new"
    )
    site = make_site(
        html_page("/a", f'<link rel="canonical" href="{BASE}/moved"><title>a</title>'),
        target_redirect,
        html_page("/b", '<link rel="canonical" href="/x"><link rel="canonical" href="/y">'),
        html_page("/c", '<link rel="canonical" href="https://other.org/c">'),
        html_page("/d"),
    )
    assert findings(site, "canonical_to_bad_target") == [f"{BASE}/a"]
    assert findings(site, "canonical_conflict") == [f"{BASE}/b"]
    assert findings(site, "canonical_cross_domain") == [f"{BASE}/c"]
    assert f"{BASE}/d" in findings(site, "canonical_missing")


def test_redirect_loop_and_temporary() -> None:
    site = make_site(
        Page(id=uuid.uuid4(), url=f"{BASE}/l1", status_code=301, redirect_to=f"{BASE}/l2"),
        Page(id=uuid.uuid4(), url=f"{BASE}/l2", status_code=302, redirect_to=f"{BASE}/l1"),
        Page(
            id=uuid.uuid4(), url=f"{BASE}/t", status_code=307, redirect_to=f"{BASE}/l2", error=None
        ),
        Page(id=uuid.uuid4(), url=f"{BASE}/x", error="redirect_loop"),
    )
    assert set(findings(site, "redirect_loops")) == {
        f"{BASE}/l1",
        f"{BASE}/l2",
        f"{BASE}/t",
        f"{BASE}/x",
    }
    assert set(findings(site, "temporary_redirects")) == {f"{BASE}/l2", f"{BASE}/t"}


def test_homepage_and_robots_rules() -> None:
    home = html_page(
        "/",
        '<meta name="robots" content="noindex"><title>Home</title>',
        found_via="start",
        allowed_google=False,
    )
    site = make_site(
        home, site={"robots": {"example.com": {"url": f"{BASE}/robots.txt", "status": 503}}}
    )
    assert findings(site, "homepage_blocked") == [f"{BASE}/"]
    assert findings(site, "homepage_noindex") == [f"{BASE}/"]
    assert findings(site, "robots_unreachable") == [f"{BASE}/robots.txt"]


def test_soft_404_pages() -> None:
    site = make_site(
        html_page("/p", "<title>Page not found</title>"),
        html_page("/ok", "<title>Fine</title>"),
        site={"soft404_probe": {"status": 404}},
    )
    assert findings(site, "soft_404_pages") == [f"{BASE}/p"]
    assert findings(site, "soft_404_site") == []


def test_sitemap_rules() -> None:
    site = make_site(
        site={
            "sitemaps": [
                {"url": f"{BASE}/s.xml", "status": 200, "error": "The sitemap is not valid XML."}
            ]
        }
    )
    assert findings(site, "sitemap_errors") == [f"{BASE}/s.xml"]
    assert findings(site, "sitemap_missing") == [None]
    ok = make_site(
        site={
            "sitemaps": [
                {
                    "url": f"{BASE}/sitemap.xml",
                    "status": 200,
                    "declared_in_robots": False,
                    "external_urls": 3,
                }
            ]
        }
    )
    assert findings(ok, "sitemap_missing") == []
    assert findings(ok, "sitemap_not_in_robots") == [f"{BASE}/sitemap.xml"]
    assert findings(ok, "sitemap_foreign_urls") == [f"{BASE}/sitemap.xml"]


def test_orphans_not_reported_for_partial_crawls() -> None:
    orphan = html_page("/o", found_via="sitemap", in_sitemap=True)
    assert findings(make_site(orphan), "orphan_pages") == [f"{BASE}/o"]
    assert findings(make_site(orphan, budget_exhausted=True), "orphan_pages") == []
    assert findings(make_site(orphan, budget_exhausted=True), "crawl_limited") == [None]


def test_content_rules() -> None:
    site = make_site(
        html_page("/a", "<title></title>"),
        html_page("/b", "<title>Hi</title><title>Again</title>"),
        html_page(
            "/c",
            '<title>Normal title here</title><meta name="description" content="' + "x" * 200 + '">',
        ),
        html_page("/d", "<html><title>No lang or h1 here at all</title><img src=a.png></html>"),
    )
    assert findings(site, "title_missing") == [f"{BASE}/a"]
    assert f"{BASE}/b" in findings(site, "title_too_short")
    assert findings(site, "title_multiple") == [f"{BASE}/b"]
    assert findings(site, "description_too_long") == [f"{BASE}/c"]
    assert f"{BASE}/d" in findings(site, "lang_missing")
    assert f"{BASE}/d" in findings(site, "h1_missing")
    assert findings(site, "images_missing_alt") == [f"{BASE}/d"]
    assert f"{BASE}/a" in findings(site, "thin_content")


def test_page_experience_rules() -> None:
    desktop = html_page(
        "/m",
        "<title>T</title><meta name=viewport content=x>",
        mobile={
            "status": 200,
            "title": "Other",
            "word_count": 1,
            "links": 0,
            "json_ld": 0,
            "canonical": None,
            "noindex": True,
        },
    )
    site = make_site(
        desktop,
        html_page("/slow", response_ms=4000),
        Page(id=uuid.uuid4(), url=f"{BASE}/big", error="too_large"),
        Page(
            id=uuid.uuid4(),
            url="http://example.com/insecure",
            status_code=200,
            content_type="text/html",
            data={"title": "x"},
        ),
        site={"https_redirect": {"status": 302, "location": "https://example.com/"}},
    )
    differences = next(f for f in RULES["mobile_parity"].check(site)).details["differences"]
    assert {"different title", "noindex on mobile"} <= set(differences)
    assert findings(site, "slow_response") == [f"{BASE}/slow"]
    assert findings(site, "html_too_large") == [f"{BASE}/big"]
    assert findings(site, "not_https") == ["http://example.com/insecure"]
    assert findings(site, "http_not_redirected") == [None]
    closed = make_site(site={"https_redirect": {"status": None}})
    assert findings(closed, "http_not_redirected") == []


def test_structured_data_rules() -> None:
    graph = """<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [
      {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "name": "Home"}]},
      {"@type": ["Event"], "name": "Launch"},
      {"@type": "HowTo", "name": "Do it"},
      {"@type": "Organization", "name": "Acme", "url": "https://example.com", "logo": "l.png"},
      {"@type": "Product", "name": "Widget", "offers": {"@type": "Offer", "priceCurrency": "EUR"}}
    ]}</script>"""
    site = make_site(
        html_page("/sd", graph),
        html_page("/bad", '<script type="application/ld+json">{nope</script>'),
    )
    required = next(iter(RULES["structured_data_missing_required"].check(site))).details["items"]
    by_type = {item["type"]: item["missing"] for item in required}
    assert by_type["Event"] == ["startDate", "location"]
    assert by_type["Offer"] == ["price|priceSpecification"]
    assert "itemListElement[0].position" in by_type["BreadcrumbList"]
    assert "Organization" not in by_type
    assert findings(site, "structured_data_limited_types") == [f"{BASE}/sd"]
    assert findings(site, "structured_data_invalid_json") == [f"{BASE}/bad"]


def test_hreflang_rules() -> None:
    en = html_page(
        "/en",
        f'<link rel="alternate" hreflang="en-UK" href="{BASE}/en">'
        f'<link rel="alternate" hreflang="de" href="{BASE}/de">'
        f'<link rel="alternate" hreflang="de" href="{BASE}/de2">'
        f'<link rel="alternate" hreflang="fr" href="{BASE}/fr">',
    )
    de = html_page("/de", f'<link rel="alternate" hreflang="de" href="{BASE}/de">')
    fr = Page(id=uuid.uuid4(), url=f"{BASE}/fr", status_code=404)
    site = make_site(en, de, fr)
    assert findings(site, "hreflang_invalid_code") == [f"{BASE}/en"]
    assert findings(site, "hreflang_missing_return") == [f"{BASE}/en"]
    assert findings(site, "hreflang_bad_target") == [f"{BASE}/en"]
    assert findings(site, "hreflang_conflict") == [f"{BASE}/en"]
    assert f"{BASE}/en" in findings(site, "hreflang_no_x_default")
    lonely = make_site(html_page("/x", f'<link rel="alternate" hreflang="de" href="{BASE}/y">'))
    assert findings(lonely, "hreflang_missing_self") == [f"{BASE}/x"]


def test_rendering_rules() -> None:
    page = html_page(
        "/r",
        "<title>Raw</title>",
        rendered={
            "failed": False,
            "title": "JS",
            "canonical": f"{BASE}/other",
            "noindex": True,
            "word_count": 900,
            "js_only_links": 2,
            "js_only_examples": [f"{BASE}/js"],
            "blocked_for_google": [f"{BASE}/app.js"],
        },
    )
    failed = html_page("/f", rendered={"failed": True, "reason": "timeout"})
    site = make_site(page, failed)
    changed = next(iter(RULES["js_changes_critical_tags"].check(site))).details["changed"]
    assert changed == ["title", "canonical", "robots"]
    assert findings(site, "js_dependent_content") == [f"{BASE}/r"]
    assert findings(site, "js_only_links") == [f"{BASE}/r"]
    assert findings(site, "resources_blocked_google") == [f"{BASE}/r"]
    assert findings(site, "render_failed") == [f"{BASE}/f"]


def test_spam_rules() -> None:
    hidden = html_page("/h", "<div style='display: none'>" + "keyword " * 200 + "</div>")
    near = []
    for i in range(6):
        text = (
            " ".join(["plumber in town serving all neighbourhoods with fast repairs"] * 30)
            + f" city{i}"
        )
        near.append(html_page(f"/city{i}", f"<title>Plumber city{i}</title><p>{text}</p>"))
    site = make_site(hidden, *near)
    assert findings(site, "hidden_text") == [f"{BASE}/h"]
    doorway = findings(site, "doorway_patterns")
    assert len(doorway) == 6


def test_engine_deltas_and_scope() -> None:
    robots = {
        "example.com": {
            "url": f"{BASE}/robots.txt",
            "status": 200,
            "crawl_delay": {"googlebot": 2, "bingbot": 5},
            "yandex_host": "example.com",
            "clean_params": ["x /"],
        }
    }
    home = html_page(
        "/",
        '<html lang="en"><meta name="googlebot" content="noindex"><title>Home</title></html>',
        found_via="start",
    )
    bing_only = html_page("/b", '<meta name="bingbot" content="noindex">', allowed_bing=False)
    site = make_site(
        home,
        bing_only,
        engines=frozenset({"google", "bing", "yandex", "baidu"}),
        site={"robots": robots},
    )
    assert findings(site, "google_noindex_only") == [f"{BASE}/"]
    assert findings(site, "bing_noindex_only") == [f"{BASE}/b"]
    assert findings(site, "bing_blocked_pages") == [f"{BASE}/b"]
    assert findings(site, "bing_crawl_delay") == [f"{BASE}/robots.txt"]
    assert findings(site, "google_ignores_crawl_delay") == [f"{BASE}/robots.txt"]
    assert findings(site, "yandex_directives") == [f"{BASE}/robots.txt"]
    assert findings(site, "baidu_language") == [f"{BASE}/"]
    result = evaluate(site)
    assert set(result.scores) == {"google", "bing", "yandex", "baidu"}
    google_only = evaluate(make_site(home, bing_only, site={"robots": robots}))
    assert not any(r.rule.scope == "bing" for r in google_only.results)
    assert applicable(RULES["google_noindex_only"], frozenset())


def test_scoring_curve_and_priority() -> None:
    assert score([]) == 100.0
    assert score([100.0]) == 50.0
    assert 0 < score([10_000.0]) < 1.5
    assert reach(True, 0, 0) == 1.0
    assert reach(False, 1, 0) == 0.0
    assert reach(False, 25, 100) == 0.5
    quick = RULES["homepage_noindex"]  # critical, effort 1
    slow = RULES["thin_content"]  # low, effort 3
    assert priority(quick, True, 1, 10) > priority(slow, False, 10, 10)
    assert WEIGHTS[Severity.INFO] == 0


def test_faulty_rule_is_reported_not_fatal() -> None:
    def boom(_site: Site) -> list[Any]:
        raise RuntimeError("bug")

    original = RULES["title_missing"]
    RULES["title_missing"] = replace(original, check=boom)
    try:
        result = evaluate(make_site(html_page("/a", "<title></title>")))
    finally:
        RULES["title_missing"] = original
    assert result.failed_rules == ["title_missing"]


def test_core_web_vitals_rules() -> None:
    vitals = [
        {
            "target": BASE,
            "scope": "origin",
            "form_factor": "PHONE",
            "lcp_ms": 4800,
            "inp_ms": 150,
            "cls": 0.05,
            "assessment": "poor",
        },
        {
            "target": BASE,
            "scope": "origin",
            "form_factor": "DESKTOP",
            "lcp_ms": 2900,
            "inp_ms": 150,
            "cls": 0.05,
            "assessment": "needs_improvement",
        },
        {
            "target": f"{BASE}/slow",
            "scope": "url",
            "form_factor": "PHONE",
            "lcp_ms": 6000,
            "inp_ms": 90,
            "cls": 0.3,
            "assessment": "poor",
        },
    ]
    site = make_site(site={"vitals": vitals})
    poor = list(RULES["cwv_origin_poor"].check(site))
    assert [f.details["form_factor"] for f in poor] == ["PHONE"]
    assert findings(site, "cwv_origin_needs_improvement") == [BASE]
    assert findings(site, "cwv_pages_poor") == [f"{BASE}/slow"]
    assert findings(make_site(), "cwv_origin_poor") == []  # no field data: nothing claimed
