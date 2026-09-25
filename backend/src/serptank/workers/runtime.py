"""Build the shared :class:`JobRuntime` for an API process or a worker process."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank import job_handlers  # noqa: F401 - registers handlers
from serptank.core.config import Settings
from serptank.core.crypto import Keyring, keyring_from_settings
from serptank.core.email import EmailSender, create_email_sender
from serptank.core.http import EgressPolicy, Resolver, SafeHttpClient, system_resolver
from serptank.modules.ai_visibility.engines import build_engines
from serptank.modules.crawler.rendering import RendererClient
from serptank.modules.jobs.service import HttpFactory, JobRuntime
from serptank.modules.llm.factory import build_gateway
from serptank.modules.search_data.collector import CollectorRouter
from serptank.modules.search_data.factory import build_router


def default_http_factory(
    resolver: Resolver = system_resolver, transport: httpx.AsyncBaseTransport | None = None
) -> HttpFactory:
    def factory(policy: EgressPolicy, user_agent: str) -> SafeHttpClient:
        return SafeHttpClient(policy, resolver=resolver, transport=transport, user_agent=user_agent)

    return factory


def build_runtime(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    http_factory: HttpFactory | None = None,
    renderer: RendererClient | None = None,
    keyring: Keyring | None = None,
    serp_router: CollectorRouter | None = None,
    email: EmailSender | None = None,
) -> JobRuntime:
    # Alert emails (tests pass an in-memory sender).
    extras: dict[str, Any] = {"email": email or create_email_sender(settings)}
    if renderer is not None:
        extras["renderer"] = renderer
    elif settings.renderer_url:
        extras["renderer"] = RendererClient(
            settings.renderer_url, settings.renderer_token.get_secret_value()
        )
    factory = http_factory or default_http_factory()
    if serp_router is None:
        # SERP vendors get their own client (closed in close_runtime).
        serp_http = factory(EgressPolicy(), settings.crawler_user_agent)
        extras["serp_http"] = serp_http
        serp_router = build_router(settings, serp_http)
    extras["serp"] = serp_router
    # The LLM provider gets its own client too (no redirects to follow, JSON only).
    llm_http = factory(EgressPolicy(), settings.crawler_user_agent)
    extras["llm_http"] = llm_http
    extras["llm"] = build_gateway(settings, llm_http)
    extras["answer_engines"] = build_engines(settings, llm_http)
    # Stripe calls get their own client too.
    extras["billing_http"] = factory(EgressPolicy(), settings.crawler_user_agent)
    return JobRuntime(
        settings=settings,
        session_factory=session_factory,
        http_factory=factory,
        keyring=keyring or keyring_from_settings(settings),
        extras=extras,
    )


async def close_runtime(runtime: JobRuntime) -> None:
    renderer = runtime.extras.get("renderer")
    if isinstance(renderer, RendererClient):
        await renderer.aclose()
    for name in ("serp_http", "llm_http", "billing_http"):
        client = runtime.extras.get(name)
        if isinstance(client, SafeHttpClient):
            await client.aclose()
