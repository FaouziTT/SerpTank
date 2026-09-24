"""Domain input normalisation using the Public Suffix List.

A project's ``primary_domain`` is a normalised host name (IDNA/punycode, lower case, no
scheme, port, path or trailing dot) that has a registrable domain. IP addresses,
single-label names, ``localhost`` and bare public suffixes (``co.uk``) are rejected:
they cannot be verified and would point crawls at infrastructure.
"""

from __future__ import annotations

import ipaddress
import re
from functools import lru_cache

from publicsuffixlist import PublicSuffixList

from serptank.core.errors import AppError

_LABEL_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


class InvalidDomainError(AppError):
    status = 422
    code = "invalid_domain"
    title = "Invalid domain"


@lru_cache(maxsize=1)
def _psl() -> PublicSuffixList:
    # accept_unknown=False: hosts under TLDs not on the Public Suffix List are rejected.
    return PublicSuffixList(accept_unknown=False)


def normalize_domain(value: str) -> str:
    raw = value.strip().lower()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if "@" in raw:
        raise InvalidDomainError("Enter a domain like example.com.")
    if raw.startswith("[") or raw.count(":") > 1:
        raise InvalidDomainError("IP addresses are not supported; enter a domain name.")
    host = raw.split(":", 1)[0].rstrip(".")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise InvalidDomainError("IP addresses are not supported; enter a domain name.")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise InvalidDomainError("This domain name is not valid.") from exc
    labels = host.split(".")
    if len(host) > 253 or len(labels) < 2 or not all(_LABEL_RE.match(label) for label in labels):  # noqa: PLR2004
        raise InvalidDomainError("Enter a domain like example.com.")
    if _psl().privatesuffix(host) is None:
        raise InvalidDomainError("Enter a registrable domain, not a public suffix.")
    return host


def registrable_domain(host: str) -> str:
    domain = _psl().privatesuffix(host)
    if domain is None:
        raise InvalidDomainError("Enter a registrable domain, not a public suffix.")
    return str(domain)
