"""Parser for Google web results HTML (as returned by raw-HTML unblocker vendors)."""

from __future__ import annotations

from selectolax.lexbor import LexborHTMLParser, LexborNode

from serptank.modules.search_data.parsers.common import (
    SerpParseError,
    clean_href,
    domain_of,
    heading_texts,
    text,
)
from serptank.modules.search_data.schema import (
    AiAnswer,
    OrganicResult,
    SerpRequest,
    SerpSnapshotData,
)

AD_CONTAINERS = ("#tads", "#bottomads", "#tadsb", '[aria-label="Ads"]')
SECTION_FEATURES = {
    "people also ask": "people_also_ask",
    "top stories": "top_stories",
    "videos": "video",
    "images": "images",
    "places": "local_pack",
    "businesses": "local_pack",
    "popular products": "shopping",
    "related searches": "related_searches",
    "people also search for": "related_searches",
}
AI_HEADINGS = ("ai overview",)
NO_RESULTS = ("did not match any documents", "no results found for")
SNIPPET = "[data-sncf], .VwiC3b, [style*='-webkit-line-clamp']"


def _section(node: LexborNode, levels: int = 6) -> LexborNode:
    """Climb from a heading to the block that contains its section."""
    current = node
    for _ in range(levels):
        parent = current.parent
        if parent is None or parent.tag in {"body", "html"}:
            break
        current = parent
        if len(current.css("a[href]")) >= 2:  # noqa: PLR2004
            break
    return current


def _ai_answer(tree: LexborHTMLParser, root: LexborNode) -> AiAnswer | None:
    """AI Overview: a heading "AI Overview" and the links (its sources) in that block."""
    for label, node in heading_texts(tree.body or root):
        if any(label.startswith(h) for h in AI_HEADINGS):
            block = _section(node, 8)
            urls = [
                u for a in block.css("a[href]") if (u := clean_href(a.attributes.get("href") or ""))
            ]
            answer = AiAnswer(
                kind="ai_overview",
                cited_urls=list(dict.fromkeys(urls))[:50],
                cited_domains=sorted({domain_of(u) for u in urls}),
                text=text(block, 4000),
            )
            block.decompose()  # its links are citations, not organic results
            return answer
    return None


def _sections(tree: LexborHTMLParser, root: LexborNode, snapshot: SerpSnapshotData) -> set[str]:
    features: set[str] = set()
    for label, node in heading_texts(root):
        for prefix, feature in SECTION_FEATURES.items():
            if not label.startswith(prefix):
                continue
            features.add(feature)
            block = _section(node, 4)
            if feature == "people_also_ask":
                questions = [text(q, 200) for q in block.css('[role="button"], [aria-expanded]')]
                snapshot.people_also_ask = [q for q in dict.fromkeys(questions) if q.endswith("?")][
                    :20
                ]
            elif feature == "related_searches":
                snapshot.related_searches = [t for a in block.css("a") if (t := text(a, 100))][:20]
    if tree.css_first('[data-attrid="wa:/description"], .kp-wholepage, #rhs .kp-blk'):
        features.add("knowledge_panel")
    if tree.css_first(".xpdopen, .ifM9O, [data-tts='answers']"):
        features.add("featured_snippet")
    return features


def _organic(root: LexborNode) -> list[OrganicResult]:
    results: list[OrganicResult] = []
    seen: set[str] = set()
    for title_node in root.css("a[href] h3"):
        anchor = title_node.parent
        while anchor is not None and anchor.tag != "a":
            anchor = anchor.parent
        if anchor is None:
            continue
        url = clean_href(anchor.attributes.get("href") or "")
        if (
            not url
            or url in seen
            or domain_of(url).endswith(("google.com", "googleusercontent.com"))
        ):
            continue
        seen.add(url)
        container = anchor
        for _ in range(6):
            if container.parent is None or container.parent.tag == "body":
                break
            container = container.parent
            if container.css_first(SNIPPET):
                break
        results.append(
            OrganicResult(
                position=len(results) + 1,
                url=url,
                domain=domain_of(url),
                title=text(title_node, 300),
                snippet=text(container.css_first(SNIPPET), 500),
            )
        )
    return results


def parse_google(html: str, request: SerpRequest) -> SerpSnapshotData:
    tree = LexborHTMLParser(html)
    root = tree.css_first("#search") or tree.css_first("#rso") or tree.body
    if root is None:
        raise SerpParseError("no body")
    for selector in AD_CONTAINERS:
        for ad in tree.css(selector):
            ad.decompose()
    snapshot = SerpSnapshotData(
        engine=request.engine,
        query=request.query,
        country=request.country,
        language=request.language,
        device=request.device,
        location=request.location,
    )
    snapshot.ai_answer = _ai_answer(tree, root)
    features = _sections(tree, root, snapshot)
    if snapshot.ai_answer is not None:
        features.add("ai_overview")
    snapshot.organic = _organic(root)
    if not snapshot.organic:
        page_text = text(tree.body, 5000).lower()
        if not any(marker in page_text for marker in NO_RESULTS):
            raise SerpParseError("no organic results found in Google HTML")
    snapshot.features = sorted(features)
    return snapshot
