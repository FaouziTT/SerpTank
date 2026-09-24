"""FastAPI application factory.

Production entrypoint (see backend/Dockerfile)::

    uvicorn --factory serptank.main:create_app --no-proxy-headers

Proxy headers are handled by our own middleware using ``SERPTANK_TRUSTED_PROXIES``.
Tests call :func:`create_app` with explicit settings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from serptank import __version__
from serptank.api import health
from serptank.core.config import Settings, get_settings
from serptank.core.db import create_engine, create_session_factory
from serptank.core.errors import register_error_handlers
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

API_PREFIX = "/api/v1"
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
        if settings.metrics_port:
            start_metrics_server(settings.metrics_port, settings.metrics_bind_address)
        try:
            yield
        finally:
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

    # Middleware: the LAST added runs FIRST (outermost). Listed innermost -> outermost.
    app.add_middleware(
        CsrfMiddleware,
        allowed_origins=[settings.public_origin, *settings.extra_allowed_origins],
        exempt_paths=(),
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
