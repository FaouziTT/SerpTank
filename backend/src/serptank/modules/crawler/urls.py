"""URL normalization and scope rules for the crawler.

Normalization keeps what can change the response (path, query) and drops what cannot
(fragment, default port, case of scheme/host), so one page maps to one crawl key.
"""

from __future__ import annotations

import posixpath
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

# Resources that are never HTML pages; we record links to them but do not fetch them.
SKIP_EXTENSIONS = frozenset(
    {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp",
        ".css", ".js", ".mjs", ".json", ".xml", ".txt", ".pdf", ".zip", ".gz", ".rar",
        ".7z", ".tar", ".mp3", ".mp4", ".m4a", ".mov", ".avi", ".webm", ".wav", ".ogg",
        ".woff", ".woff2", ".ttf", ".otf", ".eot", ".exe", ".dmg", ".apk", ".doc",
        ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".rss", ".atom",
    }
)  # fmt: skip
MAX_URL_LENGTH = 2048
_SAFE_PATH = "/%:@!$&'()*+,;=-._~"
_SAFE_QUERY = "/?%:@!$&'()*+,;=-._~"


def normalize_url(url: str, base: str | None = None) -> str | None:
    """Absolute, normalized http(s) URL, or ``None`` if it is not crawlable."""
    raw = url.strip()
    if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:", "#")):
        return None
    try:
        absolute = urljoin(base, raw) if base else raw
        parts = urlsplit(absolute)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname or parts.username:
        return None
    host = parts.hostname.lower().rstrip(".")
    try:
        host = host.encode("idna").decode("ascii") if not host.isascii() else host
    except UnicodeError:
        return None
    netloc = host if port in (None, 80 if scheme == "http" else 443) else f"{host}:{port}"
    path = parts.path or "/"
    trailing = path.endswith("/")
    path = posixpath.normpath(unquote(path)) if path not in {"", "/"} else "/"
    if path == ".":
        path = "/"
    if trailing and not path.endswith("/"):
        path += "/"
    path = quote(path, safe=_SAFE_PATH)
    query = quote(unquote(parts.query), safe=_SAFE_QUERY) if parts.query else ""
    normalized = urlunsplit((scheme, netloc, path, query, ""))
    return normalized if len(normalized) <= MAX_URL_LENGTH else None


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def site_hosts(primary_domain: str) -> frozenset[str]:
    """Hosts that belong to the project's site: the domain and its www twin."""
    domain = primary_domain.lower()
    twin = domain[4:] if domain.startswith("www.") else f"www.{domain}"
    return frozenset({domain, twin})


def is_internal(url: str, hosts: frozenset[str]) -> bool:
    return host_of(url) in hosts


def looks_like_page(url: str) -> bool:
    path = urlsplit(url).path.lower()
    dot = path.rfind(".")
    return dot == -1 or path.rfind("/") > dot or path[dot:] not in SKIP_EXTENSIONS


def path_and_query(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
