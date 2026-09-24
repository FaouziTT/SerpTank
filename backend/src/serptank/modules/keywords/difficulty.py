"""SerpTank keyword difficulty (KD), computed from the SERP itself.

No backlink index is involved (that's Phase B), so KD v1 is an explicit, explainable
heuristic on 0-100 built from what we *can* observe in a snapshot:

* **Prominence** (45 %): how often the ranking domains appear in top-10s across our
  global SERP cache - strong, broad-coverage domains are hard to displace.
* **Targeting** (25 %): share of top-10 titles containing the full keyword.
* **Root pages** (15 %): share of homepages ranking (brand/authority signals).
* **Crowding** (15 %): SERP features pushing organic results down (AI answer, local
  pack, shopping, video, top stories, featured snippet).

It returns its components so the UI can explain the number, plus a confidence label.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from serptank.modules.search_data.schema import SerpSnapshotData

CROWDING = {
    "ai_overview": 1.0,
    "local_pack": 0.8,
    "shopping": 0.8,
    "featured_snippet": 0.6,
    "video": 0.4,
    "top_stories": 0.4,
    "images": 0.2,
}
PROMINENT_AT = 50  # a domain in >= this many cached top-10s counts as fully prominent


@dataclass
class Difficulty:
    score: int
    prominence: float
    targeting: float
    root_pages: float
    crowding: float
    confidence: str  # "low" when the cache is small


def compute(
    snapshot: SerpSnapshotData, domain_frequency: dict[str, int], cache_size: int
) -> Difficulty:
    top = snapshot.organic[:10]
    if not top:
        return Difficulty(0, 0.0, 0.0, 0.0, 0.0, "low")
    query = snapshot.query.lower()
    prominence = sum(min(1.0, domain_frequency.get(r.domain, 0) / PROMINENT_AT) for r in top) / len(
        top
    )
    targeting = sum(1 for r in top if query in r.title.lower()) / len(top)
    root_pages = sum(1 for r in top if urlsplit(r.url).path in {"", "/"}) / len(top)
    crowding = min(1.0, sum(CROWDING.get(f, 0.0) for f in snapshot.features) / 2.0)
    score = round(
        100 * (0.45 * prominence + 0.25 * targeting + 0.15 * root_pages + 0.15 * crowding)
    )
    confidence = "high" if cache_size >= 5000 else "medium" if cache_size >= 500 else "low"  # noqa: PLR2004
    return Difficulty(
        score,
        round(prominence, 3),
        round(targeting, 3),
        round(root_pages, 3),
        round(crowding, 3),
        confidence,
    )
