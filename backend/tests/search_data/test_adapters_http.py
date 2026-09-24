"""Vendor adapters over HTTP (fake transport): auth, request shape, error mapping."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import httpx
import pytest

from serptank.core.http import SafeHttpClient
from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.adapters.dataforseo import DataForSeoAdapter
from serptank.modules.search_data.adapters.rawhtml import RawHtmlAdapter
from serptank.modules.search_data.schema import SerpRequest

CORPUS = Path(__file__).parent / "corpus"


async def _resolver(_h: str, _p: int) -> list[str]:
    return ["93.184.215.34"]


def _http(handler: object) -> SafeHttpClient:
    return SafeHttpClient(resolver=_resolver, transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


async def test_dataforseo_request_and_errors() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=(CORPUS / "dataforseo_google.json").read_bytes())

    adapter = DataForSeoAdapter(_http(handler), "login", "pw", 2000)
    snap = await adapter.fetch(
        SerpRequest(
            engine="bing",
            query="best running shoes",
            country="DE",
            language="de-DE",
            device="mobile",
        )
    )
    request = seen[0]
    assert request.url.path == "/v3/serp/bing/organic/live/advanced"
    assert request.headers["authorization"] == "Basic " + base64.b64encode(b"login:pw").decode()
    task = json.loads(request.content)[0]
    assert task == {
        "keyword": "best running shoes",
        "language_code": "de",
        "device": "mobile",
        "depth": 100,
        "location_code": 2276,
    }
    assert snap.organic
    city = await adapter.fetch(
        SerpRequest(
            engine="google",
            query="q",
            country="US",
            language="en",
            location="Austin,Texas,United States",
        )
    )
    assert json.loads(seen[1].content)[0]["location_name"] == "Austin,Texas,United States"
    assert city.engine == "google"
    with pytest.raises(CollectorError) as exc:
        await adapter.fetch(
            SerpRequest(engine="duckduckgo", query="q", country="US", language="en")
        )
    assert exc.value.retryable is False
    with pytest.raises(CollectorError):
        await adapter.fetch(SerpRequest(engine="google", query="q", country="ZZ", language="en"))
    for status, retryable in ((429, True), (500, True), (401, False)):
        failing = DataForSeoAdapter(_http(lambda r, s=status: httpx.Response(s)), "l", "p", 1)
        with pytest.raises(CollectorError) as exc:
            await failing.fetch(
                SerpRequest(engine="google", query="q", country="US", language="en")
            )
        assert exc.value.retryable is retryable
    garbage = DataForSeoAdapter(
        _http(lambda r: httpx.Response(200, content=b"not json")), "l", "p", 1
    )
    with pytest.raises(CollectorError):
        await garbage.fetch(SerpRequest(engine="google", query="q", country="US", language="en"))


async def test_rawhtml_builds_vendor_url_and_parses() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        target = unquote(parse_qs(urlsplit(str(request.url)).query)["url"][0])
        if "bing.com" in target:
            return httpx.Response(
                200, text=(CORPUS / "bing.html").read_text(), headers={"content-type": "text/html"}
            )
        if "captcha" in target:
            return httpx.Response(200, text=(CORPUS / "google_captcha.html").read_text())
        return httpx.Response(
            200,
            text=(CORPUS / "google_ai_overview.html").read_text(),
            headers={"content-type": "text/html"},
        )

    adapter = RawHtmlAdapter(
        _http(handler),
        "https://unblocker.example/v1?key={key}&url={url}&cc={country}",
        "s3cret",
        1000,
    )
    snap = await adapter.fetch(
        SerpRequest(engine="google", query="best running shoes", country="US", language="en")
    )
    assert snap.ai_answer is not None
    params = parse_qs(urlsplit(str(seen[0].url)).query)
    assert params["key"] == ["s3cret"]
    assert params["cc"] == ["us"]
    assert params["url"][0].startswith("https://www.google.com/search?q=best+running+shoes")
    bing = await adapter.fetch(SerpRequest(engine="bing", query="x", country="US", language="en"))
    assert bing.organic
    with pytest.raises(CollectorError, match="parse failure"):
        await adapter.fetch(
            SerpRequest(engine="google", query="captcha", country="US", language="en")
        )
    header_auth = RawHtmlAdapter(
        _http(
            lambda r: (
                httpx.Response(200, text=(CORPUS / "duckduckgo.html").read_text())
                if r.headers.get("authorization") == "Bearer k"
                else httpx.Response(401)
            )
        ),
        "https://u.example/?url={url}",
        "k",
        1,
    )
    assert (
        await header_auth.fetch(
            SerpRequest(engine="duckduckgo", query="x", country="US", language="en")
        )
    ).organic
    down = RawHtmlAdapter(
        _http(lambda r: httpx.Response(503)), "https://u.example/?url={url}", "k", 1
    )
    with pytest.raises(CollectorError):
        await down.fetch(SerpRequest(engine="google", query="x", country="US", language="en"))
