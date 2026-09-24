"""Build the process-wide LLM gateway from settings."""

from __future__ import annotations

from serptank.core.config import Settings
from serptank.core.http import SafeHttpClient
from serptank.modules.llm.gateway import LlmGateway
from serptank.modules.llm.providers.openai import OpenAiProvider


def build_gateway(settings: Settings, http: SafeHttpClient) -> LlmGateway:
    key = settings.openai_api_key.get_secret_value()
    provider = OpenAiProvider(http, key, settings.openai_model) if key else None
    return LlmGateway(provider=provider, enabled=settings.llm_enabled)
