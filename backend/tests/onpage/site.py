"""A tiny fake web: our page plus ranking competitor pages for "trail running shoes"."""

from __future__ import annotations

import httpx

from tests.support.api import FakeInternet

KEYWORD = "trail running shoes"
COMPETITORS = [
    "www.gearlab.example",
    "www.runners.example",
    "www.outdoor.example",
    "www.blocked.example",
]

SECTIONS = [
    ("How to choose trail running shoes", "grip lugs outsole traction terrain mud rock"),
    ("Cushioning and stack height", "cushioning midsole foam stack comfort distance"),
    ("Waterproof or breathable?", "waterproof membrane breathable drainage wet feet"),
    ("Sizing and fit", "sizing fit toe box heel lockdown width"),
]


def competitor_html(index: int) -> str:
    body = "".join(
        f"<h2>{title}</h2><p>{(words + ' ') * (6 + index)} trail running shoes help runners.</p>"
        for title, words in SECTIONS
    )
    return f"""<!doctype html><html lang="en"><head>
<title>Best Trail Running Shoes {2026 - index} | Reviews</title>
<meta name="description" content="We tested trail running shoes for grip, cushioning and fit.">
<script type="application/ld+json">{{"@type": "Article", "dateModified": "2026-09-01"}}</script>
</head><body><h1>The best trail running shoes</h1>{body}</body></html>"""


OWN_HTML = """<!doctype html><html lang="en"><head>
<title>Shoes</title>
</head><body><h1>Our shoes</h1>
<p>We sell shoes. Trail running shoes are in stock. Grip matters on terrain.</p>
<img src="a.jpg"><img src="b.jpg" alt="Shoe">
</body></html>"""


def install(internet: FakeInternet, own_host: str = "www.example-shop.com") -> None:
    def robots_ok(request: httpx.Request) -> httpx.Response | None:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return None

    def own(request: httpx.Request) -> httpx.Response:
        if (r := robots_ok(request)) is not None:
            return r
        return httpx.Response(200, headers={"content-type": "text/html"}, text=OWN_HTML)

    internet.handlers[own_host] = own
    for index, host in enumerate(COMPETITORS):
        if host == "www.blocked.example":
            internet.handlers[host] = lambda r: httpx.Response(
                200, text="User-agent: SerpTankBot\nDisallow: /\n"
            )
            continue

        def page(request: httpx.Request, i: int = index) -> httpx.Response:
            if (r := robots_ok(request)) is not None:
                return r
            return httpx.Response(
                200, headers={"content-type": "text/html"}, text=competitor_html(i)
            )

        internet.handlers[host] = page
