"""Shared helpers for SerpTank's own SERP HTML parsers.

Engine markup changes often and class names are obfuscated, so the parsers anchor on
*semantic* structure (result headings inside links, section headings such as "People
also ask") rather than on class names wherever possible. A page that returns 200 but
yields no organic results raises :class:`SerpParseError` - the router then fails over
and the failure is counted, so a layout change is noticed instead of storing empties.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from selectolax.lexbor import LexborNode


class SerpParseError(Exception):
    """The HTML didn't look like a results page we understand."""


def text(node: LexborNode | None, limit: int = 500) -> str:
    if node is None:
        return ""
    return " ".join(node.text(deep=True, separator=" ").split())[:limit]


def domain_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def clean_href(href: str) -> str | None:
    """Unwrap redirect links ("/url?q=...", "/l/?uddg=...") and keep only http(s)."""
    parts = urlsplit(href)
    if parts.path in {"/url", "/l/"} and parts.query:
        params = parse_qs(parts.query)
        target = (params.get("q") or params.get("url") or params.get("uddg") or [""])[0]
        href = target
    if not href.startswith(("http://", "https://")):
        return None
    return href


def heading_texts(root: LexborNode) -> list[tuple[str, LexborNode]]:
    """(lower-cased heading text, heading node) for section headings on the page."""
    out: list[tuple[str, LexborNode]] = []
    for node in root.css('h1, h2, h3, [role="heading"]'):
        label = text(node, 120).lower()
        if label:
            out.append((label, node))
    return out
