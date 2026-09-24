"""OpenAI adapter (Chat Completions with JSON-schema structured outputs), via SafeHttpClient."""

from __future__ import annotations

import json
from typing import Any

from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient
from serptank.modules.llm.gateway import Completion, LlmError

API = "https://api.openai.com/v1/chat/completions"
POLICY = EgressPolicy(max_response_bytes=2 * 1024 * 1024, total_timeout_s=90)


class OpenAiProvider:
    name = "openai"

    def __init__(self, http: SafeHttpClient, api_key: str, model: str) -> None:
        self.http = http
        self.api_key = api_key
        self.model = model

    async def complete(
        self, *, system: str, user: str, schema: dict[str, Any], max_output_tokens: int
    ) -> Completion:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_completion_tokens": max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": schema},
            },
        }
        try:
            response = await self.http.request(
                "POST",
                API,
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
                content=json.dumps(body).encode(),
                policy=POLICY,
            )
        except EgressError as exc:
            raise LlmError("llm_unavailable", "The AI provider is unavailable right now.") from exc
        if response.status_code == 429:  # noqa: PLR2004
            raise LlmError("llm_rate_limited", "The AI provider is busy; please try again shortly.")
        if response.status_code != 200:  # noqa: PLR2004
            raise LlmError("llm_unavailable", "The AI provider refused the request.")
        try:
            data = json.loads(response.content)
            text = str(data["choices"][0]["message"]["content"] or "")
            usage = data.get("usage") or {}
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LlmError("llm_invalid_output", "The AI returned an unusable answer.") from exc
        return Completion(
            text=text,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            model=str(data.get("model", self.model)),
        )
