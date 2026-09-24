"""A small website with known defects, served through the fake internet.

Each defect maps to an audit rule the golden test expects (see test_pipeline.py).
"""

from __future__ import annotations

import json

import httpx

HOST = "fixture-site.com"
BASE = f"https://{HOST}"

ROBOTS = f"""
User-agent: *
Disallow: /private/

User-agent: bingbot
Disallow: /bing-blocked/
Crawl-delay: 5

Sitemap: {BASE}/sitemap.xml
"""

SITEMAP_URLS = ["/", "/about", "/orphan", "/noindexed", "/gone", "/old", "/private/secret"]
SITEMAP = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    + "".join(f"<url><loc>{BASE}{path}</loc></url>" for path in SITEMAP_URLS)
    + "</urlset>"
)

LOREM = " ".join(f"word{i}" for i in range(260))


def page(
    title: str,
    body: str,
    *,
    head: str = "",
    viewport: bool = True,
    description: str | None = "A helpful page.",
    canonical: str | None = None,
) -> str:
    parts = [f"<title>{title}</title>"]
    if viewport:
        parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    if description:
        parts.append(f'<meta name="description" content="{description}">')
    if canonical:
        parts.append(f'<link rel="canonical" href="{canonical}">')
    parts.append(head)
    return f'<!doctype html><html lang="en"><head>{"".join(parts)}</head><body>{body}</body></html>'


PRODUCT_JSONLD = json.dumps(
    {"@context": "https://schema.org", "@type": "Product", "name": "Widget"}
)

PAGES: dict[str, str] = {
    "/": page(
        "Fixture Site - Home",
        f"<h1>Welcome</h1><p>{LOREM}</p>"
        '<a href="/about">About</a> <a href="/products">Products</a> <a href="/old">Old</a>'
        ' <a href="/gone">Gone</a> <a href="/private/secret">Secret</a>'
        ' <a href="/bing-blocked/page">Bing</a> <a href="/dup-a">A</a> <a href="/dup-b">B</a>'
        ' <a href="/noindexed">Noindexed</a> <a href="https://other.example.org/">External</a>'
        ' <a href="/contact" rel="nofollow">Contact</a>',
        head=f'<script type="application/ld+json">{PRODUCT_JSONLD}</script>',
        canonical=f"{BASE}/",
    ),
    "/about": page(
        "About the fixture site and everything it stands for in this very long title",
        f"<h1>About</h1><p>{LOREM}</p><a href='/'>Home</a>",
        description=None,
        canonical=f"{BASE}/about",
        head=f'<link rel="alternate" hreflang="en" href="{BASE}/about">'
        f'<link rel="alternate" hreflang="de" href="{BASE}/de/about">',
    ),
    "/de/about": page(
        "Über uns", f"<h1>Über uns</h1><p>{LOREM} extra</p>", canonical=f"{BASE}/de/about"
    ),
    "/products": page(
        "Products",
        f"<h1>Products</h1><p>{LOREM} products</p><img src='http://cdn.example.net/x.png' alt='x'>",
        viewport=False,
        canonical=f"{BASE}/products",
    ),
    "/noindexed": page(
        "Noindexed",
        f"<h1>Hidden</h1><p>{LOREM}</p>",
        head='<meta name="robots" content="noindex">',
    ),
    "/orphan": page("Orphan", f"<h1>Orphan</h1><p>{LOREM} orphan</p>", canonical=f"{BASE}/orphan"),
    "/dup-a": page("Duplicate", f"<h1>Dup</h1><p>{LOREM} same</p>"),
    "/dup-b": page("Duplicate", f"<h1>Dup</h1><p>{LOREM} same</p>"),
    "/bing-blocked/page": page("Bing blocked", f"<h1>Bing</h1><p>{LOREM} bing</p>"),
    "/private/secret": page("Secret", "<h1>Secret</h1>"),
    "/about-2": page("About 2", "<p>x</p>"),
}
REDIRECTS = {"/old": "/old2", "/old2": "/about"}


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.url.scheme == "http":
        return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGES["/"])
    if path == "/robots.txt":
        return httpx.Response(200, headers={"content-type": "text/plain"}, text=ROBOTS)
    if path == "/sitemap.xml":
        return httpx.Response(200, headers={"content-type": "application/xml"}, text=SITEMAP)
    if path in REDIRECTS:
        return httpx.Response(301, headers={"location": REDIRECTS[path]})
    if path == "/gone":
        return httpx.Response(
            404, headers={"content-type": "text/html"}, text=page("Not found", "")
        )
    html = PAGES.get(path)
    if html is None:
        # Soft-404 defect: unknown URLs answer 200 with a generic page.
        html = page("Fixture Site", "<h1>Oops</h1><p>We could not find that.</p>")
    return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html)
