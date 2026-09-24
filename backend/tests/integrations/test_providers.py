"""Provider adapters in isolation (recorded-style fixtures through the fake internet)."""

from __future__ import annotations

import json

import httpx
import pytest

from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.providers import indexnow
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.bing import BingWebmasterClient
from serptank.modules.integrations.providers.google_ads import KeywordPlannerClient

IDEAS = {
    "results": [
        {
            "text": "running shoes",
            "keywordIdeaMetrics": {
                "avgMonthlySearches": "90500",
                "competition": "HIGH",
                "competitionIndex": "100",
                "lowTopOfPageBidMicros": "450000",
                "highTopOfPageBidMicros": "1900000",
                "monthlySearchVolumes": [
                    {"year": "2026", "month": "AUGUST", "monthlySearches": "90500"}
                ],
            },
        },
        {"text": "trail shoes", "keywordIdeaMetrics": {}},
    ]
}


async def _resolver(_host: str, _port: int) -> list[str]:
    return ["93.184.215.34"]


def _client(handler: httpx.MockTransport) -> SafeHttpClient:
    return SafeHttpClient(resolver=_resolver, transport=handler)


async def test_keyword_planner_request_and_parsing() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=IDEAS)

    http = _client(httpx.MockTransport(handler))
    planner = KeywordPlannerClient(
        http,
        access_token="tok",
        developer_token="dev",
        api_version="v22",
        login_customer_id="123-456-7890",
    )
    ideas = await planner.ideas("111-222-3333", ["running shoes"], "US", "en-US")
    request = seen[0]
    assert request.url.path == "/v22/customers/1112223333:generateKeywordIdeas"
    assert request.headers["developer-token"] == "dev"
    assert request.headers["login-customer-id"] == "1234567890"
    body = json.loads(request.content)
    assert body["geoTargetConstants"] == ["geoTargetConstants/2840"]
    assert body["language"] == "languageConstants/1000"
    assert ideas[0].avg_monthly_searches == 90500
    assert ideas[0].competition == "HIGH"
    assert ideas[0].monthly[0]["searches"] == 90500
    # Missing metrics stay missing (never invented).
    assert ideas[1].avg_monthly_searches is None
    await http.aclose()


async def test_keyword_planner_errors_are_user_safe() -> None:
    http = _client(
        httpx.MockTransport(
            lambda r: httpx.Response(
                403, json={"error": {"message": "DEVELOPER_TOKEN_NOT_APPROVED internal detail"}}
            )
        )
    )
    planner = KeywordPlannerClient(http, access_token="t", developer_token="d", api_version="v22")
    with pytest.raises(ProviderError) as exc:
        await planner.ideas("1112223333", ["x"], "ZZ", "xx")
    assert "internal detail" not in exc.value.message
    await http.aclose()


async def test_bing_keywords_and_submission() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path.rsplit("/", 1)[-1])
        if request.url.path.endswith("SubmitUrlBatch"):
            assert json.loads(request.content)["urlList"] == ["https://s.com/a"]
            return httpx.Response(200, json={"d": None})
        return httpx.Response(200, json={"d": [{"Query": "widgets", "Impressions": 10}]})

    http = _client(httpx.MockTransport(handler))
    client = BingWebmasterClient(http, "k")
    assert (await client.keyword_stats("widgets", "US", "en-US"))[0]["Query"] == "widgets"
    await client.submit_urls("https://s.com/", ["https://s.com/a"])
    with pytest.raises(ProviderError):
        await client.submit_urls("https://s.com/", ["https://s.com/"] * 501)
    assert calls == ["GetKeywordStats", "SubmitUrlBatch"]
    await http.aclose()


async def test_indexnow_guards() -> None:
    http = _client(httpx.MockTransport(lambda r: httpx.Response(200)))
    key = indexnow.new_key()
    assert indexnow.KEY_RE.match(key)
    assert await indexnow.submit(http, "https://api.indexnow.org/indexnow", "s.com", key, []) == 200
    with pytest.raises(ProviderError, match="invalid"):
        await indexnow.submit(
            http, "https://api.indexnow.org/indexnow", "s.com", "bad key!", ["https://s.com/"]
        )
    with pytest.raises(ProviderError, match="own host"):
        await indexnow.submit(
            http, "https://api.indexnow.org/indexnow", "s.com", key, ["https://evil.com/"]
        )
    await http.aclose()
