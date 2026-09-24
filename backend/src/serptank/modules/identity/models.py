"""User accounts. Users are global (not tenant-owned); tenancy is via memberships."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from serptank.core.models import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # Argon2id hash (pwdlib). NULL for accounts that only use Google sign-in/passkeys.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    google_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_platform_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MfaTotp(Base):
    """A user's TOTP authenticator. The seed is AES-GCM encrypted (AAD = user id)."""

    __tablename__ = "mfa_totp"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Last accepted 30-second time step: prevents replay of an observed code.
    last_used_step: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecoveryCode(UUIDPrimaryKeyMixin, Base):
    """Single-use MFA recovery codes, stored only as keyed hashes."""

    __tablename__ = "recovery_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WebAuthnCredential(UUIDPrimaryKeyMixin, Base):
    """A registered passkey / security key."""

    __tablename__ = "webauthn_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    transports: Mapped[list[str]] = mapped_column(ARRAY(String(20)), nullable=False, default=list)
    name: Mapped[str] = mapped_column(String(80), nullable=False, default="Passkey")
    backed_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailTokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify_email"
    # Purpose label, not a credential.
    RESET_PASSWORD = "reset_password"  # noqa: S105  # nosec B105


class EmailToken(UUIDPrimaryKeyMixin, Base):
    """Single-use, expiring email link tokens (stored as keyed hashes only)."""

    __tablename__ = "email_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ApiKey(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """Organization-scoped API key: ``stk_live_<prefix>_<secret>``.

    Only the prefix (for lookup) and an HMAC of the secret are stored.
    """

    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(40)), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
