"""Raw-HTML collector: any "unblocker"/scraping API that returns the SERP's HTML.

Turns commodity fetch vendors into sources for *our* parsers (plan §4.6), so switching
vendors is a configuration change. The vendor URL is operator-configured; the SERP URL
we ask it to fetch is built here from validated inputs only.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlencode

from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient
from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.parsers.bing import parse_bing
from serptank.modules.search_data.parsers.common import SerpParseError
from serptank.modules.search_data.parsers.duckduckgo import parse_duckduckgo
from serptank.modules.search_data.parsers.google import parse_google
from serptank.modules.search_data.schema import SerpRequest, SerpSnapshotData

POLICY = EgressPolicy(
    max_response_bytes=8 * 1024 * 1024, total_timeout_s=90, allowed_content_types=None
)
Parser = Callable[[str, SerpRequest], SerpSnapshotData]


def serp_url(request: SerpRequest) -> str:
    lang = request.language.split("-")[0]
    if request.engine == "google":
        params = {
            "q": request.query,
            "hl": lang,
            "gl": request.country.lower(),
            "num": "10",
            "pws": "0",
        }
        return f"https://www.google.com/search?{urlencode(params)}"
    if request.engine == "bing":
        params = {"q": request.query, "cc": request.country.upper(), "setlang": lang, "count": "10"}
        return f"https://www.bing.com/search?{urlencode(params)}"
    if request.engine == "duckduckgo":
        region = f"{request.country.lower()}-{lang}"
        return f"https://html.duckduckgo.com/html/?{urlencode({'q': request.query, 'kl': region})}"
    raise CollectorError("rawhtml", f"engine {request.engine} not supported", retryable=False)


PARSERS: dict[str, Parser] = {
    "google": parse_google,
    "bing": parse_bing,
    "duckduckgo": parse_duckduckgo,
}


class RawHtmlAdapter:
    name = "rawhtml"
    engines = frozenset(PARSERS)

    def __init__(
        self, http: SafeHttpClient, endpoint_template: str, api_key: str, cost_micros: int
    ) -> None:
        self.http = http
        self.template = endpoint_template
        self.api_key = api_key
        self.cost_micros = cost_micros

    async def fetch(self, request: SerpRequest) -> SerpSnapshotData:
        target = serp_url(request)
        vendor_url = self.template.format(
            url=quote(target, safe=""),
            country=request.country.lower(),
            key=quote(self.api_key, safe=""),
        )
        headers = {} if "{key}" in self.template else {"authorization": f"Bearer {self.api_key}"}
        try:
            response = await self.http.request("GET", vendor_url, headers=headers, policy=POLICY)
        except EgressError as exc:
            raise CollectorError(self.name, type(exc).__name__) from exc
        if response.status_code != 200:  # noqa: PLR2004
            raise CollectorError(self.name, f"HTTP {response.status_code}")
        try:
            return PARSERS[request.engine](response.text(), request)
        except SerpParseError as exc:
            raise CollectorError(self.name, f"parse failure: {exc}") from exc
