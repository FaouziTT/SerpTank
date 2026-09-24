"""Application settings.

All configuration comes from environment variables prefixed ``SERPTANK_`` or, in
production, from files in ``/run/secrets`` (Docker secrets), where the file name is the
lower-case variable name without the prefix (e.g. ``/run/secrets/session_secret``).

Security properties (see docs/execution-plan.md §5.4):

* **Fail closed.** Outside ``development``/``test`` every secret must be provided and
  strong; the application refuses to start otherwise. There are no silent fallbacks.
* **Key separation.** Each purpose (sessions, CSRF, API-key pepper, field encryption)
  has its own secret. Nothing reuses a single ``SECRET_KEY``.
* Secrets are ``SecretStr`` so they never appear in ``repr()`` or logs.
"""

from __future__ import annotations

import base64
import binascii
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_MIN_SECRET_BYTES = 32
_DEV_PLACEHOLDER = "dev-insecure-change-me"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


def _default_secrets_dir() -> Path | None:
    path = Path("/run/secrets")
    return path if path.is_dir() else None


class Settings(BaseSettings):
    """Typed, validated application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SERPTANK_",
        env_file=None,
        secrets_dir=_default_secrets_dir(),
        extra="ignore",
        frozen=True,
    )

    environment: Environment = Environment.DEVELOPMENT
    app_name: str = "SerpTank"
    log_level: str = "INFO"
    log_json: bool = True

    # Public origin of the product (Caddy serves web + API on this single origin).
    public_origin: str = "http://localhost:3000"
    # Host header allow-list (TrustedHostMiddleware).
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    # Only these proxy IPs may set X-Forwarded-For / X-Forwarded-Proto.
    trusted_proxies: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["127.0.0.1"])
    # Extra origins allowed for unsafe requests (dev tooling only; production is same-origin).
    extra_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://serptank:serptank@localhost:5432/serptank"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 10
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")

    # Purpose-separated secrets.
    session_secret: SecretStr = SecretStr(_DEV_PLACEHOLDER)
    csrf_secret: SecretStr = SecretStr(_DEV_PLACEHOLDER)
    api_key_pepper: SecretStr = SecretStr(_DEV_PLACEHOLDER)
    # Field-encryption keyring: "kid1:<base64 32 bytes>,kid2:<base64 32 bytes>".
    encryption_keys: SecretStr = SecretStr("")
    encryption_active_key_id: str = ""

    docs_enabled: bool | None = None  # default: on in development/test only
    max_request_body_bytes: int = 1_048_576
    # Internal-only Prometheus endpoint (None = disabled). Never published by Caddy.
    metrics_port: int | None = None
    metrics_bind_address: str = "127.0.0.1"

    @field_validator("allowed_hosts", "trusted_proxies", "extra_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production_like(self) -> bool:
        return self.environment in {Environment.STAGING, Environment.PRODUCTION}

    @property
    def show_docs(self) -> bool:
        if self.docs_enabled is not None:
            return self.docs_enabled
        return not self.is_production_like

    @property
    def cookie_secure(self) -> bool:
        return self.is_production_like or self.public_origin.startswith("https://")

    def parsed_encryption_keys(self) -> dict[str, bytes]:
        """Return the keyring as ``{key_id: 32-byte key}`` (validated at startup)."""
        return _parse_keyring(self.encryption_keys.get_secret_value())

    @model_validator(mode="after")
    def _fail_closed(self) -> Self:
        keys = self.parsed_encryption_keys()
        if keys and self.encryption_active_key_id not in keys:
            msg = "SERPTANK_ENCRYPTION_ACTIVE_KEY_ID must name a key in SERPTANK_ENCRYPTION_KEYS"
            raise ValueError(msg)
        if not self.is_production_like:
            return self
        problems: list[str] = []
        for name in ("session_secret", "csrf_secret", "api_key_pepper"):
            value: SecretStr = getattr(self, name)
            raw = value.get_secret_value()
            if raw == _DEV_PLACEHOLDER or len(raw.encode()) < _MIN_SECRET_BYTES:
                problems.append(f"{name} must be set to >= {_MIN_SECRET_BYTES} random bytes")
        if len({self.session_secret, self.csrf_secret, self.api_key_pepper}) < 3:  # noqa: PLR2004
            problems.append("session_secret, csrf_secret and api_key_pepper must all differ")
        if not keys:
            problems.append("encryption_keys must be configured")
        if not self.public_origin.startswith("https://"):
            problems.append("public_origin must be https in staging/production")
        if "*" in self.allowed_hosts:
            problems.append("allowed_hosts must not contain '*'")
        if problems:
            raise ValueError("Insecure production configuration: " + "; ".join(problems))
        return self


def _parse_keyring(raw: str) -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    for entry in filter(None, (part.strip() for part in raw.split(","))):
        key_id, sep, encoded = entry.partition(":")
        if not sep or not key_id:
            msg = "encryption key entries must look like '<kid>:<base64 key>'"
            raise ValueError(msg)
        try:
            key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        except (binascii.Error, ValueError) as exc:
            msg = f"encryption key {key_id!r} is not valid base64"
            raise ValueError(msg) from exc
        if len(key) != _MIN_SECRET_BYTES:
            msg = f"encryption key {key_id!r} must decode to exactly 32 bytes"
            raise ValueError(msg)
        keys[key_id] = key
    return keys


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings (cached). Tests override via dependency injection."""
    return Settings()
