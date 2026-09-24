"""WebAuthn passkeys (phishing-resistant MFA and passwordless sign-in).

* Challenges are random, single use (deleted on read) and bound to the session that
  requested them (registration) or to the browser pre-session (sign-in).
* The relying-party id and origin are fixed by configuration, so a passkey created for
  SerpTank cannot be exercised by a look-alike domain.
* Sign-in requires user verification (biometric/PIN), so a passkey sign-in satisfies MFA.
* Sign-count regressions (cloned authenticators) are rejected by the library.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from serptank.core.config import Settings
from serptank.core.db import bind_identity
from serptank.core.errors import AppError
from serptank.modules.identity.models import User, WebAuthnCredential

_CHALLENGE_TTL_S = 300
MAX_PASSKEYS_PER_USER = 10


class PasskeyError(AppError):
    status = 400
    code = "passkey_failed"
    title = "Passkey verification failed"


@dataclass(frozen=True)
class PasskeyConfig:
    rp_id: str
    rp_name: str
    origin: str

    @classmethod
    def from_settings(cls, settings: Settings) -> PasskeyConfig:
        return cls(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            origin=settings.public_origin.rstrip("/"),
        )


class PasskeyService:
    def __init__(self, config: PasskeyConfig, redis: Redis) -> None:
        self._config = config
        self._redis = redis

    async def _store_challenge(self, key: str, challenge: bytes) -> None:
        await self._redis.set(f"wa:{key}", challenge.hex(), ex=_CHALLENGE_TTL_S)

    async def _take_challenge(self, key: str) -> bytes:
        raw = await self._redis.getdel(f"wa:{key}")
        if not raw:
            raise PasskeyError("The passkey request expired. Please try again.")
        return bytes.fromhex(str(raw))

    async def registration_options(
        self, db: AsyncSession, user: User, session_key: str
    ) -> dict[str, Any]:
        existing = (
            await db.execute(
                select(WebAuthnCredential.credential_id).where(
                    WebAuthnCredential.user_id == user.id
                )
            )
        ).scalars()
        excluded = [PublicKeyCredentialDescriptor(id=cid) for cid in existing]
        if len(excluded) >= MAX_PASSKEYS_PER_USER:
            raise PasskeyError(f"You can register at most {MAX_PASSKEYS_PER_USER} passkeys.")
        options = generate_registration_options(
            rp_id=self._config.rp_id,
            rp_name=self._config.rp_name,
            user_name=user.email,
            user_id=user.id.bytes,
            user_display_name=user.full_name or user.email,
            exclude_credentials=excluded,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        await self._store_challenge(f"reg:{session_key}", options.challenge)
        result: dict[str, Any] = json.loads(options_to_json(options))
        return result

    async def register(
        self,
        db: AsyncSession,
        user: User,
        session_key: str,
        credential: dict[str, Any],
        name: str,
    ) -> WebAuthnCredential:
        challenge = await self._take_challenge(f"reg:{session_key}")
        try:
            verified = verify_registration_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=self._config.rp_id,
                expected_origin=self._config.origin,
            )
        except (InvalidRegistrationResponse, ValueError, KeyError, TypeError) as exc:
            raise PasskeyError("The passkey could not be verified.") from exc
        record = WebAuthnCredential(
            user_id=user.id,
            credential_id=verified.credential_id,
            public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            transports=[str(t) for t in credential.get("response", {}).get("transports", [])][:5],
            name=(name.strip() or "Passkey")[:80],
            backed_up=verified.credential_backed_up,
        )
        db.add(record)
        return record

    async def authentication_options(self, presession_key: str) -> dict[str, Any]:
        options = generate_authentication_options(
            rp_id=self._config.rp_id,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        await self._store_challenge(f"auth:{presession_key}", options.challenge)
        result: dict[str, Any] = json.loads(options_to_json(options))
        return result

    async def authenticate(
        self, db: AsyncSession, presession_key: str, credential: dict[str, Any]
    ) -> uuid.UUID:
        """Verify an assertion and return the owning user's id."""
        challenge = await self._take_challenge(f"auth:{presession_key}")
        try:
            credential_id = base64url_to_bytes(str(credential["rawId"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise PasskeyError("Malformed passkey response.") from exc
        owner = (
            await db.execute(text("SELECT app_lookup_webauthn_user(:cid)"), {"cid": credential_id})
        ).scalar_one_or_none()
        if owner is None:
            raise PasskeyError("This passkey is not registered.")
        user_id = owner if isinstance(owner, uuid.UUID) else uuid.UUID(str(owner))
        await bind_identity(db, user_id=user_id)
        record = (
            await db.execute(
                select(WebAuthnCredential).where(WebAuthnCredential.credential_id == credential_id)
            )
        ).scalar_one()
        try:
            verified = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=self._config.rp_id,
                expected_origin=self._config.origin,
                credential_public_key=record.public_key,
                credential_current_sign_count=record.sign_count,
                require_user_verification=True,
            )
        except (InvalidAuthenticationResponse, ValueError, KeyError, TypeError) as exc:
            raise PasskeyError("The passkey could not be verified.") from exc
        record.sign_count = verified.new_sign_count
        record.last_used_at = datetime.now(UTC)
        return user_id


async def count_passkeys(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(select(func.count()).where(WebAuthnCredential.user_id == user_id))
    return int(result.scalar_one())
