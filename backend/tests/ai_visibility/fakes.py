"""Deterministic fake answer engines."""

from __future__ import annotations

from dataclasses import dataclass, field

from serptank.modules.ai_visibility.engines import EngineAnswer
from serptank.modules.llm.gateway import LlmError


@dataclass
class FakeEngine:
    name: str
    text: str
    citations: list[str] = field(default_factory=list)
    fail: LlmError | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def answer(self, prompt: str, *, country: str) -> EngineAnswer:
        self.calls.append((prompt, country))
        if self.fail is not None:
            raise self.fail
        return EngineAnswer(self.text, list(self.citations), 40, 60, f"{self.name}-model")
