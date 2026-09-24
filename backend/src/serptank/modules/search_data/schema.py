"""Normalized SERP model: every source (vendor JSON, our HTML parsers) maps to this.

Pure dataclasses, JSON-serializable, engine-agnostic (plan §4.5). Positions are
1-based ranks among organic results ("rank_group" in vendor terms); ``absolute`` is
the position counting every block on the page, when the source provides it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# SERP features we normalize (anything else is kept as "other:<name>").
FEATURES = frozenset(
    {
        "ai_overview",
        "ai_mode",
        "featured_snippet",
        "people_also_ask",
        "local_pack",
        "top_stories",
        "images",
        "video",
        "shopping",
        "knowledge_panel",
        "sitelinks",
        "related_searches",
        "twitter",
    }
)


@dataclass
class OrganicResult:
    position: int
    url: str
    domain: str
    title: str = ""
    snippet: str = ""
    absolute: int | None = None


@dataclass
class AiAnswer:
    """An AI Overview / AI Mode answer block and the sources it cites."""

    kind: str  # "ai_overview" | "ai_mode"
    cited_urls: list[str] = field(default_factory=list)
    cited_domains: list[str] = field(default_factory=list)
    text: str = ""


@dataclass
class SerpSnapshotData:
    engine: str
    query: str
    country: str
    language: str
    device: str
    location: str | None
    organic: list[OrganicResult] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    ai_answer: AiAnswer | None = None
    people_also_ask: list[str] = field(default_factory=list)
    related_searches: list[str] = field(default_factory=list)
    total_results: int | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> SerpSnapshotData:
        ai = data.get("ai_answer")
        return cls(
            engine=data["engine"],
            query=data["query"],
            country=data["country"],
            language=data["language"],
            device=data["device"],
            location=data.get("location"),
            organic=[OrganicResult(**o) for o in data.get("organic", [])],
            features=list(data.get("features", [])),
            ai_answer=AiAnswer(**ai) if ai else None,
            people_also_ask=list(data.get("people_also_ask", [])),
            related_searches=list(data.get("related_searches", [])),
            total_results=data.get("total_results"),
        )

    def position_of(self, hosts: frozenset[str]) -> OrganicResult | None:
        """Best-ranked organic result on one of ``hosts`` (domain or www twin)."""
        for result in self.organic:
            if result.domain.lower() in hosts:
                return result
        return None

    def cites(self, hosts: frozenset[str]) -> bool:
        return self.ai_answer is not None and any(
            d.lower() in hosts for d in self.ai_answer.cited_domains
        )


@dataclass(frozen=True)
class SerpRequest:
    engine: str
    query: str
    country: str
    language: str
    device: str = "desktop"
    location: str | None = None
    depth: int = 100  # results wanted (vendors paginate internally)


def normalize_query(query: str) -> str:
    """Cache key form: trimmed, lower-cased, single-spaced (Google treats these alike)."""
    return " ".join(query.lower().split())[:300]
