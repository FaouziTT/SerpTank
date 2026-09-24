"""Password hashing and policy (OWASP A04/A07:2025, NIST SP 800-63B-4).

* Hashing: **Argon2id** via ``pwdlib`` (OWASP-recommended parameters are the library
  defaults). Legacy bcrypt hashes still verify and are transparently upgraded.
* Policy: length-based (min 12, max 128), no composition rules, and rejection of
  common or breached passwords. The breach check uses the Have I Been Pwned *range*
  API (k-anonymity: only the first 5 hex chars of the SHA-1 leave the server).
* Timing: :meth:`PasswordHasher.dummy_verify` lets login spend the same time whether or
  not the account exists, so response time does not reveal registered emails.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import structlog
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from serptank.core.errors import AppError
from serptank.core.http import EgressError, SafeHttpClient

logger = structlog.get_logger(__name__)

MAX_PASSWORD_LENGTH = 128
_HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"

# A tiny local deny-list catches the most common choices even when HIBP is unreachable.
_COMMON = frozenset(
    {
        "password1234",
        "123456789012",
        "qwertyuiopas",
        "passwordpassword",
        "letmein12345",
        "iloveyou1234",
        "welcome12345",
        "serptank1234",
        "administrator",
        "000000000000",
        "111111111111",
        "abc123456789",
    }
)


class WeakPasswordError(AppError):
    status = 422
    code = "weak_password"
    title = "Password does not meet the requirements"


class PasswordHasher:
    def __init__(self) -> None:
        self._hash = PasswordHash((Argon2Hasher(), BcryptHasher()))
        self._dummy = self._hash.hash("dummy-password-for-timing-equalisation")

    def hash(self, password: str) -> str:
        return self._hash.hash(password)

    def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        """Return ``(valid, new_hash)``; ``new_hash`` is set when the hash needs upgrading."""
        try:
            return self._hash.verify_and_update(password, password_hash)
        except Exception:  # noqa: BLE001 - malformed/unknown hash formats are simply invalid
            return False, None

    def dummy_verify(self, password: str) -> None:
        self._hash.verify(password, self._dummy)


class BreachChecker(Protocol):
    async def is_breached(self, password: str) -> bool: ...


class HibpBreachChecker:
    """Have I Been Pwned range API client. Fails open (logged) if HIBP is unreachable."""

    def __init__(self, http: SafeHttpClient) -> None:
        self._http = http

    async def is_breached(self, password: str) -> bool:
        digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
        prefix, suffix = digest[:5], digest[5:]
        try:
            response = await self._http.get(
                _HIBP_RANGE_URL + prefix, headers={"Add-Padding": "true"}
            )
        except EgressError as exc:
            logger.warning("hibp_unavailable", error=type(exc).__name__)
            return False
        if response.status_code != 200:  # noqa: PLR2004
            logger.warning("hibp_unexpected_status", status=response.status_code)
            return False
        for line in response.text().splitlines():
            candidate, _, count = line.strip().partition(":")
            if candidate == suffix and count.strip() not in {"", "0"}:
                return True
        return False


class NoBreachChecker:
    async def is_breached(self, password: str) -> bool:
        return False


async def validate_password(
    password: str,
    *,
    min_length: int,
    breach_checker: BreachChecker,
    context: tuple[str, ...] = (),
) -> None:
    """Raise :class:`WeakPasswordError` if ``password`` violates the policy.

    ``context`` holds user-specific words (email local part, name) that must not be the
    password itself.
    """
    if len(password) < min_length:
        raise WeakPasswordError(f"Use at least {min_length} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Use at most {MAX_PASSWORD_LENGTH} characters.")
    lowered = password.lower()
    if lowered in _COMMON or len(set(password)) < 4:  # noqa: PLR2004
        raise WeakPasswordError("This password is too common. Choose a less predictable one.")
    for word in context:
        if word and len(word) >= 4 and lowered == word.lower():  # noqa: PLR2004
            raise WeakPasswordError("Do not use your name or email address as your password.")
    if await breach_checker.is_breached(password):
        raise WeakPasswordError(
            "This password has appeared in a data breach. Choose a different one."
        )
