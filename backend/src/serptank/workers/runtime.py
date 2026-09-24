"""Build the shared :class:`JobRuntime` for an API process or a worker process."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from serptank import job_handlers  # noqa: F401 - registers handlers
from serptank.core.config import Settings
from serptank.core.crypto import Keyring, keyring_from_settings
from serptank.core.http import EgressPolicy, Resolver, SafeHttpClient, system_resolver
from serptank.modules.crawler.rendering import RendererClient
from serptank.modules.jobs.service import HttpFactory, JobRuntime


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
) -> JobRuntime:
    extras: dict[str, Any] = {}
    if renderer is not None:
        extras["renderer"] = renderer
    elif settings.renderer_url:
        extras["renderer"] = RendererClient(
            settings.renderer_url, settings.renderer_token.get_secret_value()
        )
    return JobRuntime(
        settings=settings,
        session_factory=session_factory,
        http_factory=http_factory or default_http_factory(),
        keyring=keyring or keyring_from_settings(settings),
        extras=extras,
    )


async def close_runtime(runtime: JobRuntime) -> None:
    renderer = runtime.extras.get("renderer")
    if isinstance(renderer, RendererClient):
        await renderer.aclose()
