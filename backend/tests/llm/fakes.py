"""Deterministic fake LLM provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from serptank.modules.llm.gateway import Completion


@dataclass
class FakeLlm:
    name: str = "fake"
    reply: str = "{}"
    tokens: tuple[int, int] = (100, 50)
    fail: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def complete(
        self, *, system: str, user: str, schema: dict[str, Any], max_output_tokens: int
    ) -> Completion:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if self.fail is not None:
            raise self.fail
        return Completion(self.reply, self.tokens[0], self.tokens[1], "fake-model")
