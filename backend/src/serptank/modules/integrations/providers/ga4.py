"""GA4 Data API: organic-search landing pages (sessions, engagement, key events, revenue)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers.base import request_json

API = "https://analyticsdata.googleapis.com/v1beta"
ADMIN = "https://analyticsadmin.googleapis.com/v1beta"
LIMIT = 100_000


@dataclass(frozen=True)
class Ga4Row:
    date: date
    landing_page: str
    sessions: int
    engaged_sessions: int
    conversions: float
    revenue: float


class Ga4Client:
    def __init__(self, http: SafeHttpClient, access_token: str) -> None:
        self.http = http
        self.headers = {"authorization": f"Bearer {access_token}"}

    async def properties(self) -> list[dict[str, str]]:
        data = await request_json(
            self.http,
            "GET",
            f"{ADMIN}/accountSummaries?pageSize=200",
            provider="ga4",
            label="Google Analytics",
            headers=self.headers,
        )
        out: list[dict[str, str]] = []
        for account in (data or {}).get("accountSummaries", []):
            for prop in account.get("propertySummaries", []):
                out.append(
                    {"property_id": str(prop.get("property")), "name": str(prop.get("displayName"))}
                )
        return out

    async def organic_landing_pages(self, property_id: str, start: date, end: date) -> list[Ga4Row]:
        if not property_id.startswith("properties/"):
            property_id = f"properties/{property_id}"
        data = await request_json(
            self.http,
            "POST",
            f"{API}/{property_id}:runReport",
            provider="ga4",
            label="Google Analytics",
            headers=self.headers,
            body={
                "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
                "dimensions": [{"name": "date"}, {"name": "landingPagePlusQueryString"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "engagedSessions"},
                    {"name": "keyEvents"},
                    {"name": "totalRevenue"},
                ],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "sessionDefaultChannelGroup",
                        "stringFilter": {"value": "Organic Search"},
                    }
                },
                "limit": LIMIT,
            },
        )
        rows: list[Ga4Row] = []
        for row in (data or {}).get("rows", []):
            dims = [d.get("value", "") for d in row.get("dimensionValues", [])]
            mets = [m.get("value", "0") for m in row.get("metricValues", [])]
            if len(dims) != 2 or len(mets) != 4:  # noqa: PLR2004
                continue
            raw_date = dims[0]
            rows.append(
                Ga4Row(
                    date=date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8])),
                    landing_page=dims[1][:2048],
                    sessions=int(float(mets[0])),
                    engaged_sessions=int(float(mets[1])),
                    conversions=float(mets[2]),
                    revenue=float(mets[3]),
                )
            )
        return rows
