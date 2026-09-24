"""Unit tests: URLs, robots.txt, sitemaps, HTML parsing, fingerprints."""

from __future__ import annotations

import gzip

import pytest

from serptank.modules.crawler.parser import parse_html, robots_directives
from serptank.modules.crawler.robots import BINGBOT, GOOGLEBOT, SERPTANKBOT, parse_robots
from serptank.modules.crawler.similarity import (
    from_signed,
    hamming,
    simhash,
    to_signed,
    words,
)
from serptank.modules.crawler.sitemaps import MAX_SITEMAP_BYTES, SitemapError, parse_sitemap
from serptank.modules.crawler.urls import (
    is_internal,
    looks_like_page,
    normalize_url,
    site_hosts,
)


# --------------------------------------------------------------------------- urls
@pytest.mark.parametrize(
    ("raw", "base", "expected"),
    [
        ("HTTPS://Example.COM:443/a/../b/./c?x=1#frag", None, "https://example.com/b/c?x=1"),
        ("/path with space", "https://example.com/dir/", "https://example.com/path%20with%20space"),
        ("../up/", "https://example.com/a/b/", "https://example.com/a/up/"),
        ("http://example.com:8080/x", None, "http://example.com:8080/x"),
        ("//cdn.example.com/y", "https://example.com/", "https://cdn.example.com/y"),
        ("https://bücher.de/", None, "https://xn--bcher-kva.de/"),
        ("https://example.com", None, "https://example.com/"),
    ],
)
def test_normalize_url(raw: str, base: str | None, expected: str) -> None:
    assert normalize_url(raw, base) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "javascript:alert(1)",
        "mailto:a@b.c",
        "tel:123",
        "#top",
        "ftp://x.com/",
        "https://user:pw@x.com/",
        "",
        "https://x.com:99999/",
    ],
)
def test_normalize_rejects(raw: str) -> None:
    assert normalize_url(raw, "https://example.com/") is None


def test_scope_helpers() -> None:
    hosts = site_hosts("example.com")
    assert hosts == {"example.com", "www.example.com"}
    assert site_hosts("www.example.com") == hosts
    assert is_internal("https://www.example.com/a", hosts)
    assert not is_internal("https://evil-example.com/", hosts)
    assert looks_like_page("https://example.com/about")
    assert looks_like_page("https://example.com/v1.2/docs/")
    assert not looks_like_page("https://example.com/logo.PNG")
    assert not looks_like_page("https://example.com/file.pdf")


# ------------------------------------------------------------------------- robots
ROBOTS = """
# comment
User-agent: *
Disallow: /private/
Allow: /private/public-page
Disallow: /*.json$
Disallow: /search?

User-agent: Googlebot
User-agent: Googlebot-Image
Disallow: /no-google/
Crawl-delay: 3

User-agent: bingbot
Disallow: /
Allow: /$
Crawl-delay: 10

Sitemap: https://example.com/sitemap.xml
Host: example.com
Clean-param: utm_source /
bogus line
"""


def test_robots_group_selection_and_precedence() -> None:
    robots = parse_robots(ROBOTS)
    assert robots.sitemaps == ["https://example.com/sitemap.xml"]
    assert robots.yandex_host == "example.com"
    assert robots.clean_params == ["utm_source /"]
    assert robots.invalid_lines == 1
    # Googlebot has its own group: the * rules do not apply to it.
    assert robots.is_allowed(GOOGLEBOT, "/private/x")
    assert not robots.is_allowed(GOOGLEBOT, "/no-google/page")
    # Our crawler falls back to *.
    assert not robots.is_allowed(SERPTANKBOT, "/private/x")
    assert robots.is_allowed(SERPTANKBOT, "/private/public-page")  # longer allow wins
    assert not robots.is_allowed(SERPTANKBOT, "/data/file.json")
    assert robots.is_allowed(SERPTANKBOT, "/data/file.json?x=1")  # $ anchors the end
    assert not robots.is_allowed(SERPTANKBOT, "/search?q=1")
    # Bing: everything blocked except the homepage.
    assert robots.is_allowed(BINGBOT, "/")
    assert not robots.is_allowed(BINGBOT, "/about")
    assert robots.crawl_delay(BINGBOT) == 10
    assert robots.crawl_delay(GOOGLEBOT) == 3
    assert robots.crawl_delay(SERPTANKBOT) is None
    # robots.txt itself is always fetchable.
    assert robots.is_allowed(BINGBOT, "/robots.txt")


def test_robots_edge_cases() -> None:
    empty = parse_robots("User-agent: *\nDisallow:\n")
    assert empty.is_allowed(SERPTANKBOT, "/anything")
    tie = parse_robots("User-agent: *\nDisallow: /page\nAllow: /page\n")
    assert tie.is_allowed(SERPTANKBOT, "/page")  # allow wins ties
    encoded = parse_robots("User-agent: *\nDisallow: /a%20b\n")
    assert not encoded.is_allowed(SERPTANKBOT, "/a b")
    assert parse_robots("Disallow: /x\n").is_allowed(SERPTANKBOT, "/x")  # rule outside a group
    assert parse_robots("").is_allowed(GOOGLEBOT, "/")


