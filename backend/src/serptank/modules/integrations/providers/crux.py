"""Chrome UX Report API: real-user Core Web Vitals (p75) for an origin or URL.

Public data, queried with SerpTank's own API key. "No data" (404) is normal for
low-traffic sites and is reported as such, never filled in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from serptank.core.http import EgressError, SafeHttpClient
from serptank.modules.integrations.providers.base import (
    API_POLICY,
    ProviderError,
    parse_json,
    raise_for_status,
)

API = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
METRICS = {
    "largest_contentful_paint": "lcp_ms",
    "interaction_to_next_paint": "inp_ms",
    "cumulative_layout_shift": "cls",
    "first_contentful_paint": "fcp_ms",
    "experimental_time_to_first_byte": "ttfb_ms",
}
# Google's "good" thresholds (p75).
GOOD = {"lcp_ms": 2500.0, "inp_ms": 200.0, "cls": 0.1}
POOR = {"lcp_ms": 4000.0, "inp_ms": 500.0, "cls": 0.25}


@dataclass(frozen=True)
class Vitals:
    target: str
    scope: str
    form_factor: str
    values: dict[str, float | None]


def assess(values: dict[str, float | None]) -> str:
    """'good' | 'needs_improvement' | 'poor' | 'unknown' (Core Web Vitals assessment)."""
    core = [values.get(k) for k in GOOD]
    if any(v is None for v in core):
        return "unknown"
    if any((values[k] or 0) > POOR[k] for k in GOOD):
        return "poor"
    if all((values[k] or 0) <= GOOD[k] for k in GOOD):
        return "good"
    return "needs_improvement"


class CruxClient:
    def __init__(self, http: SafeHttpClient, api_key: str) -> None:
        self.http = http
        self.api_key = api_key

    async def query(
        self, *, origin: str | None = None, url: str | None = None, form_factor: str = "PHONE"
    ) -> Vitals | None:
        body: dict[str, Any] = {"formFactor": form_factor, "metrics": list(METRICS)}
        if url:
            body["url"] = url
        elif origin:
            body["origin"] = origin
        else:
            raise ValueError("origin or url required")
        try:
            response = await self.http.request(
                "POST",
                f"{API}?key={self.api_key}",
                headers={"content-type": "application/json"},
                content=json.dumps(body).encode(),
                policy=API_POLICY,
            )
        except EgressError as exc:
            raise ProviderError(
                "crux_unreachable", "Could not reach the Chrome UX Report.", retryable=True
            ) from exc
        if response.status_code == 404:  # noqa: PLR2004 - not enough real-user data
            return None
        raise_for_status(response, "crux", "Chrome UX Report")
        data = parse_json(response, "crux")
        metrics = ((data or {}).get("record") or {}).get("metrics", {})
        values: dict[str, float | None] = {}
        for name, column in METRICS.items():
            p75 = (metrics.get(name) or {}).get("percentiles", {}).get("p75")
            values[column] = float(p75) if p75 is not None else None
        return Vitals(
            target=url or origin or "",
            scope="url" if url else "origin",
            form_factor=form_factor,
            values=values,
        )
