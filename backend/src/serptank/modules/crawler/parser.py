"""HTML extraction for audits (selectolax/lexbor: fast, no network, no script execution).

Crawled HTML is untrusted: we only read it. Nothing extracted here is ever rendered as
HTML in the product; strings are length-capped before storage.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from selectolax.lexbor import LexborHTMLParser, LexborNode

from serptank.modules.crawler.similarity import content_hash, simhash, words
from serptank.modules.crawler.urls import normalize_url

MAX_TEXT = 500
MAX_LINKS_PER_PAGE = 1000
MAX_JSONLD_BLOCKS = 20
MAX_JSONLD_BYTES = 200_000
ROBOTS_META_NAMES = ("robots", "googlebot", "bingbot")
_HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:px|em|rem)?\s*(?:;|$)"
    r"|text-indent\s*:\s*-\d{3,}",
    re.IGNORECASE,
)


def _cap(value: str | None, limit: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value[:limit]


@dataclass
class Link:
    url: str
    anchor: str
    nofollow: bool


@dataclass
class PageData:
    title: str | None = None
    title_count: int = 0
    meta_description: str | None = None
    meta_description_count: int = 0
    # Directives per meta name: "robots", "googlebot" and "bingbot".
    meta_robots: dict[str, list[str]] = field(default_factory=dict)
    canonicals: list[str] = field(default_factory=list)
    hreflang: list[tuple[str, str]] = field(default_factory=list)
    h1: list[str] = field(default_factory=list)
    heading_counts: dict[str, int] = field(default_factory=dict)
    lang: str | None = None
    viewport: str | None = None
    meta_refresh: str | None = None
    links: list[Link] = field(default_factory=list)
    images: int = 0
    images_missing_alt: int = 0
    json_ld: list[Any] = field(default_factory=list)
    json_ld_errors: int = 0
    microdata_types: list[str] = field(default_factory=list)
    word_count: int = 0
    content_hash: str = ""
    simhash: int = 0
    hidden_words: int = 0
    insecure_resources: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["links_count"] = len(data.pop("links"))
        data.pop("simhash")
        return data


def _attr(node: LexborNode, name: str) -> str:
    value = node.attributes.get(name)
    return value.strip() if isinstance(value, str) else ""


def _head(tree: LexborHTMLParser, page: PageData, url: str, base: str) -> None:  # noqa: PLR0912
    html_node = tree.css_first("html")
    if html_node is not None:
        page.lang = _cap(_attr(html_node, "lang"), 35) or None
    titles = tree.css("head title") or tree.css("title")
    page.title_count = len(titles)
    if titles:
        page.title = _cap(titles[0].text(deep=True)) or ""
    for meta in tree.css("meta[name]"):
        name = _attr(meta, "name").lower()
        content = _attr(meta, "content")
        if name == "description":
            page.meta_description_count += 1
            if page.meta_description is None:
                page.meta_description = _cap(content) or ""
        elif name in ROBOTS_META_NAMES:
            directives = [d.strip().lower() for d in content.split(",") if d.strip()]
            page.meta_robots.setdefault(name, []).extend(directives)
        elif name == "viewport":
            page.viewport = _cap(content, 200)
    for meta in tree.css("meta[http-equiv]"):
        if _attr(meta, "http-equiv").lower() == "refresh":
            page.meta_refresh = _cap(_attr(meta, "content"), 300)
    for link in tree.css("link[rel]"):
        rel = _attr(link, "rel").lower().split()
        href = _attr(link, "href")
        if not href:
            continue
        target = normalize_url(href, base)
        if "canonical" in rel and target:
            page.canonicals.append(target)
        if "alternate" in rel and link.attributes.get("hreflang") and target:
            page.hreflang.append((_attr(link, "hreflang").lower(), target))
        if "stylesheet" in rel and url.startswith("https:") and href.startswith("http:"):
            page.insecure_resources.append(href[:300])


def _body_elements(tree: LexborHTMLParser, page: PageData, url: str, base: str) -> None:
    for level in range(1, 7):
        nodes = tree.css(f"h{level}")
        if nodes:
            page.heading_counts[f"h{level}"] = len(nodes)
        if level == 1:
            page.h1 = [text for n in nodes[:10] if (text := _cap(n.text(deep=True), 300))]
    for anchor in tree.css("a[href]"):
        if len(page.links) >= MAX_LINKS_PER_PAGE:
            break
        target = normalize_url(_attr(anchor, "href"), base)
        if target is None:
            continue
        rel = _attr(anchor, "rel").lower().split()
        page.links.append(
            Link(
                url=target,
                anchor=_cap(anchor.text(deep=True), 200) or "",
                nofollow=bool({"nofollow", "ugc", "sponsored"} & set(rel)),
            )
        )
    images = tree.css("img")
    page.images = len(images)
    page.images_missing_alt = sum(1 for img in images if "alt" not in img.attributes)
    if url.startswith("https:"):
        for node in tree.css("img[src], script[src], iframe[src], video[src], audio[src]"):
            if _attr(node, "src").startswith("http:"):
                page.insecure_resources.append(_attr(node, "src")[:300])
    page.insecure_resources = page.insecure_resources[:20]


def _structured_data(tree: LexborHTMLParser, page: PageData) -> None:
    for script in tree.css('script[type="application/ld+json"]')[:MAX_JSONLD_BLOCKS]:
        raw = script.text(deep=True)
        if len(raw) > MAX_JSONLD_BYTES:
            page.json_ld_errors += 1
            continue
        try:
            page.json_ld.append(json.loads(raw))
        except ValueError:
            page.json_ld_errors += 1
    page.microdata_types = sorted(
        {_attr(n, "itemtype")[:200] for n in tree.css("[itemtype]") if _attr(n, "itemtype")}
    )[:20]


def _text(tree: LexborHTMLParser, page: PageData) -> None:
    page.hidden_words = sum(
        len(words(node.text(deep=True, separator=" ")))
        for node in tree.css("[style]")
        if _HIDDEN_STYLE.search(_attr(node, "style"))
    )
    body = tree.body
    tokens: list[str] = []
    if body is not None:
        for node in body.css("script, style, noscript, template"):
            node.decompose()
        tokens = words(body.text(deep=True, separator=" "))
    page.word_count = len(tokens)
    page.content_hash = content_hash(tokens)
    page.simhash = simhash(tokens)


def parse_html(html: str, url: str) -> PageData:
    tree = LexborHTMLParser(html)
    page = PageData()
    base = url
    base_node = tree.css_first("base[href]")
    if base_node is not None:
        base = normalize_url(_attr(base_node, "href"), url) or url
    _head(tree, page, url, base)
    _body_elements(tree, page, url, base)
    _structured_data(tree, page)
    _text(tree, page)  # last: it removes script/style nodes from the tree
    return page


def robots_directives(page: PageData, header_values: list[str], bot: str) -> set[str]:
    """Effective indexing directives for ``bot`` ("googlebot"/"bingbot") from meta + header."""
    directives = set(page.meta_robots.get("robots", [])) | set(page.meta_robots.get(bot, []))
    for header in header_values:
        # X-Robots-Tag is "noindex" or bot-scoped, e.g. "googlebot: noindex, nofollow".
        value = header
        scope, sep, rest = header.partition(":")
        agent = scope.strip().lower()
        if sep and agent != "unavailable_after" and " " not in agent:
            if agent != bot:
                continue
            value = rest
        directives |= {d.strip().lower() for d in value.split(",") if d.strip()}
    if "none" in directives:
        directives |= {"noindex", "nofollow"}
    return directives
