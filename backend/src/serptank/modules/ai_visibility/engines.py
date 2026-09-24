"""Answer engines we can sample through official APIs.

* ``chatgpt``    - OpenAI Responses API with the ``web_search`` tool (what ChatGPT search
  uses); citations come from ``url_citation`` annotations.
* ``perplexity`` - Perplexity Sonar API; citations come from ``citations`` /
  ``search_results``.

Gemini, Copilot and Claude have no sampling adapter yet; they are reported as "not
available" (Copilot citation data arrives through the Bing AI Performance import).
Google AI Overviews come from the SERP collector, not from here. The customer's prompt
is sent as-is, with no system prompt, so the answer is the one a user would get.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from serptank.core.config import Settings
from serptank.core.http import EgressError, EgressPolicy, SafeHttpClient
from serptank.modules.llm.gateway import LlmError

POLICY = EgressPolicy(max_response_bytes=4 * 1024 * 1024, total_timeout_s=120)
MAX_ANSWER_CHARS = 20_000
MAX_CITATIONS = 30


@dataclass
class EngineAnswer:
    text: str
    citations: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


class AnswerEngine(Protocol):
    name: str

    async def answer(self, prompt: str, *, country: str) -> EngineAnswer: ...


def _unique(urls: list[str]) -> list[str]:
    valid = (u for u in urls if u.startswith(("http://", "https://")))
    return list(dict.fromkeys(valid))[:MAX_CITATIONS]


async def _post(
    http: SafeHttpClient, url: str, api_key: str, body: dict[str, Any]
) -> dict[str, Any]:
    try:
        response = await http.request(
            "POST",
            url,
            headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
            content=json.dumps(body).encode(),
            policy=POLICY,
        )
    except EgressError as exc:
        raise LlmError("llm_unavailable", "The answer engine is unavailable right now.") from exc
    if response.status_code == 429:  # noqa: PLR2004
        raise LlmError("llm_rate_limited", "The answer engine is busy; try again later.")
    if response.status_code != 200:  # noqa: PLR2004
        raise LlmError("llm_unavailable", "The answer engine refused the request.")
    try:
        data = json.loads(response.content)
    except ValueError as exc:
        raise LlmError("llm_invalid_output", "The answer engine returned bad data.") from exc
    if not isinstance(data, dict):
        raise LlmError("llm_invalid_output", "The answer engine returned bad data.")
    return data


class OpenAiSearchEngine:
    name = "chatgpt"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, http: SafeHttpClient, api_key: str, model: str) -> None:
        self.http, self.api_key, self.model = http, api_key, model

    async def answer(self, prompt: str, *, country: str) -> EngineAnswer:
        data = await _post(
            self.http,
            self.endpoint,
            self.api_key,
            {
                "model": self.model,
                "input": prompt,
                "tools": [
                    {
                        "type": "web_search",
                        "user_location": {"type": "approximate", "country": country},
                    }
                ],
                "max_output_tokens": 1500,
            },
        )
        texts: list[str] = []
        citations: list[str] = []
        for item in data.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    texts.append(str(part.get("text", "")))
                    citations += [
                        str(a.get("url", ""))
                        for a in part.get("annotations") or []
                        if isinstance(a, dict) and a.get("type") == "url_citation"
                    ]
        if not texts:
            raise LlmError("llm_invalid_output", "The answer engine returned no answer.")
        usage = data.get("usage") or {}
        return EngineAnswer(
            text="\n".join(texts)[:MAX_ANSWER_CHARS],
            citations=_unique(citations),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            model=str(data.get("model", self.model)),
        )


class PerplexityEngine:
    name = "perplexity"
    endpoint = "https://api.perplexity.ai/chat/completions"

    def __init__(self, http: SafeHttpClient, api_key: str, model: str) -> None:
        self.http, self.api_key, self.model = http, api_key, model

    async def answer(self, prompt: str, *, country: str) -> EngineAnswer:
        data = await _post(
            self.http,
            self.endpoint,
            self.api_key,
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "web_search_options": {"user_location": {"country": country}},
            },
        )
        try:
            text = str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError("llm_invalid_output", "The answer engine returned no answer.") from exc
        urls = [str(u) for u in data.get("citations") or [] if isinstance(u, str)]
        urls += [
            str(r.get("url", "")) for r in data.get("search_results") or [] if isinstance(r, dict)
        ]
        usage = data.get("usage") or {}
        return EngineAnswer(
            text=text[:MAX_ANSWER_CHARS],
            citations=_unique(urls),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            model=str(data.get("model", self.model)),
        )


def build_engines(settings: Settings, http: SafeHttpClient) -> dict[str, AnswerEngine]:
    engines: dict[str, AnswerEngine] = {}
    if settings.llm_enabled and settings.openai_api_key.get_secret_value():
        engines["chatgpt"] = OpenAiSearchEngine(
            http, settings.openai_api_key.get_secret_value(), settings.openai_search_model
        )
    if settings.llm_enabled and settings.perplexity_api_key.get_secret_value():
        engines["perplexity"] = PerplexityEngine(
            http, settings.perplexity_api_key.get_secret_value(), settings.perplexity_model
        )
    return engines
