"""TOTP authenticators and recovery codes.

* TOTP seeds are encrypted with the field-encryption keyring (AAD binds the ciphertext to
  the user, so a seed copied to another row cannot be decrypted).
* Codes are accepted for the current time step +/- 1 (clock drift) and a step can only
  be used once per user (``last_used_step``), which blocks replay of an observed code.
* Recovery codes: 10 random codes shown once, stored as keyed hashes, single use.
"""

from __future__ import annotations

import secrets
import time
import uuid
from datetime import UTC, datetime

import pyotp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.crypto import Keyring, constant_time_equals, hash_token
from serptank.modules.identity.models import MfaTotp, RecoveryCode

TOTP_ISSUER = "SerpTank"
_STEP_S = 30
_RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o/1/l/i ambiguity


def _aad(user_id: uuid.UUID) -> bytes:
    return f"mfa_totp:{user_id}".encode()


# Public alias for maintenance jobs that re-encrypt TOTP seeds (key rotation).
totp_associated_data = _aad


def new_totp_secret() -> str:
    return pyotp.random_base32(length=32)


def provisioning_uri(secret: str, account_name: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=TOTP_ISSUER)


def normalise_code(code: str) -> str:
    return code.replace(" ", "").replace("-", "").strip().lower()


def matching_step(secret: str, code: str, now: float | None = None) -> int | None:
    """Return the time step ``code`` is valid for (current +/- 1), or ``None``."""
    code = normalise_code(code)
    if len(code) != 6 or not code.isdigit():  # noqa: PLR2004
        return None
    totp = pyotp.TOTP(secret)
    current = int((now if now is not None else time.time()) // _STEP_S)
    for step in (current, current - 1, current + 1):
        if constant_time_equals(totp.generate_otp(step), code):
            return step
    return None


async def store_pending_totp(
    session: AsyncSession, keyring: Keyring, user_id: uuid.UUID, secret: str
) -> None:
    """Create or replace an *unconfirmed* authenticator for ``user_id``."""
    existing = await session.get(MfaTotp, user_id)
    encrypted = keyring.encrypt(secret, associated_data=_aad(user_id))
    if existing is None:
        session.add(MfaTotp(user_id=user_id, secret_encrypted=encrypted))
    else:
        existing.secret_encrypted = encrypted
        existing.confirmed_at = None
        existing.last_used_step = None


async def verify_totp(
    session: AsyncSession,
    keyring: Keyring,
    user_id: uuid.UUID,
    code: str,
    *,
    require_confirmed: bool = True,
) -> bool:
    record = await session.get(MfaTotp, user_id, with_for_update=True)
    if record is None or (require_confirmed and record.confirmed_at is None):
        return False
    secret = keyring.decrypt(record.secret_encrypted, associated_data=_aad(user_id))
    step = matching_step(secret, code)
    if step is None or (record.last_used_step is not None and step <= record.last_used_step):
        return False
    record.last_used_step = step
    if record.confirmed_at is None:
        record.confirmed_at = datetime.now(UTC)
    if keyring.needs_rotation(record.secret_encrypted):
        record.secret_encrypted = keyring.encrypt(secret, associated_data=_aad(user_id))
    return True


def _new_recovery_code() -> str:
    raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
    return f"{raw[:5]}-{raw[5:]}"


async def regenerate_recovery_codes(
    session: AsyncSession, user_id: uuid.UUID, pepper: str
) -> list[str]:
    """Replace all recovery codes; returns the plaintext codes (show them exactly once)."""
    existing = await session.execute(select(RecoveryCode).where(RecoveryCode.user_id == user_id))
    for row in existing.scalars():
        await session.delete(row)
    codes = [_new_recovery_code() for _ in range(_RECOVERY_CODE_COUNT)]
    for code in codes:
        session.add(
            RecoveryCode(user_id=user_id, code_hash=hash_token(normalise_code(code), pepper=pepper))
        )
    return codes


async def use_recovery_code(
    session: AsyncSession, user_id: uuid.UUID, code: str, pepper: str
) -> bool:
    digest = hash_token(normalise_code(code), pepper=pepper)
    result = await session.execute(
        update(RecoveryCode)
        .where(
            RecoveryCode.user_id == user_id,
            RecoveryCode.code_hash == digest,
            RecoveryCode.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
        .returning(RecoveryCode.id)
    )
    return result.scalar_one_or_none() is not None


async def remaining_recovery_codes(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.execute(
        select(RecoveryCode.id).where(
            RecoveryCode.user_id == user_id, RecoveryCode.used_at.is_(None)
        )
    )
    return len(result.all())
