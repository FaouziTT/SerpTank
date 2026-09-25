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

    # --- Identity (Module 3) -------------------------------------------------------
    session_idle_timeout_s: int = 24 * 3600
    session_absolute_timeout_s: int = 14 * 24 * 3600
    session_remember_absolute_timeout_s: int = 30 * 24 * 3600
    reauth_window_s: int = 10 * 60
    password_min_length: int = 12
    breached_password_check: bool = True  # HIBP k-anonymity range API
    # WebAuthn relying party; the RP id must be the registrable domain of public_origin.
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "SerpTank"
    # Google sign-in (OIDC). Separate OAuth client from the GSC/GA4 data integration (M7).
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    # Cloudflare Turnstile; when unset, repeated failures are throttled instead.
    turnstile_secret: SecretStr = SecretStr("")
    # Outbound email. "console" logs a redacted notice (dev); "smtp" sends for real.
    email_backend: str = "console"
    email_from: str = "SerpTank <no-reply@serptank.com>"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = False
    max_request_body_bytes: int = 1_048_576

    # --- Jobs, crawler and renderer (Module 6) --------------------------------------
    # "inprocess" runs jobs as asyncio tasks inside the API (development and tests);
    # "celery" hands them to the worker fleet (required in staging/production).
    jobs_backend: str = "inprocess"
    celery_broker_url: SecretStr = SecretStr("")  # defaults to redis_url when empty
    # BYPASSRLS login used only by the scheduler to find due work across tenants.
    scheduler_database_url: SecretStr = SecretStr("")
    crawler_user_agent: str = "SerpTankBot/1.0 (+https://serptank.com/bot)"
    crawl_max_pages_per_crawl: int = 10_000
    crawl_max_pages_unverified: int = 100  # shallow crawl until domain ownership is proven
    crawl_max_depth: int = 10
    crawl_min_delay_s: float = 1.0  # politeness floor between requests to one host
    crawl_concurrency: int = 2
    crawl_mobile_sample: int = 10  # pages re-fetched with a mobile UA for parity checks
    # Isolated Playwright renderer (internal service). Unset = no JS rendering checks.
    renderer_url: str = ""
    renderer_token: SecretStr = SecretStr("")
    render_sample: int = 10
    renderer_chromium_path: str = ""  # only when the browser build differs from Playwright's

    # --- Integrations and indexing (Module 7) ----------------------------------------
    # Separate OAuth client for customer data (GSC/GA4/Ads) - never the sign-in client.
    google_data_client_id: str = ""
    google_data_client_secret: SecretStr = SecretStr("")
    # Server-side key for PageSpeed Insights and the CrUX API (public data).
    google_api_key: SecretStr = SecretStr("")
    # Google Ads API (Keyword Planner): developer token + optional manager account.
    google_ads_developer_token: SecretStr = SecretStr("")
    google_ads_login_customer_id: str = ""
    google_ads_api_version: str = "v22"
    indexnow_endpoint: str = "https://api.indexnow.org/indexnow"
    gsc_backfill_days: int = 90  # GSC keeps 16 months; first sync fetches this much
    max_csv_import_bytes: int = 20 * 1024 * 1024

    # --- Search data engine (Module 8) ---------------------------------------------
    # Structured-JSON SERP vendor (DataForSEO, HTTP basic auth).
    dataforseo_login: str = ""
    dataforseo_password: SecretStr = SecretStr("")
    dataforseo_cost_micros: int = 2000  # live endpoint, USD micros per request
    # Generic "unblocker" returning raw HTML, parsed by our own parsers. The template
    # gets {url} (URL-encoded target) and {country}; the key goes in {key} or a header.
    rawhtml_endpoint: str = ""
    rawhtml_api_key: SecretStr = SecretStr("")
    rawhtml_cost_micros: int = 1000
    # Vendor order per engine ("*" = default), e.g. "google=dataforseo,rawhtml;*=dataforseo".
    serp_vendor_order: str = "*=dataforseo,rawhtml"
    serp_global_daily_requests: int = 20_000  # hard stop across all orgs (cost breaker)
    serp_validation_rate: float = 0.0  # share of fetches cross-checked with a 2nd vendor
    serp_cache_days: int = 1  # public SERPs are shared across orgs for this long

    # --- LLM gateway (Modules 9-10) -----------------------------------------------
    llm_enabled: bool = True  # global kill switch
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    # Answer-engine sampling (Module 10): ChatGPT search via the Responses API web-search
    # tool, Perplexity via its Sonar API. Unset keys = that engine is "not available".
    openai_search_model: str = "gpt-4.1-mini"
    perplexity_api_key: SecretStr = SecretStr("")
    perplexity_model: str = "sonar"

    # --- Billing (Module 12) - optional; billing pages say "not configured" when unset --
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    # Stripe price ids per plan/add-on: "pro=price_..,agency=price_..,engines_bing=price_.."
    stripe_prices: str = ""
    billing_grace_days: int = 7
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
    def broker_url(self) -> str:
        return self.celery_broker_url.get_secret_value() or self.redis_url.get_secret_value()

    @property
    def google_data_enabled(self) -> bool:
        return bool(
            self.google_data_client_id and self.google_data_client_secret.get_secret_value()
        )

    @property
    def google_sign_in_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret.get_secret_value())

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
        if self.jobs_backend != "celery":
            problems.append("jobs_backend must be 'celery' in staging/production")
        if self.renderer_url and len(self.renderer_token.get_secret_value()) < _MIN_SECRET_BYTES:
            problems.append("renderer_token must be >= 32 bytes when renderer_url is set")
        if self.email_backend != "smtp":
            problems.append("email_backend must be 'smtp' in staging/production")
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
