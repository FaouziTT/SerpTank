"""Google Ads API Keyword Planner (official search volume, competition, CPC ranges).

Requires SerpTank's developer token (Basic Access, granted per Google Cloud project)
plus the customer's OAuth grant (``adwords`` scope) and Ads customer ID. Volumes are
exact only for accounts with ad spend; otherwise Google returns ranges and we store
them as such - never as invented precise numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers.base import request_json

API = "https://googleads.googleapis.com"
# Google Ads geo target and language constants for common markets (subset; extendable).
GEO_TARGETS = {
    "US": 2840,
    "GB": 2826,
    "DE": 2276,
    "FR": 2250,
    "NL": 2528,
    "ES": 2724,
    "IT": 2380,
    "CA": 2124,
    "AU": 2036,
    "IN": 2356,
    "BR": 2076,
    "JP": 2392,
}
LANGUAGES = {
    "en": 1000,
    "de": 1001,
    "fr": 1002,
    "es": 1003,
    "it": 1004,
    "ja": 1005,
    "nl": 1010,
    "pt": 1014,
}


@dataclass(frozen=True)
class KeywordIdea:
    keyword: str
    avg_monthly_searches: int | None
    competition: str | None
    competition_index: int | None
    low_bid_micros: int | None
    high_bid_micros: int | None
    monthly: list[dict[str, Any]]


class KeywordPlannerClient:
    def __init__(
        self,
        http: SafeHttpClient,
        *,
        access_token: str,
        developer_token: str,
        api_version: str,
        login_customer_id: str = "",
    ) -> None:
        self.http = http
        self.api_version = api_version
        self.headers = {
            "authorization": f"Bearer {access_token}",
            "developer-token": developer_token,
        }
        if login_customer_id:
            self.headers["login-customer-id"] = login_customer_id.replace("-", "")

    async def ideas(
        self, customer_id: str, keywords: list[str], country: str, language: str
    ) -> list[KeywordIdea]:
        cid = customer_id.replace("-", "")
        body: dict[str, Any] = {
            "keywordSeed": {"keywords": keywords[:20]},
            "keywordPlanNetwork": "GOOGLE_SEARCH",
            "includeAdultKeywords": False,
        }
        if country.upper() in GEO_TARGETS:
            body["geoTargetConstants"] = [f"geoTargetConstants/{GEO_TARGETS[country.upper()]}"]
        lang = language.split("-", maxsplit=1)[0].lower()
        if lang in LANGUAGES:
            body["language"] = f"languageConstants/{LANGUAGES[lang]}"
        data = await request_json(
            self.http,
            "POST",
            f"{API}/{self.api_version}/customers/{cid}:generateKeywordIdeas",
            provider="google_ads",
            label="Google Ads",
            headers=self.headers,
            body=body,
        )
        ideas: list[KeywordIdea] = []
        for result in (data or {}).get("results", []):
            metrics = result.get("keywordIdeaMetrics") or {}

            def as_int(value: Any) -> int | None:
                return int(value) if value not in (None, "") else None

            ideas.append(
                KeywordIdea(
                    keyword=str(result.get("text", "")),
                    avg_monthly_searches=as_int(metrics.get("avgMonthlySearches")),
                    competition=metrics.get("competition"),
                    competition_index=as_int(metrics.get("competitionIndex")),
                    low_bid_micros=as_int(metrics.get("lowTopOfPageBidMicros")),
                    high_bid_micros=as_int(metrics.get("highTopOfPageBidMicros")),
                    monthly=[
                        {
                            "year": m.get("year"),
                            "month": m.get("month"),
                            "searches": as_int(m.get("monthlySearches")),
                        }
                        for m in metrics.get("monthlySearchVolumes", [])
                    ],
                )
            )
        return ideas
