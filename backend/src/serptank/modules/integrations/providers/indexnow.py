"""IndexNow: instant URL submission to Bing, Yandex, Seznam, Naver (not Google).

Protocol: the site hosts ``https://<host>/<key>.txt`` containing the key; submissions
POST ``{host, key, keyLocation, urlList}``. We only ever submit URLs of the project's own
verified domain (plan §5.5), in batches of at most 10,000.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from serptank.core.crypto import constant_time_equals, generate_token
from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient
from serptank.modules.integrations.providers.base import ProviderError

MAX_URLS = 10_000
KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")
KEY_FILE_POLICY = EgressPolicy(max_response_bytes=1024, total_timeout_s=10)


def new_key() -> str:
    # URL-safe token; IndexNow allows a-z, A-Z, 0-9 and "-" (8-128 chars).
    return re.sub(r"[^A-Za-z0-9-]", "", generate_token(24))[:32]


def key_location(host: str, key: str) -> str:
    return f"https://{host}/{key}.txt"


async def key_file_ok(http: SafeHttpClient, host: str, key: str) -> bool:
    try:
        response = await http.get(key_location(host, key), policy=KEY_FILE_POLICY)
    except EgressError:
        return False
    return response.status_code == 200 and constant_time_equals(response.text().strip(), key)  # noqa: PLR2004


async def submit(http: SafeHttpClient, endpoint: str, host: str, key: str, urls: list[str]) -> int:
    if not KEY_RE.match(key):
        raise ProviderError("indexnow_bad_key", "The IndexNow key is invalid.")
    if not urls:
        return 200
    if len(urls) > MAX_URLS:
        raise ProviderError(
            "indexnow_too_many", f"IndexNow accepts at most {MAX_URLS} URLs per request."
        )
    if any((urlsplit(u).hostname or "").lower() != host for u in urls):
        raise ProviderError(
            "indexnow_foreign_url", "Only URLs on the project's own host can be submitted."
        )
    body = {"host": host, "key": key, "keyLocation": key_location(host, key), "urlList": urls}
    try:
        response = await http.request(
            "POST",
            endpoint,
            headers={"content-type": "application/json; charset=utf-8"},
            content=json.dumps(body).encode(),
            policy=EgressPolicy(total_timeout_s=30, max_response_bytes=64 * 1024),
        )
    except EgressError as exc:
        raise ProviderError(
            "indexnow_unreachable", "Could not reach IndexNow.", retryable=True
        ) from exc
    if response.status_code in {200, 202}:
        return response.status_code
    messages = {
        400: "IndexNow rejected the request format.",
        403: "IndexNow couldn't verify the key file on your site.",
        422: "IndexNow says some URLs don't belong to the host or the key doesn't match.",
        429: "Too many IndexNow submissions; try again later.",
    }
    raise ProviderError(
        f"indexnow_{response.status_code}",
        messages.get(response.status_code, f"IndexNow returned HTTP {response.status_code}."),
        retryable=response.status_code == 429,  # noqa: PLR2004
    )