# ----------------------------------------------------------------------- sitemaps
def test_sitemap_urlset_with_hreflang() -> None:
    xml = b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
      <url><loc> https://example.com/a </loc><lastmod>2026-09-01</lastmod>
        <xhtml:link rel="alternate" hreflang="de" href="https://example.com/de/a"/></url>
      <url><loc>https://example.com/b</loc></url>
      <url></url>
    </urlset>"""
    sitemap = parse_sitemap(xml)
    assert [u.loc for u in sitemap.urls] == ["https://example.com/a", "https://example.com/b"]
    assert sitemap.urls[0].lastmod == "2026-09-01"
    assert sitemap.urls[0].alternates == {"de": "https://example.com/de/a"}


def test_sitemap_index_and_gzip() -> None:
    xml = b"""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.com/s1.xml.gz</loc></sitemap></sitemapindex>"""
    sitemap = parse_sitemap(gzip.compress(xml))
    assert sitemap.children == ["https://example.com/s1.xml.gz"]
    assert sitemap.urls == []


@pytest.mark.parametrize(
    "payload",
    [
        b"not xml at all",
        b"<html><body>hi</body></html>",
        # Entity expansion (billion laughs) and XXE are refused by defusedxml.
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]>'
        b"<urlset>&b;</urlset>",
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><urlset>&e;</urlset>',
        b"\x1f\x8b not really gzip",
    ],
)
def test_sitemap_rejects_bad_input(payload: bytes) -> None:
    with pytest.raises(SitemapError):
        parse_sitemap(payload)


def test_sitemap_gzip_bomb_is_capped() -> None:
    bomb = gzip.compress(b"<urlset>" + b" " * (MAX_SITEMAP_BYTES + 10) + b"</urlset>")
    with pytest.raises(SitemapError, match="50 MB"):
        parse_sitemap(bomb)


# -------------------------------------------------------------------------- parser
HTML = """<!doctype html><html lang="en-GB"><head>
<base href="https://example.com/base/">
<title> Hello   World </title><title>second</title>
<meta name="description" content="Desc">
<meta name="robots" content="noindex, nofollow"><meta name="googlebot" content="noarchive">
<meta name="viewport" content="width=device-width">
<meta http-equiv="refresh" content="0; url=/elsewhere">
<link rel="canonical" href="/canonical">
<link rel="alternate" hreflang="DE" href="https://example.com/de/">
<link rel="stylesheet" href="http://insecure.example.com/x.css">
<script type="application/ld+json">{"@type": "Organization", "name": "X"}</script>
<script type="application/ld+json">{broken</script>
</head><body>
<h1>Main</h1><h2>a</h2><h2>b</h2>
<a href="page">Relative</a><a href="https://other.com/" rel="nofollow ugc">Ext</a>
<a href="javascript:void(0)">js</a>
<img src="a.png"><img src="b.png" alt=""><img src="http://insecure.example.com/i.png" alt="x">
<div style="display:none">hidden words here</div>
<div itemscope itemtype="https://schema.org/Product">p</div>
<script>var notText = 1;</script><p>Some visible text.</p>
</body></html>"""


def test_parse_html_extracts_audit_facts() -> None:
    page = parse_html(HTML, "https://example.com/start")
    assert page.title == "Hello World"
    assert page.title_count == 2
    assert page.meta_description == "Desc"
    assert page.meta_robots == {"robots": ["noindex", "nofollow"], "googlebot": ["noarchive"]}
    assert page.viewport == "width=device-width"
    assert page.meta_refresh == "0; url=/elsewhere"
    assert page.canonicals == ["https://example.com/canonical"]
    assert page.hreflang == [("de", "https://example.com/de/")]
    assert page.lang == "en-GB"
    assert page.h1 == ["Main"]
    assert page.heading_counts == {"h1": 1, "h2": 2}
    assert [(link.url, link.nofollow) for link in page.links] == [
        ("https://example.com/base/page", False),
        ("https://other.com/", True),
    ]
    assert page.images == 3
    assert page.images_missing_alt == 1
    assert page.json_ld == [{"@type": "Organization", "name": "X"}]
    assert page.json_ld_errors == 1
    assert page.microdata_types == ["https://schema.org/Product"]
    assert page.hidden_words == 3
    assert "notText" not in " ".join(words("x"))
    assert page.word_count > 0
    assert len(page.insecure_resources) == 2
    data = page.to_json()
    assert data["links_count"] == 2
    assert "links" not in data


def test_robots_directives_combine_meta_and_header() -> None:
    page = parse_html('<meta name="bingbot" content="noindex">', "https://e.com/")
    assert "noindex" in robots_directives(page, [], "bingbot")
    assert "noindex" not in robots_directives(page, [], "googlebot")
    assert "noindex" in robots_directives(page, ["googlebot: noindex"], "googlebot")
    assert "noindex" not in robots_directives(page, ["otherbot: noindex"], "googlebot")
    assert {"noindex", "nofollow"} <= robots_directives(page, ["none"], "googlebot")
    assert "noindex" not in robots_directives(page, ["unavailable_after: 2030-01-01"], "googlebot")


def test_parse_html_survives_garbage() -> None:
    page = parse_html("\x00<<<>>> <a href='https://[::1'>x</a>", "https://e.com/")
    assert page.links == []
    assert page.title is None


# ---------------------------------------------------------------------- similarity
def test_simhash_similarity() -> None:
    base = words("the quick brown fox jumps over the lazy dog " * 20)
    near = words(
        "the quick brown fox jumps over the lazy cat "
        + "the quick brown fox jumps over the lazy dog " * 19
    )
    other = words("completely different content about search engine optimisation audits " * 20)
    assert hamming(simhash(base), simhash(near)) < hamming(simhash(base), simhash(other))
    assert simhash([]) == 0
    value = simhash(base)
    assert from_signed(to_signed(value)) == value
    assert -(1 << 63) <= to_signed(value) < (1 << 63)
