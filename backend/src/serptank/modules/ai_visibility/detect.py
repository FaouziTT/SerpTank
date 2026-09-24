"""Turn one AI answer into facts: is the brand mentioned or cited, who else is, how.

Pure functions. Matching is case-insensitive on word boundaries for brand terms and
competitor labels, and on host (domain or ``www`` twin) for cited URLs.

``sentiment`` is a small lexicon heuristic over the sentences that mention the brand
(-1..1). It is labelled as such in the UI, and it is ``None`` without a mention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

MAX_EXCERPT = 600
_POSITIVE_WORDS = """
best top leading excellent great recommended reliable popular trusted favorite
favourite affordable fast easy powerful comprehensive robust ideal standout
"""
POSITIVE = frozenset(_POSITIVE_WORDS.split())
_NEGATIVE_WORDS = """
worst poor bad expensive slow unreliable limited complicated outdated avoid
lacking weak issues problems complaints overpriced difficult
"""
NEGATIVE = frozenset(_NEGATIVE_WORDS.split())
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True)
class Entity:
    """A brand to look for: its hosts (for citations) and names (for mentions)."""

    key: str  # domain, used as the stable identifier
    hosts: frozenset[str]
    names: tuple[str, ...]


@dataclass
class Detection:
    mentioned: bool
    cited: bool
    mention_rank: int | None  # 1 = first brand named in the answer
    sentiment: float | None
    competitors: dict[str, dict[str, bool]] = field(default_factory=dict)
    excerpt: str = ""


def _hosts(domain: str) -> frozenset[str]:
    bare = domain.lower().removeprefix("www.")
    return frozenset({bare, f"www.{bare}"})


def entity_for(domain: str, extra_names: list[str] | None = None) -> Entity:
    """Names: the domain itself, its label ("example-shop"), spaced label, extras."""
    bare = domain.lower().removeprefix("www.")
    label = bare.split(".")[0]
    names = [bare, label, label.replace("-", " ")] + [n.lower() for n in extra_names or []]
    unique = tuple(dict.fromkeys(n.strip() for n in names if len(n.strip()) >= 3))  # noqa: PLR2004
    return Entity(key=bare, hosts=_hosts(bare), names=unique)


def _first_mention(text: str, entity: Entity) -> int | None:
    best: int | None = None
    for name in entity.names:
        match = re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text)
        if match and (best is None or match.start() < best):
            best = match.start()
    return best


def _cited(citations: list[str], entity: Entity) -> bool:
    return any((urlsplit(u).hostname or "").lower() in entity.hosts for u in citations)


def _sentiment(text: str, entity: Entity) -> float | None:
    sentences = [s for s in SENTENCE.split(text) if _first_mention(s.lower(), entity) is not None]
    if not sentences:
        return None
    words = re.findall(r"[a-z]+", " ".join(sentences).lower())
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    return 0.0 if pos + neg == 0 else round((pos - neg) / (pos + neg), 2)


def _excerpt(text: str, at: int | None) -> str:
    start = 0 if at is None else max(0, at - MAX_EXCERPT // 3)
    snippet = " ".join(text[start : start + MAX_EXCERPT].split())
    return ("…" if start else "") + snippet


def detect(text: str, citations: list[str], own: Entity, competitors: list[Entity]) -> Detection:
    lowered = text.lower()
    positions = {e.key: _first_mention(lowered, e) for e in [own, *competitors]}
    order = sorted((pos, key) for key, pos in positions.items() if pos is not None)
    ranks = {key: i + 1 for i, (_, key) in enumerate(order)}
    own_at = positions[own.key]
    return Detection(
        mentioned=own_at is not None,
        cited=_cited(citations, own),
        mention_rank=ranks.get(own.key),
        sentiment=_sentiment(lowered, own),
        competitors={
            c.key: {"mentioned": positions[c.key] is not None, "cited": _cited(citations, c)}
            for c in competitors
        },
        excerpt=_excerpt(text, own_at),
    )
