"""HTTP front for the renderer (internal network only, bearer-token authenticated).

uvicorn --factory serptank.renderer.app:create_app --port 8100
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic import BaseModel, ConfigDict, Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from serptank.core.config import Settings, get_settings
from serptank.core.crypto import constant_time_equals
from serptank.core.http import EgressError, SafeHttpClient, normalize_public_url
from serptank.core.logging import configure_logging
from serptank.renderer.browser import Renderer


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(max_length=2048)
    user_agent: str = Field(max_length=300)
    mobile: bool = False


def create_app(settings: Settings | None = None, renderer: Renderer | None = None) -> Starlette:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.log_json)
    token = settings.renderer_token.get_secret_value()

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        own = renderer is None
        app.state.renderer = renderer or Renderer(
            SafeHttpClient(user_agent=settings.crawler_user_agent),
            executable_path=settings.renderer_chromium_path or None,
        )
        if own:
            await app.state.renderer.start()
        try:
            yield
        finally:
            if own:
                await app.state.renderer.stop()
                await app.state.renderer.http.aclose()

    async def render(request: Request) -> JSONResponse:
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
        if not token or not constant_time_equals(supplied, token):
            return JSONResponse({"code": "unauthorized"}, status_code=401)
        try:
            body = RenderRequest.model_validate(await request.json())
            url = normalize_public_url(body.url)
        except (ValueError, EgressError):
            return JSONResponse({"code": "invalid_request"}, status_code=422)
        result = await request.app.state.renderer.render(
            url, user_agent=body.user_agent, mobile=body.mobile
        )
        return JSONResponse(result.to_json())

    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return Starlette(
        routes=[Route("/render", render, methods=["POST"]), Route("/healthz", healthz)],
        lifespan=lifespan,
    )
