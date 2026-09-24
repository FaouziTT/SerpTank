"""Shared helpers for provider adapters (all HTTP goes through SafeHttpClient)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient, SafeResponse

API_POLICY = EgressPolicy(max_response_bytes=32 * 1024 * 1024, total_timeout_s=60)


class ProviderError(Exception):
    """A provider call failed. ``message`` is user-safe; ``reauth`` means the grant is gone."""

    def __init__(
        self, code: str, message: str, *, reauth: bool = False, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.reauth = reauth
        self.retryable = retryable


def parse_json(response: SafeResponse, provider: str) -> Any:
    try:
        return json.loads(response.content or b"null")
    except ValueError as exc:
        raise ProviderError(
            f"{provider}_bad_response", f"{provider} returned an unreadable response."
        ) from exc


def raise_for_status(response: SafeResponse, provider: str, label: str) -> None:
    status = response.status_code
    if status < 400:  # noqa: PLR2004
        return
    if status in {401, 403}:
        raise ProviderError(
            f"{provider}_unauthorized",
            f"{label} rejected our access. Reconnect the account or check its permissions.",
            reauth=status == 401,  # noqa: PLR2004
        )
    if status == 429:  # noqa: PLR2004
        raise ProviderError(
            f"{provider}_rate_limited", f"{label} quota reached; we'll retry later.", retryable=True
        )
    if status >= 500:  # noqa: PLR2004
        raise ProviderError(
            f"{provider}_unavailable", f"{label} is temporarily unavailable.", retryable=True
        )
    raise ProviderError(
        f"{provider}_request_failed", f"{label} refused the request (HTTP {status})."
    )


async def request_json(
    http: SafeHttpClient,
    method: str,
    url: str,
    *,
    provider: str,
    label: str,
    headers: dict[str, str] | None = None,
    body: Any = None,
    form: dict[str, str] | None = None,
) -> Any:
    request_headers = dict(headers or {})
    content: bytes | None = None
    if body is not None:
        request_headers["content-type"] = "application/json"
        content = json.dumps(body).encode()
    elif form is not None:
        request_headers["content-type"] = "application/x-www-form-urlencoded"
        content = urlencode(form).encode()
    try:
        response = await http.request(
            method, url, headers=request_headers, content=content, policy=API_POLICY
        )
    except EgressError as exc:
        raise ProviderError(
            f"{provider}_unreachable", f"Could not reach {label}.", retryable=True
        ) from exc
    raise_for_status(response, provider, label)
    return parse_json(response, provider)
