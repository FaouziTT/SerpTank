"""Pure on-page logic: text stats, the analyzer, briefs and Markdown export."""

from __future__ import annotations

from datetime import date

from serptank.modules.onpage.analyzer import analyze, dominant_schema, important_terms
from serptank.modules.onpage.brief import build_brief, outline, to_markdown
from serptank.modules.onpage.text import (
    PageContent,
    contains_phrase,
    extract_content,
    flesch_reading_ease,
    term_counts,
    term_coverage,
    words,
)
from serptank.modules.search_data.schema import AiAnswer, OrganicResult, SerpSnapshotData
from tests.onpage.site import KEYWORD, OWN_HTML, competitor_html

TODAY = date(2026, 9, 24)


def competitors(n: int = 3) -> list[PageContent]:
    return [extract_content(competitor_html(i), f"https://c{i}.example/") for i in range(n)]


def test_text_helpers() -> None:
    assert words("Don't e-mail 42 Trail-Running!") == ["don't", "e-mail", "trail-running"]
    counts = term_counts("The trail running shoes and trail running shoes")
    assert counts["trail running"] == 2
    assert counts["the"] == 0  # stop word
    assert contains_phrase("Best Trail  Running shoes 2026", "trail running shoes")
    assert not contains_phrase("running trail shoes", "trail running shoes")
    assert not contains_phrase(None, "x")
    assert term_coverage("trail shoes", KEYWORD) == 2 / 3
    assert flesch_reading_ease("Short text.", "en") is None
    easy = "The cat sat on the mat. " * 30
    score = flesch_reading_ease(easy, "en-GB")
    assert score is not None
    assert score > 80
    assert flesch_reading_ease(easy, "de") is None  # English only, honestly


def test_extract_content() -> None:
    page = extract_content(competitor_html(0), "https://c.example/")
    assert page.title == "Best Trail Running Shoes 2026 | Reviews"
    assert page.h1 == ["The best trail running shoes"]
    assert page.headings[0] == (2, "How to choose trail running shoes")
    assert page.schema_types == ["Article"]
    assert page.modified == "2026-09-01"
    assert page.word_count > 100
    summary = page.summary()
    assert "text" not in summary  # never stored


def test_analyzer_scores_and_explains() -> None:
    own = extract_content(OWN_HTML, "https://www.example-shop.com/trail")
    result = analyze(own, KEYWORD, competitors(), intent="commercial", today=TODAY, inlinks=0)
    by_id = {c.id: c for c in result.checks}
    assert by_id["title_keyword"].status == "fail"
    assert by_id["meta_description"].status == "warn"
    assert by_id["h1_keyword"].status == "fail"
    assert by_id["content_length"].status == "fail"
    assert by_id["topic_coverage"].status in {"fail", "warn"}
    assert "cushioning" in by_id["topic_coverage"].detail["missing"]
    assert by_id["page_type"].status == "warn"
    assert by_id["structured_data"].detail["suggested_type"] == "Article"
    assert by_id["internal_links"].status == "fail"
    assert by_id["freshness"].status == "info"
    assert result.checks[0].status == "fail"  # failures first
    assert 0 <= result.score < 40
    assert result.benchmarks["competitors_analyzed"] == 3

    good = competitors(4)[3]
    better = analyze(good, KEYWORD, competitors(), intent="commercial", today=TODAY, inlinks=5)
    assert better.score > 80
    assert better.score > result.score


def test_analyzer_without_competitors_is_honest() -> None:
    own = extract_content(OWN_HTML, "https://www.example-shop.com/trail")
    result = analyze(own, KEYWORD, [], today=TODAY)
    info = {c.id for c in result.checks if c.status == "info"}
    assert {"content_length", "topic_coverage", "page_type", "internal_links"} <= info
    assert result.term_gaps == []


def test_terms_and_schema() -> None:
    pages = competitors()
    terms = [t for t, _, _ in important_terms(pages, KEYWORD)]
    assert "cushioning" in terms
    assert "trail running" not in terms  # the keyword itself is excluded
    assert dominant_schema(pages) == "Article"
    assert dominant_schema([]) is None


def _serp() -> SerpSnapshotData:
    return SerpSnapshotData(
        engine="google",
        query=KEYWORD,
        country="US",
        language="en",
        device="desktop",
        location=None,
        organic=[OrganicResult(1, "https://c0.example/", "c0.example")],
        features=["people_also_ask", "ai_overview"],
        ai_answer=AiAnswer("ai_overview", cited_domains=["c0.example"]),
        people_also_ask=["Are trail shoes worth it?"],
        related_searches=["trail shoes women"],
    )


def test_brief_and_markdown() -> None:
    pages = competitors()
    sections = outline(pages)
    assert [s.heading for s in sections][:2] == [
        "How to choose trail running shoes",
        "Cushioning and stack height",
    ]
    assert all(s.pages == 3 for s in sections)
    brief = build_brief(
        KEYWORD,
        _serp(),
        pages,
        intent="commercial",
        intent_reasons=["modifier"],
        competitors=[{"position": 1, "domain": "c0.example", "word_count": 300}],
        internal_links=[{"url": "https://www.example-shop.com/trail", "title": "Trail"}],
    )
    assert brief.word_count_range is not None
    assert brief.schema_type == "Article"
    assert "Are trail shoes worth it?" in brief.questions
    assert "Waterproof or breathable?" in brief.questions
    assert brief.ai_answer == {"kind": "ai_overview", "cited_domains": ["c0.example"]}
    md = to_markdown(brief.to_json())
    assert md.startswith("# Content brief: trail running shoes")
    assert "## Suggested outline" in md
    assert "trail shoes women" in md


def test_markdown_neutralises_third_party_text() -> None:
    brief = build_brief(
        "x", None, [], intent="unknown", intent_reasons=[], competitors=[], internal_links=[]
    ).to_json()
    brief["questions"] = ["<script>alert(1)</script> [click](javascript:alert(1))"]
    md = to_markdown(brief)
    assert "<script>" not in md
    assert "[click]" not in md
    assert any("No live SERP" in n for n in brief["notes"])
