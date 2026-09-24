"""XML sitemap parsing (sitemaps.org protocol), hardened for untrusted input.

``defusedxml`` rejects entity expansion, external entities and DTDs, so a hostile
sitemap cannot trigger billion-laughs or XXE. Gzip bodies are decompressed with a hard
output cap (zip-bomb safe). Google's limits: 50,000 URLs and 50 MB uncompressed.
"""

from __future__ import annotations

import gzip
import io
import zlib
from dataclasses import dataclass, field

# Type only; all parsing goes through defusedxml.
from xml.etree.ElementTree import Element  # nosec B405

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

MAX_SITEMAP_BYTES = 50 * 1024 * 1024
MAX_URLS_PER_SITEMAP = 50_000


class SitemapError(Exception):
    """The sitemap could not be read (safe to show to users)."""


@dataclass
class SitemapEntry:
    loc: str
    lastmod: str | None = None
    alternates: dict[str, str] = field(default_factory=dict)  # hreflang -> URL


@dataclass
class Sitemap:
    urls: list[SitemapEntry] = field(default_factory=list)
    children: list[str] = field(default_factory=list)  # from a <sitemapindex>
    truncated: bool = False


def _decompress(data: bytes) -> bytes:
    if not data.startswith(b"\x1f\x8b"):
        return data
    out = io.BytesIO()
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        chunk = decompressor.decompress(data, MAX_SITEMAP_BYTES + 1)
    except (zlib.error, gzip.BadGzipFile) as exc:
        raise SitemapError("The sitemap is not valid gzip.") from exc
    out.write(chunk)
    if out.tell() > MAX_SITEMAP_BYTES or decompressor.unconsumed_tail:
        raise SitemapError("The sitemap is larger than 50 MB uncompressed.")
    return out.getvalue()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: Element, name: str) -> str | None:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def parse_sitemap(data: bytes) -> Sitemap:
    body = _decompress(data)
    try:
        root = SafeET.fromstring(body)
    except (SafeET.ParseError, DefusedXmlException) as exc:
        raise SitemapError("The sitemap is not valid XML.") from exc
    result = Sitemap()
    kind = _local(root.tag)
    if kind == "sitemapindex":
        for node in root:
            if _local(node.tag) == "sitemap" and (loc := _child_text(node, "loc")):
                result.children.append(loc)
        return result
    if kind != "urlset":
        raise SitemapError("The file is not a sitemap (<urlset> or <sitemapindex>).")
    for node in root:
        if _local(node.tag) != "url":
            continue
        loc = _child_text(node, "loc")
        if not loc:
            continue
        if len(result.urls) >= MAX_URLS_PER_SITEMAP:
            result.truncated = True
            break
        entry = SitemapEntry(loc=loc, lastmod=_child_text(node, "lastmod"))
        for child in node:
            if _local(child.tag) == "link" and child.get("rel") == "alternate":
                lang, href = child.get("hreflang"), child.get("href")
                if lang and href:
                    entry.alternates[lang.lower()] = href
        result.urls.append(entry)
    return result
