"""Organization-scoped API keys for programmatic access.

Format: ``stk_live_<prefix>_<secret>`` (prefix: 12 chars, secret: 256 bits).

* Only ``prefix`` and ``HMAC(secret, api_key_pepper)`` are stored; the full key is
  shown once at creation.
* Lookup before any identity is bound uses the ``app_lookup_api_key`` SECURITY DEFINER
  function (exact prefix only); the secret hash is compared in constant time.
* Keys carry scopes (``read``/``write``), can expire and are revocable.
* API keys are *never* accepted for account-level or security-sensitive operations
  (member management, billing, key management) - see ``tenancy.policies``.
"""

from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.crypto import constant_time_equals, generate_token, hash_token
from serptank.modules.identity.models import ApiKey

KEY_PREFIX = "stk_live_"
_KEY_RE = re.compile(r"^stk_live_([a-z0-9]{12})_([A-Za-z0-9_-]{40,64})$")
_PREFIX_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
_LAST_USED_GRANULARITY = timedelta(minutes=5)


class ApiScope(StrEnum):
    READ = "read"
    WRITE = "write"


@dataclass(frozen=True)
class ApiKeyPrincipal:
    key_id: uuid.UUID
    organization_id: uuid.UUID
    scopes: frozenset[str]


@dataclass(frozen=True)
class NewApiKey:
    record: ApiKey
    plaintext: str


def generate_api_key(pepper: str) -> tuple[str, str, str]:
    """Return ``(plaintext, prefix, secret_hash)``."""
    prefix = "".join(secrets.choice(_PREFIX_ALPHABET) for _ in range(12))
    secret = generate_token(32)
    return f"{KEY_PREFIX}{prefix}_{secret}", prefix, hash_token(secret, pepper=pepper)


def create_api_key(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    created_by: uuid.UUID,
    name: str,
    scopes: list[ApiScope],
    expires_in_days: int | None,
    pepper: str,
) -> NewApiKey:
    plaintext, prefix, secret_hash = generate_api_key(pepper)
    record = ApiKey(
        organization_id=organization_id,
        name=name.strip()[:80] or "API key",
        prefix=prefix,
        secret_hash=secret_hash,
        scopes=sorted({s.value for s in scopes}),
        created_by_user_id=created_by,
        expires_at=(
            datetime.now(UTC) + timedelta(days=expires_in_days) if expires_in_days else None
        ),
    )
    db.add(record)
    return NewApiKey(record=record, plaintext=plaintext)


async def authenticate_api_key(
    db: AsyncSession, raw_key: str, pepper: str
) -> ApiKeyPrincipal | None:
    match = _KEY_RE.match(raw_key.strip())
    if not match:
        return None
    prefix, secret = match.groups()
    row = (
        await db.execute(
            text(
                "SELECT id, organization_id, secret_hash, scopes, expires_at, revoked_at "
                "FROM app_lookup_api_key(:prefix)"
            ),
            {"prefix": prefix},
        )
    ).first()
    candidate = hash_token(secret, pepper=pepper)
    if row is None:
        constant_time_equals(candidate, candidate)  # equalise timing with the found path
        return None
    key_id, org_id, secret_hash, scopes, expires_at, revoked_at = row
    if not constant_time_equals(candidate, secret_hash):
        return None
    now = datetime.now(UTC)
    if revoked_at is not None or (expires_at is not None and expires_at <= now):
        return None
    return ApiKeyPrincipal(key_id=key_id, organization_id=org_id, scopes=frozenset(scopes))


async def touch_api_key(db: AsyncSession, key_id: uuid.UUID) -> None:
    """Record usage, at most every few minutes (avoids a write per request)."""
    now = datetime.now(UTC)
    await db.execute(
        update(ApiKey)
        .where(
            ApiKey.id == key_id,
            (ApiKey.last_used_at.is_(None)) | (ApiKey.last_used_at < now - _LAST_USED_GRANULARITY),
        )
        .values(last_used_at=now)
    )
