"""Per-request context (request/trace id) stored in context variables.

The id is bound by :class:`serptank.core.middleware.RequestContextMiddleware` and read by
logging and error responses so a user-visible ``trace_id`` always matches the logs.
"""

from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def get_client_ip() -> str | None:
    return _client_ip.get()


def set_client_ip(value: str | None) -> None:
    _client_ip.set(value)
