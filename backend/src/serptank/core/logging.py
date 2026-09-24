"""Structured JSON logging with secret/PII redaction (OWASP A09:2025).

* One JSON object per line with ``timestamp``, ``level``, ``event``, ``request_id``.
* A redaction processor removes values of sensitive keys (tokens, passwords, cookies,
  session ids, secrets) at any nesting depth, and replaces email addresses with a
  stable keyed hash so events can still be correlated without storing the address.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from serptank.core.request_context import get_request_id

REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(pass(word|wd)?|secret|token|api[_-]?key|authorization|cookie|session|csrf|"
    r"credential|private[_-]?key|otp|totp|recovery|refresh|access[_-]?key|signature)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _hash_email(match: re.Match[str]) -> str:
    digest = hashlib.sha256(match.group(0).lower().encode()).hexdigest()[:12]
    return f"email#{digest}"


def redact(value: Any, *, key: str | None = None) -> Any:
    """Return ``value`` with sensitive content removed (pure, recursive)."""
    if key is not None and _SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {k: redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(redact(item) for item in value)
    if isinstance(value, str):
        return _EMAIL.sub(_hash_email, value)
    return value


def _redaction_processor(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    return {k: redact(v, key=k) if k != "event" else redact(v) for k, v in event_dict.items()}


def _add_request_id(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    request_id = get_request_id()
    if request_id:
        event_dict.setdefault("request_id", request_id)
    return event_dict


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    """Configure structlog and route stdlib logging (uvicorn, sqlalchemy) through it."""
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_id,
        structlog.processors.format_exc_info,
        _redaction_processor,
    ]
    renderer: Any = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Access logs are emitted by our own middleware (with redaction), not uvicorn.
    logging.getLogger("uvicorn.access").disabled = True
