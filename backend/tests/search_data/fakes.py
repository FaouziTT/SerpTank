"""Deterministic fake SERP vendors."""

from __future__ import annotations

from dataclasses import dataclass, field

from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.schema import (
    AiAnswer,
    OrganicResult,
    SerpRequest,
    SerpSnapshotData,
)

DEFAULT_RANKING = [
    "www.runnersworld.com",
    "www.example-shop.com",
    "www.rival.com",
    "shoe-lab.example",
]


@dataclass
class FakeVendor:
    name: str = "fake"
    engines: frozenset[str] = frozenset({"google", "bing"})
    cost_micros: int = 1000
    ranking: list[str] = field(default_factory=lambda: list(DEFAULT_RANKING))
    fail_with: CollectorError | None = None
    calls: list[SerpRequest] = field(default_factory=list)
    ai_cites: list[str] = field(default_factory=list)

    async def fetch(self, request: SerpRequest) -> SerpSnapshotData:
        self.calls.append(request)
        if self.fail_with is not None:
            raise self.fail_with
        organic = [
            OrganicResult(
                position=i + 1,
                url=f"https://{d}/{request.query.replace(' ', '-')}",
                domain=d,
                title=f"{request.query} guide" if i else "Home",
            )
            for i, d in enumerate(self.ranking)
        ]
        features = ["people_also_ask"]
        answer = None
        if self.ai_cites:
            features.append("ai_overview")
            answer = AiAnswer(
                kind="ai_overview",
                cited_urls=[f"https://{d}/" for d in self.ai_cites],
                cited_domains=sorted(self.ai_cites),
            )
        return SerpSnapshotData(
            engine=request.engine,
            query=request.query,
            country=request.country,
            language=request.language,
            device=request.device,
            location=request.location,
            organic=organic,
            features=features,
            ai_answer=answer,
            people_also_ask=["What are good shoes?"],
        )
