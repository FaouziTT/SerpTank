"""SERP-based page analysis: compare one page with what ranks for a keyword.

Pure and deterministic (no I/O): the service fetches pages and the SERP, this module
turns them into explainable checks. Every check says what we looked at, why it matters
and what to do; checks without enough evidence are ``info`` and don't move the score.
The score is the weighted share of passed checks (warn counts half), 0-100.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Literal

from serptank.modules.onpage.text import (
    PageContent,
    contains_phrase,
    content_terms,
    flesch_reading_ease,
    term_counts,
    term_coverage,
    words,
)

Status = Literal["pass", "warn", "fail", "info"]
# Score contribution per status (built from tuples: a literal "pass" key trips bandit B105).
VALUE: dict[str, float] = dict(zip(("pass", "warn", "fail"), (1.0, 0.5, 0.0), strict=True))
SEVERITY_ORDER = ("fail", "warn", "info", "pass")
MIN_COMPETITORS = 3  # below this, benchmarks are too noisy to judge against
TERMS_PER_PAGE = 60
MAX_GAP_TERMS = 30
STALE_DAYS = 365
TITLE_CHARS = (30, 60)
FULL = 0.99  # "all keyword words present" with float tolerance
GOOD_RATIO = 0.7

# Page types we can recognise from schema.org types, and what an intent usually wants.
PAGE_TYPES = {
    "Product": "product",
    "Offer": "product",
    "AggregateOffer": "product",
    "Article": "article",
    "NewsArticle": "article",
    "BlogPosting": "article",
    "HowTo": "article",
    "Recipe": "recipe",
    "ItemList": "list",
    "CollectionPage": "list",
    "LocalBusiness": "local",
    "Store": "local",
    "Restaurant": "local",
    "SoftwareApplication": "product",
    "Course": "course",
    "Event": "event",
    "VideoObject": "video",
}
INTENT_SCHEMA = {
    "transactional": "Product",
    "commercial": "Article",
    "informational": "Article",
    "local": "LocalBusiness",
    "navigational": "Organization",
}


@dataclass
class Check:
    id: str
    status: Status
    weight: int
    message: str
    recommendation: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class TermGap:
    term: str
    competitors_using: int
    median_uses: float
    your_uses: int


@dataclass
class Analysis:
    score: int
    checks: list[Check]
    term_gaps: list[TermGap]
    benchmarks: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def important_terms(pages: list[PageContent], keyword: str) -> list[tuple[str, int, float]]:
    """Terms most competitors use: (term, pages using it, median uses among them)."""
    exclude = set(content_terms(words(keyword))) | {" ".join(words(keyword))}
    df: Counter[str] = Counter()
    uses: dict[str, list[int]] = {}
    for page in pages:
        counts = term_counts(page.text)
        for term, count in counts.most_common(TERMS_PER_PAGE):
            if term in exclude:
                continue
            df[term] += 1
            uses.setdefault(term, []).append(count)
    need = max(2, math.ceil(0.4 * len(pages)))
    ranked = sorted(
        ((t, n, statistics.median(uses[t])) for t, n in df.items() if n >= need),
        key=lambda row: (-row[1], -row[2], row[0]),
    )
    return ranked[:MAX_GAP_TERMS]


def dominant_schema(pages: list[PageContent]) -> str | None:
    """A schema.org type used by at least half of the competitor pages."""
    counts: Counter[str] = Counter(t for p in pages for t in set(p.schema_types) if t in PAGE_TYPES)
    if not counts or not pages:
        return None
    kind, n = counts.most_common(1)[0]
    return kind if n * 2 >= len(pages) else None


def _grade(value: float, good: float, ok: float) -> Status:
    return "pass" if value >= good else "warn" if value >= ok else "fail"


class _Checks:
    def __init__(self, page: PageContent, keyword: str, competitors: list[PageContent]) -> None:
        self.page = page
        self.keyword = keyword
        self.competitors = competitors
        self.items: list[Check] = []
        self.enough = len(competitors) >= MIN_COMPETITORS

    def add(self, *args: Any, **kwargs: Any) -> None:
        self.items.append(Check(*args, **kwargs))

    def title(self) -> None:
        title = self.page.title or ""
        if not title:
            self.add(
                "title_keyword",
                "fail",
                12,
                "The page has no <title>.",
                "Add a unique, descriptive title that leads with the keyword.",
            )
        elif contains_phrase(title, self.keyword):
            self.add("title_keyword", "pass", 12, "The title contains the keyword.")
        else:
            cov = term_coverage(title, self.keyword)
            self.add(
                "title_keyword",
                _grade(cov, 1.1, 0.5),
                12,
                f"The title covers {round(cov * 100)}% of the keyword's words.",
                "Work the exact keyword into the title, ideally near the start.",
                {"title": title},
            )
        length = len(title)
        self.add(
            "title_length",
            "pass" if TITLE_CHARS[0] <= length <= TITLE_CHARS[1] else "warn",
            4,
            f"The title is {length} characters.",
            ""
            if TITLE_CHARS[0] <= length <= TITLE_CHARS[1]
            else "Aim for roughly 30-60 characters so Google shows it in full.",
        )

    def meta(self) -> None:
        meta = self.page.meta_description or ""
        if not meta:
            self.add(
                "meta_description",
                "warn",
                5,
                "No meta description.",
                "Write a 70-160 character summary that includes the keyword; "
                "Google often shows it as the snippet.",
            )
            return
        cov = 1.0 if contains_phrase(meta, self.keyword) else term_coverage(meta, self.keyword)
        length_ok = 70 <= len(meta) <= 160  # noqa: PLR2004
        status: Status = "pass" if cov >= 1 and length_ok else "warn"
        self.add(
            "meta_description",
            status,
            5,
            f"Meta description: {len(meta)} characters, covers {round(cov * 100)}% of the keyword.",
            "" if status == "pass" else "Keep it 70-160 characters and mention the keyword.",
        )

    def headings(self) -> None:
        h1 = self.page.h1
        if not h1:
            self.add(
                "h1_keyword",
                "fail",
                8,
                "The page has no H1.",
                "Add one H1 that states the topic using the keyword.",
            )
        else:
            cov = max(term_coverage(h, self.keyword) for h in h1)
            status = _grade(cov, 0.99, 0.5)
            self.add(
                "h1_keyword",
                status if len(h1) == 1 else "warn",
                8,
                f"{len(h1)} H1 heading(s); best keyword coverage {round(cov * 100)}%.",
                ""
                if status == "pass" and len(h1) == 1
                else "Use a single H1 that contains the keyword.",
            )
        sub = " ".join(t for _, t in self.page.headings)
        cov = term_coverage(sub, self.keyword)
        self.add(
            "subheadings",
            _grade(cov, FULL, 0.5) if self.page.headings else "warn",
            5,
            f"{len(self.page.headings)} H2/H3 headings; "
            f"they cover {round(cov * 100)}% of the keyword's words.",
            ""
            if cov >= FULL
            else "Use H2/H3 headings to structure the page around the topic and its sub-questions.",
        )

    def body(self) -> None:
        first = " ".join(words(self.page.text)[:100])
        early = contains_phrase(first, self.keyword)
        self.add(
            "keyword_early",
            "pass" if early else "warn",
            4,
            "The keyword appears in the first 100 words."
            if early
            else "The keyword does not appear in the first 100 words.",
            "" if early else "Mention the topic plainly in the opening paragraph.",
        )

    def length(self, benchmarks: dict[str, Any]) -> None:
        counts = [c.word_count for c in self.competitors if c.word_count]
        if not self.enough or len(counts) < MIN_COMPETITORS:
            self.add(
                "content_length",
                "info",
                10,
                "Not enough ranking pages could be read to benchmark length.",
            )
            return
        median = statistics.median(counts)
        benchmarks["median_word_count"] = round(median)
        ratio = self.page.word_count / median if median else 1.0
        self.add(
            "content_length",
            _grade(ratio, 0.7, 0.4),
            10,
            f"{self.page.word_count:,} words vs a median of {round(median):,} on ranking pages.",
            ""
            if ratio >= GOOD_RATIO
            else "Ranking pages cover the topic in more depth; expand the sections that "
            "matter to searchers (length itself is not a ranking factor).",
        )

    def terms(self) -> list[TermGap]:
        if not self.enough:
            self.add(
                "topic_coverage",
                "info",
                15,
                "Not enough ranking pages could be read to compare topics.",
            )
            return []
        ours = term_counts(self.page.text)
        wanted = important_terms(self.competitors, self.keyword)
        if not wanted:
            self.add("topic_coverage", "info", 15, "Ranking pages share no common subtopics.")
            return []
        gaps = [TermGap(t, n, m, ours.get(t, 0)) for t, n, m in wanted]
        covered = sum(1 for g in gaps if g.your_uses) / len(gaps)
        missing = [g.term for g in gaps if not g.your_uses]
        self.add(
            "topic_coverage",
            _grade(covered, 0.7, 0.4),
            15,
            f"The page mentions {round(covered * 100)}% of the subtopics most ranking pages cover.",
            "" if not missing else "Consider covering: " + ", ".join(missing[:8]) + ".",
            {"missing": missing},
        )
        return gaps

    def page_type(self, intent: str) -> None:
        dominant = dominant_schema(self.competitors) if self.enough else None
        ours = {PAGE_TYPES[t] for t in self.page.schema_types if t in PAGE_TYPES}
        if dominant is None:
            self.add(
                "page_type",
                "info",
                8,
                "Ranking pages don't share one page type.",
                detail={"intent": intent},
            )
            return
        wanted = PAGE_TYPES[dominant]
        match = wanted in ours
        self.add(
            "page_type",
            "pass" if match else "warn",
            8,
            f"Most ranking pages are {wanted} pages ({dominant})"
            + ("; so is this one." if match else "; this page doesn't look like one."),
            ""
            if match
            else "Check the page format matches what searchers want "
            f"(a {wanted} page for “{self.keyword}”).",
            {"intent": intent, "dominant_schema": dominant},
        )

    def structured_data(self, intent: str) -> None:
        if self.page.schema_types:
            self.add(
                "structured_data",
                "pass",
                6,
                "Structured data: " + ", ".join(self.page.schema_types[:5]) + ".",
            )
            return
        suggestion = (
            dominant_schema(self.competitors) if self.enough else None
        ) or INTENT_SCHEMA.get(intent, "Article")
        self.add(
            "structured_data",
            "warn",
            6,
            "No schema.org structured data found.",
            f"Add {suggestion} markup (JSON-LD) that matches visible content; "
            "validate it with Google's Rich Results Test.",
            {"suggested_type": suggestion},
        )

    def readability(self, language: str) -> None:
        score = flesch_reading_ease(self.page.text, language)
        if score is None:
            self.add(
                "readability",
                "info",
                4,
                "Readability is only scored for English pages with 100+ words.",
            )
            return
        self.add(
            "readability",
            _grade(score, 50, 30),
            4,
            f"Flesch reading ease {score} (higher is easier).",
            "" if score >= 50 else "Shorten sentences and prefer plain words.",  # noqa: PLR2004
            {"flesch": score},
        )

    def freshness(self, today: date) -> None:
        if not self.page.modified:
            self.add(
                "freshness",
                "info",
                4,
                "No published/modified date found in structured data or meta tags.",
                "If the content is time-sensitive, show and mark up a dateModified.",
            )
            return
        try:
            age = (today - date.fromisoformat(self.page.modified)).days
        except ValueError:
            self.add("freshness", "info", 4, "The page's date could not be read.")
            return
        self.add(
            "freshness",
            "pass" if age <= STALE_DAYS else "warn",
            4,
            f"Last updated {age} days ago.",
            ""
            if age <= STALE_DAYS
            else "Review the facts and update the page if anything changed.",
        )

    def images(self) -> None:
        if not self.page.images:
            self.add("image_alt", "info", 3, "The page has no images.")
            return
        missing = self.page.images_missing_alt
        self.add(
            "image_alt",
            "pass" if missing == 0 else "warn",
            3,
            f"{missing} of {self.page.images} images have no alt text.",
            "" if missing == 0 else "Describe meaningful images with alt text.",
        )

    def internal_links(self, inlinks: int | None, suggestions: list[dict[str, str]]) -> None:
        if inlinks is None:
            self.add(
                "internal_links", "info", 6, "Run a crawl to check internal links to this page."
            )
            return
        status: Status = "pass" if inlinks >= 3 else "warn" if inlinks else "fail"  # noqa: PLR2004
        self.add(
            "internal_links",
            status,
            6,
            f"{inlinks} internal page(s) link here.",
            "" if status == "pass" else "Link to this page from related pages (suggestions below).",
            {"suggestions": suggestions[:10]},
        )


def analyze(
    page: PageContent,
    keyword: str,
    competitors: list[PageContent],
    *,
    intent: str = "unknown",
    language: str = "en",
    today: date,
    inlinks: int | None = None,
    link_suggestions: list[dict[str, str]] | None = None,
) -> Analysis:
    checks = _Checks(page, keyword, competitors)
    benchmarks: dict[str, Any] = {
        "competitors_analyzed": len(competitors),
        "word_count": page.word_count,
    }
    checks.title()
    checks.meta()
    checks.headings()
    checks.body()
    checks.length(benchmarks)
    gaps = checks.terms()
    checks.page_type(intent)
    checks.structured_data(intent)
    checks.readability(language)
    checks.freshness(today)
    checks.images()
    checks.internal_links(inlinks, link_suggestions or [])
    scored = [c for c in checks.items if c.status != "info"]
    total = sum(c.weight for c in scored)
    score = round(100 * sum(c.weight * VALUE[c.status] for c in scored) / total) if total else 0
    ordered = sorted(checks.items, key=lambda c: (SEVERITY_ORDER.index(c.status), -c.weight))
    return Analysis(score=score, checks=ordered, term_gaps=gaps, benchmarks=benchmarks)
