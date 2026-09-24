"""Search intent classification (rule-based, explainable).

Signals, strongest first: SERP features when we have the SERP (shopping -> transactional,
local pack -> local, ...), then modifier words. Every result carries its reasons so the
UI can show *why*, and "unknown" is a valid answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TRANSACTIONAL = {
    "buy",
    "price",
    "prices",
    "cheap",
    "deal",
    "deals",
    "discount",
    "coupon",
    "order",
    "shop",
    "sale",
    "for sale",
    "kaufen",
    "preis",
    "acheter",
    "comprar",
}
COMMERCIAL = {
    "best",
    "top",
    "review",
    "reviews",
    "vs",
    "versus",
    "compare",
    "comparison",
    "alternative",
    "alternatives",
    "test",
    "beste",
}
INFORMATIONAL = {
    "how",
    "what",
    "why",
    "when",
    "who",
    "where",
    "guide",
    "tutorial",
    "tips",
    "ideas",
    "examples",
    "meaning",
    "definition",
    "wie",
    "was",
    "comment",
    "cómo",
}
LOCAL = {"near me", "nearby", "open now", "in my area"}
NAVIGATIONAL = {"login", "log in", "sign in", "account", "official site", "website", "app download"}

FEATURE_INTENT = {
    "shopping": "transactional",
    "local_pack": "local",
    "people_also_ask": "informational",
    "featured_snippet": "informational",
    "knowledge_panel": "navigational",
}


@dataclass
class Intent:
    primary: str  # transactional | commercial | informational | navigational | local | unknown
    reasons: list[str] = field(default_factory=list)


def classify(
    keyword: str, features: list[str] | None = None, brand_terms: set[str] | None = None
) -> Intent:
    text = f" {' '.join(keyword.lower().split())} "
    words = set(text.split())
    scores: dict[str, float] = {}
    reasons: list[str] = []

    def add(intent: str, weight: float, reason: str) -> None:
        scores[intent] = scores.get(intent, 0.0) + weight
        reasons.append(reason)

    for phrase in LOCAL:
        if f" {phrase} " in text:
            add("local", 3, f"contains “{phrase}”")
    for phrase in NAVIGATIONAL:
        if f" {phrase} " in text:
            add("navigational", 2, f"contains “{phrase}”")
    for group, intent, weight in (
        (TRANSACTIONAL, "transactional", 2.0),
        (COMMERCIAL, "commercial", 2.0),
        (INFORMATIONAL, "informational", 1.5),
    ):
        hits = sorted(w for w in group if (" " in w and f" {w} " in text) or w in words)
        if hits:
            add(intent, weight * len(hits), f"modifier “{hits[0]}”")
    if brand_terms and words & brand_terms:
        add("navigational", 2.5, "contains a brand term")
    for feature in features or []:
        feature_intent = FEATURE_INTENT.get(feature)
        if feature_intent:
            add(feature_intent, 1.5, f"SERP shows {feature.replace('_', ' ')}")
    if keyword.strip().endswith("?"):
        add("informational", 1.0, "phrased as a question")
    if not scores:
        return Intent("unknown", [])
    primary = max(scores.items(), key=lambda kv: kv[1])[0]
    return Intent(primary, reasons[:4])
