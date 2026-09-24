"""Client for the isolated renderer service, and raw-vs-rendered comparison.

The renderer is an internal service at an operator-configured address (never derived
from user input), so this client uses a plain ``httpx`` client with a bearer token. The
*pages* it renders are fetched inside the renderer through ``SafeHttpClient``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx
import structlog

from serptank.modules.crawler.parser import parse_html
from serptank.modules.crawler.robots import GOOGLEBOT, RobotsTxt
from serptank.modules.crawler.urls import is_internal, path_and_query

logger = structlog.get_logger(__name__)
RENDER_RESOURCES = frozenset({"script", "stylesheet", "image", "fetch", "xhr"})


class RendererClient:
    def __init__(
        self, base_url: str, token: str, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.AsyncClient(timeout=60, trust_env=False)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def render(
        self, url: str, *, user_agent: str, mobile: bool = False
    ) -> dict[str, Any] | None:
        try:
            response = await self._client.post(
                f"{self.base_url}/render",
                json={"url": url, "user_agent": user_agent, "mobile": mobile},
                headers={"authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            logger.warning("renderer_unreachable", error=type(exc).__name__)
            return None
        if response.status_code != 200:  # noqa: PLR2004
            logger.warning("renderer_error", status=response.status_code)
            return None
        data: dict[str, Any] = response.json()
        return data


def render_summary(
    url: str,
    raw_links: set[str],
    rendered: dict[str, Any] | None,
    robots: dict[str, RobotsTxt],
    hosts: frozenset[str],
) -> dict[str, Any]:
    """What changed after JavaScript ran, plus resources Googlebot may not fetch."""
    if rendered is None:
        return {"failed": True, "reason": "renderer_unavailable"}
    html = rendered.get("html") or ""
    if not html or rendered.get("timed_out"):
        return {"failed": True, "reason": "timeout" if rendered.get("timed_out") else "empty"}
    data = parse_html(html, url)
    js_links = sorted({link.url for link in data.links if is_internal(link.url, hosts)} - raw_links)
    blocked: list[str] = []
    for request in rendered.get("requests", []):
        target = str(request.get("url", ""))
        host = (urlsplit(target).hostname or "").lower()
        rules = robots.get(host)
        if (
            rules is not None
            and request.get("resource_type") in RENDER_RESOURCES
            and not rules.is_allowed(GOOGLEBOT, path_and_query(target))
        ):
            blocked.append(target)
    return {
        "failed": False,
        "title": data.title,
        "canonical": data.canonicals[0] if data.canonicals else None,
        "noindex": "noindex" in data.meta_robots.get("robots", [])
        or "noindex" in data.meta_robots.get("googlebot", []),
        "word_count": data.word_count,
        "js_only_links": len(js_links),
        "js_only_examples": js_links[:5],
        "blocked_for_google": sorted(set(blocked))[:20],
        "requests": len(rendered.get("requests", [])),
    }
