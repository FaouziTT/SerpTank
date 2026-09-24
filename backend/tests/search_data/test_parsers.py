"""SERP parsers and vendor mapping against a saved corpus (tests/search_data/corpus).

The corpus is versioned: when an engine changes its layout, add the new page here and
make the parser pass both. A 200 page that yields nothing must raise, never store empties.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.adapters.dataforseo import parse_response
from serptank.modules.search_data.adapters.rawhtml import serp_url
from serptank.modules.search_data.parsers.bing import parse_bing
from serptank.modules.search_data.parsers.common import SerpParseError, clean_href
from serptank.modules.search_data.parsers.duckduckgo import parse_duckduckgo
from serptank.modules.search_data.parsers.google import parse_google
from serptank.modules.search_data.schema import SerpRequest, SerpSnapshotData, normalize_query

CORPUS = Path(__file__).parent / "corpus"
OWN = frozenset({"example-shop.com", "www.example-shop.com"})


def req(engine: str = "google") -> SerpRequest:
    return SerpRequest(engine=engine, query="best running shoes", country="US", language="en")


def test_google_parser_extracts_organic_ai_answer_and_features() -> None:
    snap = parse_google((CORPUS / "google_ai_overview.html").read_text(), req())
    assert [r.domain for r in snap.organic] == [
        "www.runnersworld.com",
        "www.example-shop.com",
        "shoe-lab.example",
    ]
    assert (
        snap.organic[0].url == "https://www.runnersworld.com/gear/a1/best-running-shoes/"
    )  # /url?q= unwrapped
    assert snap.organic[0].snippet == "We tested hundreds of pairs."
    assert snap.organic[1].snippet == "Free shipping on running shoes."
    assert all("ads" not in r.domain for r in snap.organic)  # ads removed
    assert snap.ai_answer is not None
    assert snap.ai_answer.cited_domains == ["shoe-lab.example", "www.runnersworld.com"]
    assert set(snap.features) == {"ai_overview", "people_also_ask", "related_searches"}
    assert snap.people_also_ask == [
        "What is the most comfortable running shoe?",
        "Which brand is best for running?",
    ]
    assert snap.position_of(OWN).position == 2  # type: ignore[union-attr]
    assert not snap.cites(OWN)


def test_google_parser_handles_empty_and_blocked_pages() -> None:
    empty = parse_google((CORPUS / "google_no_results.html").read_text(), req())
    assert empty.organic == []
    with pytest.raises(SerpParseError):
        parse_google((CORPUS / "google_captcha.html").read_text(), req())


def test_bing_and_duckduckgo_parsers() -> None:
    bing = parse_bing((CORPUS / "bing.html").read_text(), req("bing"))
    assert [r.domain for r in bing.organic] == ["www.example-shop.com", "www.runnersworld.com"]
    assert {"sitelinks", "people_also_ask"} <= set(bing.features)
    ddg = parse_duckduckgo((CORPUS / "duckduckgo.html").read_text(), req("duckduckgo"))
    assert [r.url for r in ddg.organic] == [
        "https://www.example-shop.com/running",
        "https://www.runnersworld.com/gear/",
    ]
    with pytest.raises(SerpParseError):
        parse_bing("<html><body>blocked</body></html>", req("bing"))


def test_dataforseo_mapping() -> None:
    payload = json.loads((CORPUS / "dataforseo_google.json").read_text())
    snap = parse_response(payload, req())
    assert [(r.position, r.domain, r.absolute) for r in snap.organic] == [
        (1, "www.runnersworld.com", 3),
        (2, "www.example-shop.com", 5),
    ]
    assert snap.cites(OWN)  # the AI Overview cites the shop's guide
    assert snap.people_also_ask == ["What is the best running shoe?", "Is Nike good?"]
    assert snap.related_searches == ["best trail shoes", "running shoes men"]
    assert set(snap.features) == {
        "ai_overview",
        "people_also_ask",
        "shopping",
        "related_searches",
        "sitelinks",
        "other:brand_new_widget",
    }
    assert snap.total_results == 412000000
    # Round-trips through JSON storage.
    assert SerpSnapshotData.from_json(snap.to_json()) == snap


@pytest.mark.parametrize(
    ("payload", "retryable"),
    [
        ({"status_code": 40100}, True),
        ({"status_code": 20000, "tasks": [{"status_code": 40501}]}, False),
        ({"status_code": 20000, "tasks": [{"status_code": 20000, "result": []}]}, True),
    ],
)
def test_dataforseo_errors(payload: dict[str, object], retryable: bool) -> None:
    with pytest.raises(CollectorError) as exc:
        parse_response(payload, req())
    assert exc.value.retryable is retryable


def test_helpers() -> None:
    assert normalize_query("  Best   RUNNING shoes ") == "best running shoes"
    assert clean_href("/url?q=https://a.com/x&sa=U") == "https://a.com/x"
    assert clean_href("javascript:void(0)") is None
    assert serp_url(req()).startswith(
        "https://www.google.com/search?q=best+running+shoes&hl=en&gl=us"
    )
    assert "cc=US" in serp_url(req("bing"))
    with pytest.raises(CollectorError):
        serp_url(req("baidu"))
