"""Domain ownership verification (required before deep crawls and indexing submissions).

Methods:
* ``dns``  - a TXT record ``serptank-site-verification=<token>`` on the registrable
  domain (proves control of the whole domain).
* ``html`` - the token served at ``https://<host>/.well-known/serptank-verification.txt``
  (proves control of that host). Fetched through :class:`SafeHttpClient`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import StrEnum

import dns.asyncresolver
import dns.exception
import dns.resolver
import structlog

from serptank.core.crypto import constant_time_equals, generate_token
from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient
from serptank.modules.projects.domains import registrable_domain

logger = structlog.get_logger(__name__)

TXT_PREFIX = "serptank-site-verification="
WELL_KNOWN_PATH = "/.well-known/serptank-verification.txt"

TxtResolver = Callable[[str], Awaitable[list[str]]]


class VerificationMethod(StrEnum):
    DNS = "dns"
    HTML = "html"


def new_verification_token() -> str:
    return "stv_" + generate_token(24)


async def system_txt_resolver(name: str) -> list[str]:
    try:
        answer = await dns.asyncresolver.resolve(name, "TXT", lifetime=5.0)
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.exception.Timeout,
        dns.resolver.NoNameservers,
    ):
        return []
    return [b"".join(r.strings).decode("utf-8", "replace") for r in answer]


async def check_dns(host: str, token: str, resolver: TxtResolver) -> bool:
    records = await resolver(registrable_domain(host))
    expected = TXT_PREFIX + token
    return any(constant_time_equals(r.strip().strip('"'), expected) for r in records)


async def check_html(host: str, token: str, http: SafeHttpClient) -> bool:
    policy = EgressPolicy(max_response_bytes=4096, total_timeout_s=10)
    try:
        response = await http.get(f"https://{host}{WELL_KNOWN_PATH}", policy=policy)
    except EgressError as exc:
        logger.info("verification_fetch_failed", host=host, error=type(exc).__name__)
        return False
    return response.status_code == 200 and constant_time_equals(response.text().strip(), token)  # noqa: PLR2004
