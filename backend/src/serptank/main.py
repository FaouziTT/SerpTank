"""FastAPI application factory.

Production entrypoint (see backend/Dockerfile)::

    uvicorn --factory serptank.main:create_app --no-proxy-headers

Proxy headers are handled by our own middleware using ``SERPTANK_TRUSTED_PROXIES``.
Tests call :func:`create_app` with explicit settings.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from serptank import __version__
from serptank.api import health
from serptank.core.config import Settings, get_settings
from serptank.core.crypto import Keyring
from serptank.core.db import create_engine, create_session_factory
from serptank.core.email import EmailSender, create_email_sender
from serptank.core.errors import register_error_handlers
from serptank.core.http import SafeHttpClient
from serptank.core.logging import configure_logging
from serptank.core.metrics import MetricsMiddleware, start_metrics_server
from serptank.core.middleware import (
    BodySizeLimitMiddleware,
    CsrfMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from serptank.core.ratelimit import RateLimiter
from serptank.core.redis import create_redis
from serptank.modules.identity import router as identity_router
from serptank.modules.identity.brute_force import (
    CaptchaVerifier,
    DisabledCaptcha,
    LoginThrottle,
    TurnstileVerifier,
)
from serptank.modules.identity.csrf import build_csrf_hooks
from serptank.modules.identity.deps import IdentityServices
from serptank.modules.identity.google import GoogleOidcClient
from serptank.modules.identity.passkeys import PasskeyConfig, PasskeyService
from serptank.modules.identity.passwords import (
    BreachChecker,
    HibpBreachChecker,
    NoBreachChecker,
    PasswordHasher,
)
from serptank.modules.identity.sessions import SessionStore
from serptank.modules.projects import router as projects_router
from serptank.modules.tenancy import router as tenancy_router

API_PREFIX = "/api/v1"
logger = structlog.get_logger(__name__)


def build_keyring(settings: Settings) -> Keyring:
    keys = settings.parsed_encryption_keys()
    if keys:
        return Keyring(keys, settings.encryption_active_key_id)
    # Only reachable outside staging/production (config validation fails closed there).
    logger.warning("ephemeral_encryption_key", detail="data encrypted now is lost on restart")
    return Keyring({"ephemeral": secrets.token_bytes(32)}, "ephemeral")


def build_identity(
    settings: Settings,
    redis: Redis,
    limiter: RateLimiter,
    *,
    http: SafeHttpClient | None = None,
    email: EmailSender | None = None,
    breach_checker: BreachChecker | None = None,
    captcha: CaptchaVerifier | None = None,
) -> IdentityServices:
    http = http or SafeHttpClient()
    turnstile_secret = settings.turnstile_secret.get_secret_value()
    captcha = captcha or (
        TurnstileVerifier(http, turnstile_secret) if turnstile_secret else DisabledCaptcha()
    )
    if breach_checker is None:
        breach_checker = (
            HibpBreachChecker(http) if settings.breached_password_check else NoBreachChecker()
        )
    return IdentityServices(
        settings=settings,
        redis=redis,
        store=SessionStore(redis, settings),
        hasher=PasswordHasher(),
        breach_checker=breach_checker,
        throttle=LoginThrottle(redis, limiter, captcha),
        email=email or create_email_sender(settings),
        keyring=build_keyring(settings),
        passkeys=PasskeyService(PasskeyConfig.from_settings(settings), redis),
        google=GoogleOidcClient(settings, redis, http),
        http=http,
        captcha=captcha,
    )


DOCS_PATHS = (f"{API_PREFIX}/docs", f"{API_PREFIX}/openapi.json")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.engine = create_engine(settings)
        app.state.session_factory = create_session_factory(app.state.engine)
        app.state.redis = create_redis(settings)
        app.state.rate_limiter = RateLimiter(app.state.redis)
        overrides = getattr(app.state, "identity_overrides", {})
        app.state.identity = build_identity(
            settings, app.state.redis, app.state.rate_limiter, **overrides
        )
        if settings.metrics_port:
            start_metrics_server(settings.metrics_port, settings.metrics_bind_address)
        try:
            yield
        finally:
            await app.state.identity.http.aclose()
            await app.state.redis.aclose()
            await app.state.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url=DOCS_PATHS[0] if settings.show_docs else None,
        redoc_url=None,
        openapi_url=DOCS_PATHS[1] if settings.show_docs else None,
        redirect_slashes=False,
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(identity_router.router, prefix=API_PREFIX)
    app.include_router(identity_router.org_router, prefix=API_PREFIX)
    app.include_router(tenancy_router.router, prefix=API_PREFIX)
    app.include_router(projects_router.router, prefix=API_PREFIX)

    # Middleware: the LAST added runs FIRST (outermost). Listed innermost -> outermost.
    session_detector, token_verifier = build_csrf_hooks(settings)
    app.add_middleware(
        CsrfMiddleware,
        allowed_origins=[settings.public_origin, *settings.extra_allowed_origins],
        exempt_paths=(),
        session_detector=session_detector,
        token_verifier=token_verifier,
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts=settings.cookie_secure,
        docs_paths=DOCS_PATHS if settings.show_docs else (),
    )
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_proxies)
    return app
