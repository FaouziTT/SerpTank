"""Google Search Console API: Search Analytics, URL Inspection, sitemaps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import quote

from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers.base import ProviderError, request_json

API = "https://searchconsole.googleapis.com"
WEBMASTERS = "https://www.googleapis.com/webmasters/v3"
ROW_LIMIT = 25_000  # API maximum per request
MAX_ROWS_PER_DAY = 200_000


@dataclass(frozen=True)
class GscRow:
    date: date
    query: str
    page: str
    country: str
    device: str
    clicks: int
    impressions: int
    position: float


class GscClient:
    def __init__(self, http: SafeHttpClient, access_token: str) -> None:
        self.http = http
        self.headers = {"authorization": f"Bearer {access_token}"}

    async def _call(self, method: str, url: str, body: Any = None) -> Any:
        return await request_json(
            self.http,
            method,
            url,
            provider="gsc",
            label="Search Console",
            headers=self.headers,
            body=body,
        )

    async def sites(self) -> list[dict[str, str]]:
        data = await self._call("GET", f"{WEBMASTERS}/sites")
        return [
            {"site_url": str(s.get("siteUrl")), "permission": str(s.get("permissionLevel"))}
            for s in (data or {}).get("siteEntry", [])
            if s.get("permissionLevel") != "siteUnverifiedUser"
        ]

    async def search_analytics(self, site_url: str, day: date) -> list[GscRow]:
        """All rows for one day (paged), by query, page, country and device."""
        rows: list[GscRow] = []
        start = 0
        url = f"{WEBMASTERS}/sites/{quote(site_url, safe='')}/searchAnalytics/query"
        while start < MAX_ROWS_PER_DAY:
            data = await self._call(
                "POST",
                url,
                {
                    "startDate": day.isoformat(),
                    "endDate": day.isoformat(),
                    "dimensions": ["query", "page", "country", "device"],
                    "type": "web",
                    "dataState": "final",
                    "rowLimit": ROW_LIMIT,
                    "startRow": start,
                },
            )
            batch = (data or {}).get("rows", [])
            for row in batch:
                keys = row.get("keys", [])
                if len(keys) != 4:  # noqa: PLR2004
                    continue
                rows.append(
                    GscRow(
                        date=day,
                        query=str(keys[0])[:1000],
                        page=str(keys[1])[:2048],
                        country=str(keys[2])[:3],
                        device=str(keys[3]).lower()[:10],
                        clicks=int(row.get("clicks", 0)),
                        impressions=int(row.get("impressions", 0)),
                        position=float(row.get("position", 0.0)),
                    )
                )
            if len(batch) < ROW_LIMIT:
                break
            start += ROW_LIMIT
        return rows

    async def inspect(self, site_url: str, url: str, language: str = "en-US") -> dict[str, Any]:
        data = await self._call(
            "POST",
            f"{API}/v1/urlInspection/index:inspect",
            {"inspectionUrl": url, "siteUrl": site_url, "languageCode": language},
        )
        result = (data or {}).get("inspectionResult", {})
        if not isinstance(result, dict):
            raise ProviderError("gsc_bad_response", "Search Console returned no inspection result.")
        return result

    async def sitemaps(self, site_url: str) -> list[dict[str, Any]]:
        data = await self._call("GET", f"{WEBMASTERS}/sites/{quote(site_url, safe='')}/sitemaps")
        return [
            {
                "path": s.get("path"),
                "last_submitted": s.get("lastSubmitted"),
                "last_downloaded": s.get("lastDownloaded"),
                "is_pending": s.get("isPending"),
                "errors": int(s.get("errors", 0) or 0),
                "warnings": int(s.get("warnings", 0) or 0),
            }
            for s in (data or {}).get("sitemap", [])
        ]

    async def submit_sitemap(self, site_url: str, sitemap_url: str) -> None:
        await self._call(
            "PUT",
            f"{WEBMASTERS}/sites/{quote(site_url, safe='')}/sitemaps/{quote(sitemap_url, safe='')}",
        )
