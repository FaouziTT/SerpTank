"""SERP-based content briefs: what a new page needs to compete for a keyword.

Built only from observed evidence - the live SERP (features, People Also Ask, related
searches, AI answer citations) and the ranking pages we could read (headings, length,
terms, schema). Nothing is invented; sections without evidence are left empty and the
brief says so.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

from serptank.modules.onpage.analyzer import INTENT_SCHEMA, dominant_schema, important_terms
from serptank.modules.onpage.text import PageContent, content_terms, words
from serptank.modules.search_data.schema import SerpSnapshotData

MAX_SECTIONS = 12
SIMILAR = 0.5  # Jaccard similarity for grouping competitor headings


@dataclass
class Section:
    heading: str
    pages: int  # how many ranking pages cover it
    variants: list[str] = field(default_factory=list)


@dataclass
class Brief:
    keyword: str
    intent: str
    intent_reasons: list[str]
    word_count_range: tuple[int, int] | None
    outline: list[Section]
    questions: list[str]
    terms: list[str]
    secondary_keywords: list[str]
    schema_type: str
    serp_features: list[str]
    ai_answer: dict[str, Any] | None
    competitors: list[dict[str, Any]]
    internal_links: list[dict[str, str]]
    notes: list[str]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _key(text: str) -> frozenset[str]:
    return frozenset(content_terms(words(text)))


def outline(pages: list[PageContent]) -> list[Section]:
    """Group similar H2s across pages; keep topics at least two pages cover."""
    groups: list[tuple[frozenset[str], list[tuple[int, float, str]]]] = []
    for page_index, page in enumerate(pages):
        h2 = [t for level, t in page.headings if level == 2]  # noqa: PLR2004
        for position, heading in enumerate(h2):
            key = _key(heading)
            if not key:
                continue
            relative = position / max(1, len(h2) - 1)
            for group_key, members in groups:
                if len(key & group_key) / len(key | group_key) >= SIMILAR:
                    members.append((page_index, relative, heading))
                    break
            else:
                groups.append((key, [(page_index, relative, heading)]))
    sections = []
    for _, members in groups:
        distinct = {m[0] for m in members}
        if len(distinct) < 2:  # noqa: PLR2004
            continue
        order = statistics.mean(m[1] for m in members)
        variants = list(dict.fromkeys(m[2] for m in members))
        sections.append((order, Section(min(variants, key=len), len(distinct), variants[:4])))
    top = sorted(sections, key=lambda s: -s[1].pages)[:MAX_SECTIONS]
    return [s for _, s in sorted(top, key=lambda s: s[0])]


def _range(pages: list[PageContent]) -> tuple[int, int] | None:
    counts = sorted(p.word_count for p in pages if p.word_count)
    if len(counts) < 3:  # noqa: PLR2004
        return None
    quartiles = statistics.quantiles(counts, n=4)
    return (int(round(quartiles[0], -1)), int(round(quartiles[2], -1)))


def build_brief(
    keyword: str,
    serp: SerpSnapshotData | None,
    pages: list[PageContent],
    *,
    intent: str,
    intent_reasons: list[str],
    competitors: list[dict[str, Any]],
    internal_links: list[dict[str, str]],
) -> Brief:
    notes: list[str] = []
    if serp is None:
        notes.append("No live SERP was available, so SERP features and questions are missing.")
    if len(pages) < 3:  # noqa: PLR2004
        notes.append(
            f"Only {len(pages)} ranking page(s) could be read; "
            "the outline and length are indicative."
        )
    questions = list(serp.people_also_ask) if serp else []
    for page in pages:
        for _, heading in page.headings:
            if heading.endswith("?") and heading not in questions:
                questions.append(heading)
    related = list(serp.related_searches) if serp else []
    schema = dominant_schema(pages) or INTENT_SCHEMA.get(intent, "Article")
    ai = None
    if serp and serp.ai_answer:
        ai = {"kind": serp.ai_answer.kind, "cited_domains": serp.ai_answer.cited_domains[:10]}
        notes.append(
            "An AI answer appears for this query; clear, well-sourced answers to the "
            "questions below help earn citations."
        )
    return Brief(
        keyword=keyword,
        intent=intent,
        intent_reasons=intent_reasons,
        word_count_range=_range(pages),
        outline=outline(pages),
        questions=questions[:15],
        terms=[t for t, _, _ in important_terms(pages, keyword)] if len(pages) >= 2 else [],  # noqa: PLR2004
        secondary_keywords=related[:10],
        schema_type=schema,
        serp_features=list(serp.features) if serp else [],
        ai_answer=ai,
        competitors=competitors,
        internal_links=internal_links[:10],
        notes=notes,
    )


def _md_escape(text: str) -> str:
    """Neutralise Markdown/HTML control characters in third-party text."""
    out = text.replace("\\", "\\\\")
    for char in "`*_[]<>#|":
        out = out.replace(char, f"\\{char}")
    return " ".join(out.split())


def to_markdown(data: dict[str, Any]) -> str:
    """Render a stored brief (``Brief.to_json()``) as Markdown for writers."""
    e = _md_escape
    lines = [f"# Content brief: {e(data['keyword'])}", ""]
    lines.append(f"**Search intent:** {data['intent']}")
    if data.get("word_count_range"):
        low, high = data["word_count_range"]
        lines.append(f"**Suggested length:** {low:,}-{high:,} words (ranking pages' middle half)")
    lines.append(f"**Structured data:** {e(data['schema_type'])}")
    if data.get("serp_features"):
        lines.append("**SERP features:** " + ", ".join(e(f) for f in data["serp_features"]))
    lines.append("")
    if data.get("outline"):
        lines += ["## Suggested outline", ""]
        lines += [
            f"- {e(s['heading'])} _(covered by {s['pages']} ranking pages)_"
            for s in data["outline"]
        ]
        lines.append("")
    for title, key in (
        ("Questions to answer", "questions"),
        ("Terms to cover", "terms"),
        ("Secondary keywords", "secondary_keywords"),
    ):
        if data.get(key):
            lines += [f"## {title}", ""] + [f"- {e(item)}" for item in data[key]] + [""]
    if data.get("internal_links"):
        lines += ["## Link from these pages", ""]
        lines += [
            f"- {e(link.get('title') or link['url'])}: <{link['url']}>"
            for link in data["internal_links"]
        ]
        lines.append("")
    if data.get("competitors"):
        lines += ["## Ranking pages analysed", ""]
        for c in data["competitors"]:
            status = (
                f"{c['word_count']:,} words"
                if c.get("word_count")
                else f"not read ({c.get('skipped', 'n/a')})"
            )
            lines.append(f"{c['position']}. {e(c['domain'])}: {status}")
        lines.append("")
    if data.get("notes"):
        lines += ["## Notes", ""] + [f"- {e(n)}" for n in data["notes"]] + [""]
    return "\n".join(lines)
