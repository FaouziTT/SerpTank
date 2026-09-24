"""Pure AI-visibility logic: detection, statistics, prompt suggestions, engine adapters."""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from serptank.core.config import Settings
from serptank.core.http import SafeHttpClient
from serptank.modules.ai_visibility.detect import detect, entity_for
from serptank.modules.ai_visibility.engines import (
    OpenAiSearchEngine,
    PerplexityEngine,
    build_engines,
)
from serptank.modules.ai_visibility.router import suggest_prompt
from serptank.modules.ai_visibility.stats import wilson
from serptank.modules.llm.gateway import LlmError

OWN = entity_for("www.example-shop.com", ["Example Shop"])
RIVAL = entity_for("rival.com", ["Rival"])
GEAR = entity_for("gearlab.example")


def test_entities() -> None:
    assert OWN.key == "example-shop.com"
    assert OWN.hosts == frozenset({"example-shop.com", "www.example-shop.com"})
    assert "example shop" in OWN.names
    assert entity_for("ab.io").names == ("ab.io",)  # 2-letter label dropped


def test_detect_mentions_citations_rank_and_sentiment() -> None:
    text = (
        "For trail running, Rival is popular. Example Shop is the best and most reliable "
        "choice.\nGearlab is expensive."
    )
    found = detect(
        text,
        ["https://www.example-shop.com/trail", "https://news.example/x"],
        OWN,
        [RIVAL, GEAR],
    )
    assert found.mentioned
    assert found.cited
    assert found.mention_rank == 2  # Rival is named first
    assert found.sentiment == 1.0
    assert found.competitors == {
        "rival.com": {"mentioned": True, "cited": False},
        "gearlab.example": {"mentioned": True, "cited": False},
    }
    assert "Example Shop" in found.excerpt


def test_detect_word_boundaries_and_absence() -> None:
    found = detect("Visit example-shopping.com or myexample shop", [], OWN, [])
    assert not found.mentioned
    assert found.sentiment is None
    assert found.mention_rank is None
    assert not detect("", ["https://evil-example-shop.com/"], OWN, []).cited


def test_wilson() -> None:
    empty = wilson(0, 0)
    assert empty.rate is None
    assert empty.low is None
    half = wilson(5, 10)
    assert half.rate == 0.5
    assert half.low == pytest.approx(0.2366, abs=1e-3)
    assert half.high == pytest.approx(0.7634, abs=1e-3)
    assert wilson(0, 3).low == 0.0
    assert wilson(3, 3).high == 1.0


def test_prompt_suggestions() -> None:
    assert suggest_prompt("how to lace trail shoes", "informational") == "How to lace trail shoes?"
    assert suggest_prompt("buy trail shoes", "transactional").startswith("Where is the best place")
    assert "recommend" in suggest_prompt("trail shoes", "commercial")


async def _public(_host: str, _port: int) -> list[str]:
    return ["93.184.215.34"]


async def test_openai_and_perplexity_adapters() -> None:
    seen: list[dict[str, object]] = []

    def api(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if request.headers["host"] == "api.openai.com":
            return httpx.Response(
                200,
                json={
                    "model": "gpt-x",
                    "output": [
                        {"type": "web_search_call", "status": "completed"},
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Example Shop leads.",
                                    "annotations": [
                                        {"type": "url_citation", "url": "https://a.example/1"},
                                        {"type": "url_citation", "url": "https://a.example/1"},
                                        {"type": "file_citation", "file_id": "x"},
                                    ],
                                }
                            ],
                        },
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                },
            )
        if body.get("messages", [{}])[0].get("content") == "busy":
            return httpx.Response(429)
        return httpx.Response(
            200,
            json={
                "model": "sonar",
                "choices": [{"message": {"content": "Rival wins."}}],
                "citations": ["https://b.example/"],
                "search_results": [{"url": "https://c.example/"}, {"url": "javascript:alert(1)"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7},
            },
        )

    http = SafeHttpClient(resolver=_public, transport=httpx.MockTransport(api))
    chat = await OpenAiSearchEngine(http, "k", "gpt-x").answer("best shoes", country="GB")
    assert chat.text == "Example Shop leads."
    assert chat.citations == ["https://a.example/1"]
    assert (chat.input_tokens, chat.output_tokens) == (10, 20)
    assert seen[0]["tools"] == [
        {"type": "web_search", "user_location": {"type": "approximate", "country": "GB"}}
    ]
    pplx = PerplexityEngine(http, "k", "sonar")
    answer = await pplx.answer("best shoes", country="US")
    assert answer.citations == ["https://b.example/", "https://c.example/"]
    with pytest.raises(LlmError) as exc:
        await pplx.answer("busy", country="US")
    assert exc.value.code == "llm_rate_limited"
    await http.aclose()


def test_build_engines() -> None:
    http = SafeHttpClient()
    assert build_engines(Settings(), http) == {}
    both = build_engines(
        Settings(openai_api_key=SecretStr("a"), perplexity_api_key=SecretStr("b")), http
    )
    assert set(both) == {"chatgpt", "perplexity"}
    off = Settings(openai_api_key=SecretStr("a"), llm_enabled=False)
    assert build_engines(off, http) == {}
