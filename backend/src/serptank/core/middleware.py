"""Pure-ASGI middleware stack.

Written as raw ASGI (not ``BaseHTTPMiddleware``) so errors become proper Problem Details
responses instead of 500s, and streaming bodies are not buffered.

Order (outermost first), assembled in :func:`serptank.main.create_app`:

1. ``ProxyHeadersMiddleware`` (uvicorn) - trusted proxies only; sets the real client IP.
2. :class:`RequestContextMiddleware` - request id, access log.
3. :class:`SecurityHeadersMiddleware` - HSTS, CSP, nosniff, frame and referrer policy.
4. ``TrustedHostMiddleware`` - Host header allow-list.
5. :class:`BodySizeLimitMiddleware` - rejects oversized request bodies early.
6. :class:`CsrfMiddleware` - Origin/Fetch-Metadata checks + session-bound token (M3).
"""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable, Sequence

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from serptank.core.errors import problem_body
from serptank.core.request_context import set_client_ip, set_request_id

logger = structlog.get_logger("serptank.access")

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


async def _send_problem(send: Send, *, status: int, code: str, title: str, detail: str) -> None:
    body = json.dumps(problem_body(status=status, code=code, title=title, detail=detail)).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/problem+json"),
                (b"content-length", str(len(body)).encode()),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    """Assigns a request id (echoed as ``X-Request-ID``) and writes one access log line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        client = scope.get("client")
        client_ip = client[0] if client else None
        set_request_id(request_id)
        set_client_ip(client_ip)
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_holder: dict[str, int] = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                MutableHeaders(scope=message)["x-request-id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info(
                "request",
                method=scope["method"],
                path=scope["path"],  # never the query string: it may carry tokens
                status=status_holder["status"],
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                client_ip=client_ip,
            )
            structlog.contextvars.clear_contextvars()


class SecurityHeadersMiddleware:
    """Adds browser security headers to every HTTP response (OWASP A02:2025)."""

    API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    DOCS_CSP = (
        "default-src 'none'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: "
        "https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'"
    )

    def __init__(self, app: ASGIApp, *, hsts: bool, docs_paths: Iterable[str] = ()) -> None:
        self.app = app
        self.hsts = hsts
        self.docs_paths = tuple(docs_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = bool(self.docs_paths) and scope["path"].startswith(self.docs_paths)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("x-content-type-options", "nosniff")
                headers.setdefault("x-frame-options", "DENY")
                headers.setdefault("referrer-policy", "strict-origin-when-cross-origin")
                headers.setdefault(
                    "permissions-policy", "camera=(), microphone=(), geolocation=(), payment=()"
                )
                headers.setdefault("cross-origin-opener-policy", "same-origin")
                headers.setdefault("cross-origin-resource-policy", "same-origin")
                headers.setdefault(
                    "content-security-policy", self.DOCS_CSP if is_docs else self.API_CSP
                )
                headers.setdefault("cache-control", "no-store")
                if self.hsts:
                    headers.setdefault(
                        "strict-transport-security", "max-age=63072000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Rejects request bodies larger than ``max_bytes`` (declared or streamed)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int = 1_048_576,
        overrides: Sequence[tuple[re.Pattern[str], int]] = (),
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        # (path pattern, limit) pairs for the few routes that accept larger uploads.
        self.overrides = tuple(overrides)

    def _limit(self, path: str) -> int:
        for pattern, limit in self.overrides:
            if pattern.match(path):
                return limit
        return self.max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        max_bytes = self._limit(scope.get("path", ""))
        declared = Headers(scope=scope).get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            await _send_problem(
                send,
                status=413,
                code="payload_too_large",
                title="Payload too large",
                detail=f"Request bodies are limited to {max_bytes} bytes.",
            )
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise _BodyTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLargeError:
            await _send_problem(
                send,
                status=413,
                code="payload_too_large",
                title="Payload too large",
                detail=f"Request bodies are limited to {max_bytes} bytes.",
            )


class _BodyTooLargeError(Exception):
    pass


# (scope, headers) -> True if the request carries a valid session-bound CSRF token.
CsrfTokenVerifier = Callable[[Scope, Headers], Awaitable[bool]]
# (scope, headers) -> True if the request is authenticated by a browser session cookie.
SessionDetector = Callable[[Headers], bool]


class CsrfMiddleware:
    """Cross-site request forgery protection for unsafe methods (OWASP A01).

    Layered checks, all fail-closed:

    1. **Fetch Metadata:** ``Sec-Fetch-Site: cross-site`` is rejected outright.
    2. **Origin:** when a browser sends ``Origin`` (or only ``Referer``), it must be the
       product origin or an explicitly allowed dev origin.
    3. **Synchronizer token:** requests that carry a session cookie must present a valid
       ``X-CSRF-Token`` bound to that session (verifier supplied by the identity
       module). This includes *login* via a pre-session token, preventing login CSRF.

    Non-browser API clients authenticate with ``Authorization`` API keys, send no cookies
    and no Origin, and are therefore unaffected. Exempt paths must be signature-verified
    webhooks only (e.g. Stripe).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_origins: Iterable[str],
        exempt_paths: Iterable[str] = (),
        session_detector: SessionDetector | None = None,
        token_verifier: CsrfTokenVerifier | None = None,
    ) -> None:
        self.app = app
        self.allowed_origins = {o.rstrip("/").lower() for o in allowed_origins}
        self.exempt_paths = frozenset(exempt_paths)
        self.session_detector = session_detector
        self.token_verifier = token_verifier

    async def _reject(self, send: Send, detail: str) -> None:
        await _send_problem(
            send,
            status=403,
            code="csrf_failed",
            title="Request rejected by CSRF protection",
            detail=detail,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] in _SAFE_METHODS
            or scope["path"] in self.exempt_paths
        ):
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        if headers.get("sec-fetch-site", "").lower() == "cross-site":
            await self._reject(send, "Cross-site requests are not allowed.")
            return
        origin = headers.get("origin")
        if origin is None and (referer := headers.get("referer")):
            origin = _origin_of(referer)
        if origin is not None and origin.rstrip("/").lower() not in self.allowed_origins:
            await self._reject(send, "Request origin is not allowed.")
            return
        if (
            self.session_detector is not None
            and self.token_verifier is not None
            and self.session_detector(headers)
            and not await self.token_verifier(scope, headers)
        ):
            await self._reject(send, "Missing or invalid CSRF token.")
            return
        await self.app(scope, receive, send)


def _origin_of(url: str) -> str | None:
    match = re.match(r"^(https?://[^/?#]+)", url, re.IGNORECASE)
    return match.group(1) if match else None
