"""Fake Google / Bing / CrUX / IndexNow endpoints behaving like the real APIs.

They validate what the real services validate (PKCE verifier, bearer tokens, API keys,
IndexNow key location) so the tests prove our side of each protocol.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx

from tests.support.api import FakeInternet


def _json(data: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


@dataclass
class FakeGoogle:
    code_challenge: str | None = None
    issued_access: set[str] = field(default_factory=set)
    refresh_valid: bool = True
    revoked: list[str] = field(default_factory=list)
    scopes: str = "openid email https://www.googleapis.com/auth/webmasters.readonly https://www.googleapis.com/auth/analytics.readonly"
    sites: list[dict[str, str]] = field(
        default_factory=lambda: [
            {"siteUrl": "sc-domain:example-shop.com", "permissionLevel": "siteOwner"},
            {"siteUrl": "https://other-site.com/", "permissionLevel": "siteFullUser"},
        ]
    )
    gsc_rows: int = 3
    analytics_calls: int = 0
    inspections: int = 0
    sitemap_submissions: list[str] = field(default_factory=list)
    counter: int = 0

    def _authorized(self, request: httpx.Request) -> bool:
        return (
            request.headers.get("authorization", "").removeprefix("Bearer ") in self.issued_access
        )

    def _issue(self) -> str:
        self.counter += 1
        token = f"access-{self.counter}"
        self.issued_access.add(token)
        return token

    def oauth(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        if path == "/revoke":
            self.revoked.append(form.get("token", ""))
            return _json({})
        if form.get("grant_type") == "authorization_code":
            verifier = form.get("code_verifier", "")
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .rstrip(b"=")
                .decode()
            )
            if (
                form.get("code") != "good-code"
                or challenge != self.code_challenge
                or form.get("client_secret") != "data-secret"
            ):
                return _json({"error": "invalid_grant"}, 400)
            return _json(
                {
                    "access_token": self._issue(),
                    "refresh_token": "refresh-1",
                    "expires_in": 3600,
                    "scope": self.scopes,
                }
            )
        if form.get("grant_type") == "refresh_token":
            if not self.refresh_valid or form.get("refresh_token") != "refresh-1":
                return _json({"error": "invalid_grant"}, 400)
            return _json({"access_token": self._issue(), "expires_in": 3600, "scope": self.scopes})
        return _json({"error": "unsupported"}, 400)

    def userinfo(self, request: httpx.Request) -> httpx.Response:
        if not self._authorized(request):
            return _json({}, 401)
        return _json({"email": "owner@example-shop.com"})

    def webmasters(self, request: httpx.Request) -> httpx.Response:  # noqa: PLR0911
        if not self._authorized(request):
            return _json({}, 401)
        path = request.url.path
        if path.endswith("/sites"):
            return _json({"siteEntry": self.sites})
        if path.endswith("/searchAnalytics/query"):
            body = json.loads(request.content)
            if body["startRow"] > 0:
                return _json({"rows": []})
            day = body["startDate"]
            return _json(
                {
                    "rows": [
                        {
                            "keys": [
                                f"query {i}",
                                f"https://example-shop.com/p{i}",
                                "usa",
                                "MOBILE",
                            ],
                            "clicks": 10 - i,
                            "impressions": 100,
                            "position": 3.5 + i,
                        }
                        for i in range(self.gsc_rows)
                    ]
                    + [
                        {
                            "keys": [
                                "only-day",
                                f"https://example-shop.com/{day}",
                                "deu",
                                "DESKTOP",
                            ],
                            "clicks": 1,
                            "impressions": 5,
                            "position": 9.0,
                        }
                    ]
                }
            )
        if path.endswith("/sitemaps"):
            return _json(
                {
                    "sitemap": [
                        {
                            "path": "https://example-shop.com/sitemap.xml",
                            "lastSubmitted": "2026-09-01T00:00:00Z",
                            "isPending": False,
                            "errors": "0",
                            "warnings": "2",
                        }
                    ]
                }
            )
        if "/sitemaps/" in path and request.method == "PUT":
            self.sitemap_submissions.append(path)
            return _json({})
        return _json({}, 404)

    def inspection(self, request: httpx.Request) -> httpx.Response:
        if not self._authorized(request):
            return _json({}, 401)
        self.inspections += 1
        body = json.loads(request.content)
        return _json(
            {
                "inspectionResult": {
                    "indexStatusResult": {
                        "verdict": "PASS",
                        "coverageState": "Submitted and indexed",
                        "indexingState": "INDEXING_ALLOWED",
                        "robotsTxtState": "ALLOWED",
                        "pageFetchState": "SUCCESSFUL",
                        "lastCrawlTime": "2026-09-20T08:00:00Z",
                        "googleCanonical": body["inspectionUrl"],
                        "userCanonical": body["inspectionUrl"],
                    }
                }
            }
        )

    def analytics_admin(self, request: httpx.Request) -> httpx.Response:
        if not self._authorized(request):
            return _json({}, 401)
        return _json(
            {
                "accountSummaries": [
                    {
                        "propertySummaries": [
                            {"property": "properties/123", "displayName": "Shop GA4"}
                        ]
                    }
                ]
            }
        )

    def analytics_data(self, request: httpx.Request) -> httpx.Response:
        if not self._authorized(request):
            return _json({}, 401)
        self.analytics_calls += 1
        body = json.loads(request.content)
        assert body["dimensionFilter"]["filter"]["stringFilter"]["value"] == "Organic Search"
        return _json(
            {
                "rows": [
                    {
                        "dimensionValues": [{"value": "20260920"}, {"value": "/landing"}],
                        "metricValues": [
                            {"value": "120"},
                            {"value": "80"},
                            {"value": "4"},
                            {"value": "199.5"},
                        ],
                    }
                ]
            }
        )

    def crux(self, request: httpx.Request) -> httpx.Response:
        if parse_qs(urlsplit(str(request.url)).query).get("key") != ["crux-key"]:
            return _json({}, 403)
        body = json.loads(request.content)
        if body.get("url", "").endswith("/rare"):
            return _json({"error": {"code": 404}}, 404)
        slow = body.get("formFactor") == "PHONE"
        metrics = {
            "largest_contentful_paint": {"percentiles": {"p75": 4800 if slow else 1900}},
            "interaction_to_next_paint": {"percentiles": {"p75": 150}},
            "cumulative_layout_shift": {"percentiles": {"p75": "0.05"}},
        }
        return _json({"record": {"metrics": metrics}})

    def install(self, internet: FakeInternet) -> None:
        internet.handlers["oauth2.googleapis.com"] = self.oauth
        internet.handlers["openidconnect.googleapis.com"] = self.userinfo
        internet.handlers["www.googleapis.com"] = self.webmasters
        internet.handlers["searchconsole.googleapis.com"] = self.inspection
        internet.handlers["analyticsadmin.googleapis.com"] = self.analytics_admin
        internet.handlers["analyticsdata.googleapis.com"] = self.analytics_data
        internet.handlers["chromeuxreport.googleapis.com"] = self.crux


@dataclass
class FakeBing:
    key: str = "bing-key-0123456789abcdef"
    submitted: list[dict[str, Any]] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        params = parse_qs(urlsplit(str(request.url)).query)
        if params.get("apikey") != [self.key]:
            return _json({"Message": "invalid key"}, 401)
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "GetUserSites":
            return _json(
                {
                    "d": [
                        {"Url": "https://example-shop.com/", "IsVerified": True},
                        {"Url": "https://unverified.com/", "IsVerified": False},
                    ]
                }
            )
        if method == "GetQueryStats":
            return _json(
                {
                    "d": [
                        {
                            "Date": "/Date(1758326400000)/",
                            "Query": "blue widgets",
                            "Clicks": 7,
                            "Impressions": 90,
                            "AvgImpressionPosition": 4.2,
                        },
                        {
                            "Date": "/Date(1758412800000-0700)/",
                            "Query": "red widgets",
                            "Clicks": 2,
                            "Impressions": 30,
                            "AvgImpressionPosition": -1,
                        },
                    ]
                }
            )
        if method == "SubmitUrlBatch":
            self.submitted.append(json.loads(request.content))
            return _json({"d": None})
        return _json({}, 404)

    def install(self, internet: FakeInternet) -> None:
        internet.handlers["ssl.bing.com"] = self.handler


@dataclass
class FakeIndexNow:
    received: list[dict[str, Any]] = field(default_factory=list)
    status: int = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.received.append(json.loads(request.content))
        return httpx.Response(self.status)

    def install(self, internet: FakeInternet) -> None:
        internet.handlers["api.indexnow.org"] = self.handler
