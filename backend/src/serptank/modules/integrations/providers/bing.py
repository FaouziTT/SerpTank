"""Bing Webmaster Tools API (JSON endpoint, API-key auth).

Covers Bing - and so Yahoo, DuckDuckGo and Copilot grounding, which use Bing's index.
The API key is the customer's (created in Bing Webmaster Tools) and is stored encrypted.
Key-in-query is how the API works; our HTTP layer never logs full URLs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote, urlencode

from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers.base import ProviderError, request_json

API = "https://ssl.bing.com/webmaster/api.svc/json"
_MS_DATE = re.compile(r"/Date\((-?\d+)")
MAX_URL_BATCH = 500


@dataclass(frozen=True)
class BingQueryRow:
    date: date
    query: str
    clicks: int
    impressions: int
    position: float | None


def parse_ms_date(value: Any) -> date | None:
    """Bing returns WCF dates like "/Date(1719878400000-0700)/"."""
    match = _MS_DATE.search(str(value or ""))
    if not match:
        return None
    return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=UTC).date()


class BingWebmasterClient:
    def __init__(self, http: SafeHttpClient, api_key: str) -> None:
        self.http = http
        self.api_key = api_key

    def _url(self, method: str, **params: str) -> str:
        return f"{API}/{method}?{urlencode({**params, 'apikey': self.api_key})}"

    async def _get(self, method: str, **params: str) -> Any:
        data = await request_json(
            self.http,
            "GET",
            self._url(method, **params),
            provider="bing",
            label="Bing Webmaster Tools",
        )
        return (data or {}).get("d")

    async def sites(self) -> list[dict[str, Any]]:
        data = await self._get("GetUserSites")
        return [
            {"site_url": s.get("Url"), "verified": bool(s.get("IsVerified"))} for s in data or []
        ]

    async def query_stats(self, site_url: str) -> list[BingQueryRow]:
        rows: list[BingQueryRow] = []
        for item in await self._get("GetQueryStats", siteUrl=site_url) or []:
            day = parse_ms_date(item.get("Date"))
            if day is None:
                continue
            position = item.get("AvgImpressionPosition")
            rows.append(
                BingQueryRow(
                    date=day,
                    query=str(item.get("Query", ""))[:1000],
                    clicks=int(item.get("Clicks", 0) or 0),
                    impressions=int(item.get("Impressions", 0) or 0),
                    position=float(position) if position not in (None, -1) else None,
                )
            )
        return rows

    async def crawl_issues(self, site_url: str) -> list[dict[str, Any]]:
        data = await self._get("GetCrawlIssues", siteUrl=site_url)
        return [
            {"url": i.get("Url"), "issues": i.get("Issues"), "http_code": i.get("HttpCode")}
            for i in data or []
        ]

    async def submit_urls(self, site_url: str, urls: list[str]) -> None:
        if len(urls) > MAX_URL_BATCH:
            raise ProviderError(
                "bing_batch_too_large", f"Bing accepts at most {MAX_URL_BATCH} URLs per batch."
            )
        await request_json(
            self.http,
            "POST",
            self._url("SubmitUrlBatch"),
            provider="bing",
            label="Bing Webmaster Tools",
            body={"siteUrl": site_url, "urlList": urls},
        )

    async def keyword_stats(
        self, keyword: str, country: str, language: str
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "GetKeywordStats", q=keyword, country=country.lower(), language=language
        )
        return list(data or [])

    async def related_keywords(
        self, keyword: str, country: str, language: str, start: date, end: date
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "GetRelatedKeywords",
            q=keyword,
            country=country.lower(),
            language=language,
            startDate=start.isoformat(),
            endDate=end.isoformat(),
        )
        return list(data or [])


def site_url_for(domain: str) -> str:
    return f"https://{quote(domain)}/"
