"""Red flags for Google's spam policies. These are prompts to review, not verdicts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site
from serptank.modules.crawler.similarity import from_signed, hamming

REF_SPAM = "https://developers.google.com/search/docs/essentials/spam-policies"
HIDDEN_WORDS = 150
NEAR_DUP_BITS = 3
DOORWAY_CLUSTER = 5
MIN_WORDS = 50


@rule(
    "hidden_text",
    title="Large amounts of hidden text",
    category="spam",
    severity=Severity.LOW,
    description="Text hidden with inline CSS (display:none, zero font size, off-screen indent). "
    "Menus and tabs are fine; hiding keyword-rich text from users violates spam policies.",
    fix="Review the hidden blocks and make sure they serve users (e.g. accordions, menus).",
    effort=1,
    reference=REF_SPAM,
)
def hidden_text(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        hidden = int(page.data.get("hidden_words") or 0)
        if hidden >= HIDDEN_WORDS:
            yield Finding(page.url, {"hidden_words": hidden})


@rule(
    "doorway_patterns",
    title="Clusters of near-identical pages",
    category="spam",
    severity=Severity.MEDIUM,
    description="Many indexable pages with almost the same text but different titles - a typical "
    "doorway pattern (e.g. one page per city with swapped names).",
    fix="Merge them into fewer, genuinely distinct pages, or noindex the variants.",
    effort=3,
    reference=REF_SPAM,
)
def doorway_patterns(site: Site) -> Iterator[Finding]:
    pages = [
        p
        for p in site.html_pages
        if p.indexable() and p.simhash and int(p.data.get("word_count") or 0) >= MIN_WORDS
    ]
    # Locality-sensitive bucketing: near-duplicates (<=3 differing bits of 64) must share
    # at least one of four 16-bit bands exactly (pigeonhole).
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    hashes = [from_signed(p.simhash or 0) for p in pages]
    for index, value in enumerate(hashes):
        for band in range(4):
            buckets[(band, (value >> (16 * band)) & 0xFFFF)].append(index)
    parent = list(range(len(pages)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for members in buckets.values():
        if len(members) > 500:  # noqa: PLR2004 - pathological bucket; skip rather than go quadratic
            continue
        for a_pos, a in enumerate(members):
            for b in members[a_pos + 1 :]:
                if (
                    hamming(hashes[a], hashes[b]) <= NEAR_DUP_BITS
                    and pages[a].content_hash != pages[b].content_hash
                ):
                    parent[find(a)] = find(b)
    clusters: dict[int, list[int]] = defaultdict(list)
    for index in range(len(pages)):
        clusters[find(index)].append(index)
    for members in clusters.values():
        titles = {(pages[i].title or "").lower() for i in members}
        if len(members) >= DOORWAY_CLUSTER and len(titles) > 1:
            urls = [pages[i].url for i in members]
            for url in urls:
                yield Finding(
                    url, {"cluster_size": len(urls), "examples": [u for u in urls if u != url][:4]}
                )
