"""DataForSEO SERP API adapter (structured JSON, all our engines except DuckDuckGo).

Uses the "live/advanced" endpoints (synchronous, all SERP elements). Their JSON is
mapped onto :class:`SerpSnapshotData`; unknown element types are kept as
``other:<type>`` features so a vendor change is visible rather than silently lost.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import urlsplit

from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient
from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.locations import location_code
from serptank.modules.search_data.schema import (
    AiAnswer,
    OrganicResult,
    SerpRequest,
    SerpSnapshotData,
)

API = "https://api.dataforseo.com/v3/serp/{engine}/organic/live/advanced"
ENGINES = frozenset({"google", "bing", "yahoo", "yandex", "baidu", "naver", "seznam"})
HTTP_OK, HTTP_TOO_MANY, HTTP_SERVER_ERROR = 200, 429, 500
POLICY = EgressPolicy(max_response_bytes=16 * 1024 * 1024, total_timeout_s=90)
_FEATURE_TYPES = {
    "featured_snippet": "featured_snippet",
    "people_also_ask": "people_also_ask",
    "local_pack": "local_pack",
    "map": "local_pack",
    "top_stories": "top_stories",
    "images": "images",
    "video": "video",
    "shopping": "shopping",
    "popular_products": "shopping",
    "knowledge_graph": "knowledge_panel",
    "related_searches": "related_searches",
    "twitter": "twitter",
    "ai_overview": "ai_overview",
}
_IGNORED = {"organic", "paid"}


def _domain(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def parse_response(payload: dict[str, Any], request: SerpRequest) -> SerpSnapshotData:
    if payload.get("status_code") != 20000:  # noqa: PLR2004
        raise CollectorError("dataforseo", f"API status {payload.get('status_code')}")
    tasks = payload.get("tasks") or []
    if not tasks or tasks[0].get("status_code") != 20000:  # noqa: PLR2004
        status = tasks[0].get("status_code") if tasks else None
        raise CollectorError("dataforseo", f"task status {status}", retryable=status != 40501)  # noqa: PLR2004
    results = tasks[0].get("result") or []
    if not results:
        raise CollectorError("dataforseo", "empty result")
    result = results[0]
    snapshot = SerpSnapshotData(
        engine=request.engine,
        query=request.query,
        country=request.country,
        language=request.language,
        device=request.device,
        location=request.location,
        total_results=result.get("se_results_count"),
    )
    features: list[str] = []
    for item in result.get("items") or []:
        kind = str(item.get("type", ""))
        if kind == "organic":
            url = str(item.get("url") or "")
            if not url:
                continue
            snapshot.organic.append(
                OrganicResult(
                    position=int(item.get("rank_group") or len(snapshot.organic) + 1),
                    absolute=item.get("rank_absolute"),
                    url=url,
                    domain=str(item.get("domain") or _domain(url)).lower(),
                    title=str(item.get("title") or "")[:300],
                    snippet=str(item.get("description") or "")[:500],
                )
            )
            if item.get("links"):
                features.append("sitelinks")
            continue
        if kind in _IGNORED:
            continue
        feature = _FEATURE_TYPES.get(kind, f"other:{kind}"[:40])
        features.append(feature)
        if kind == "ai_overview":
            refs = item.get("references") or []
            urls = [str(r.get("url")) for r in refs if r.get("url")]
            snapshot.ai_answer = AiAnswer(
                kind="ai_overview",
                cited_urls=urls[:50],
                cited_domains=sorted(
                    {
                        str(r.get("domain") or _domain(str(r.get("url", "")))).lower()
                        for r in refs
                        if r.get("url")
                    }
                ),
                text=str(item.get("markdown") or item.get("text") or "")[:4000],
            )
        elif kind == "people_also_ask":
            snapshot.people_also_ask = [
                str(q.get("title")) for q in item.get("items") or [] if q.get("title")
            ][:20]
        elif kind == "related_searches":
            snapshot.related_searches = [
                str(q) for q in item.get("items") or [] if isinstance(q, str)
            ][:20]
    snapshot.features = sorted(set(features))
    return snapshot


class DataForSeoAdapter:
    name = "dataforseo"
    engines = ENGINES

    def __init__(self, http: SafeHttpClient, login: str, password: str, cost_micros: int) -> None:
        self.http = http
        self.cost_micros = cost_micros
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._auth = f"Basic {token}"

    async def fetch(self, request: SerpRequest) -> SerpSnapshotData:
        if request.engine not in ENGINES:
            raise CollectorError(
                self.name, f"engine {request.engine} not supported", retryable=False
            )
        task: dict[str, Any] = {
            "keyword": request.query,
            "language_code": request.language.split("-")[0],
            "device": request.device,
            "depth": min(request.depth, 100),
        }
        if request.location:
            task["location_name"] = request.location
        else:
            code = location_code(request.country)
            if code is None:
                raise CollectorError(
                    self.name, f"no location code for {request.country}", retryable=False
                )
            task["location_code"] = code
        try:
            response = await self.http.request(
                "POST",
                API.format(engine=request.engine),
                headers={"authorization": self._auth, "content-type": "application/json"},
                content=json.dumps([task]).encode(),
                policy=POLICY,
            )
        except EgressError as exc:
            raise CollectorError(self.name, type(exc).__name__) from exc
        if response.status_code != HTTP_OK:
            retryable = (
                response.status_code >= HTTP_SERVER_ERROR or response.status_code == HTTP_TOO_MANY
            )
            raise CollectorError(self.name, f"HTTP {response.status_code}", retryable=retryable)
        try:
            payload = json.loads(response.content)
        except ValueError as exc:
            raise CollectorError(self.name, "invalid JSON") from exc
        return parse_response(payload, request)
