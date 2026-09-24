"""Prometheus metrics.

Metrics are **not** exposed on the public app. :func:`start_metrics_server` serves them
on a separate port that is only reachable on the internal Docker network (M14 wires
Prometheus to it). Paths are recorded by route template, never raw URLs, to keep label
cardinality bounded and avoid leaking identifiers.
"""

from __future__ import annotations

import time

from prometheus_client import Counter, Histogram, start_http_server
from starlette.routing import Match
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUESTS = Counter("serptank_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "serptank_http_request_duration_seconds", "HTTP request latency", ["method", "route"]
)


def _route_template(scope: Scope) -> str:
    app = scope.get("app")
    router = getattr(app, "router", None)
    for route in getattr(router, "routes", []):
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return str(getattr(route, "path", "unmatched"))
    return "unmatched"


class MetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = _route_template(scope)
            REQUESTS.labels(scope["method"], route, str(status["code"])).inc()
            LATENCY.labels(scope["method"], route).observe(time.perf_counter() - started)


def start_metrics_server(port: int, addr: str) -> None:
    start_http_server(port, addr=addr)
