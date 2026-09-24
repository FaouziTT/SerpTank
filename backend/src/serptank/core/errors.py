"""RFC 9457 Problem Details error model.

Every error response has ``Content-Type: application/problem+json`` and the shape::

    {"type": "https://serptank.com/problems/<code>", "title": "...", "status": 404,
     "code": "not_found", "detail": "...", "trace_id": "..."}

Rules (OWASP A10:2025, "mishandling of exceptional conditions"):

* Internal exception text **never** reaches the client. Unexpected exceptions become a
  generic 500 whose ``trace_id`` lets operators find the full stack trace in logs.
* ``code`` values are stable and documented; clients branch on them, not on text.
"""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from serptank.core.request_context import get_request_id

PROBLEM_BASE_URI = "https://serptank.com/problems/"
PROBLEM_CONTENT_TYPE = "application/problem+json"

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Base class for expected, client-facing errors.

    Subclasses set ``status`` and ``code``; ``detail`` must be safe to show to users.
    """

    status: int = HTTPStatus.BAD_REQUEST
    code: str = "bad_request"
    title: str = "Bad request"

    def __init__(
        self,
        detail: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.extra = extra or {}
        self.headers = headers or {}


class NotFoundError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = "not_found"
    title = "Resource not found"


class AuthenticationRequiredError(AppError):
    status = HTTPStatus.UNAUTHORIZED
    code = "authentication_required"
    title = "Authentication required"


class PermissionDeniedError(AppError):
    status = HTTPStatus.FORBIDDEN
    code = "permission_denied"
    title = "Permission denied"


class ConflictError(AppError):
    status = HTTPStatus.CONFLICT
    code = "conflict"
    title = "Conflict"


class RateLimitedError(AppError):
    status = HTTPStatus.TOO_MANY_REQUESTS
    code = "rate_limited"
    title = "Too many requests"


class CsrfError(AppError):
    status = HTTPStatus.FORBIDDEN
    code = "csrf_failed"
    title = "Request rejected by CSRF protection"


class ServiceUnavailableError(AppError):
    status = HTTPStatus.SERVICE_UNAVAILABLE
    code = "service_unavailable"
    title = "Service temporarily unavailable"


def problem_body(
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": PROBLEM_BASE_URI + code,
        "title": title,
        "status": status,
        "code": code,
        "trace_id": get_request_id(),
    }
    if detail:
        body["detail"] = detail
    if extra:
        body.update({k: v for k, v in extra.items() if k not in body})
    return body


def problem_response(
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        problem_body(status=status, code=code, title=title, detail=detail, extra=extra),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_CONTENT_TYPE,
    )


_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "authentication_required",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_failed",
    429: "rate_limited",
}


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # defensive: never trust handler registration
        return await _unhandled_handler(request, exc)
    return problem_response(
        status=int(exc.status),
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        extra=exc.extra,
        headers=exc.headers,
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return await _unhandled_handler(request, exc)
    status = exc.status_code
    code = _STATUS_CODES.get(status, "http_error")
    title = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "Error"
    # Framework-generated details (e.g. "Not Found") are generic and safe; we still drop
    # anything that is not a plain string to avoid leaking structured internals.
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
    return problem_response(
        status=status, code=code, title=title, detail=detail, headers=exc.headers
    )


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await _unhandled_handler(request, exc)
    errors = [
        {
            # Drop the leading "body"/"query" segment; never echo the rejected input value.
            "field": ".".join(str(part) for part in err.get("loc", ())[1:]),
            "message": err.get("msg", "invalid"),
            "type": err.get("type", "value_error"),
        }
        for err in exc.errors()
    ]
    return problem_response(
        status=422,
        code="validation_failed",
        title="Request validation failed",
        extra={"errors": errors},
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
    )
    return problem_response(
        status=500,
        code="internal_error",
        title="Internal server error",
        detail="An unexpected error occurred. Quote the trace_id when contacting support.",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
