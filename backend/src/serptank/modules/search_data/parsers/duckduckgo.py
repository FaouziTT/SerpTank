"""Parser for DuckDuckGo's HTML endpoint (html.duckduckgo.com/html/)."""

from __future__ import annotations

from selectolax.lexbor import LexborHTMLParser

from serptank.modules.search_data.parsers.common import SerpParseError, clean_href, domain_of, text
from serptank.modules.search_data.schema import OrganicResult, SerpRequest, SerpSnapshotData


def parse_duckduckgo(html: str, request: SerpRequest) -> SerpSnapshotData:
    tree = LexborHTMLParser(html)
    snapshot = SerpSnapshotData(
        engine=request.engine,
        query=request.query,
        country=request.country,
        language=request.language,
        device=request.device,
        location=request.location,
    )
    for item in tree.css("div.result"):
        classes = item.attributes.get("class") or ""
        if "result--ad" in classes:
            continue
        link = item.css_first("a.result__a[href]")
        url = clean_href(link.attributes.get("href") or "") if link else None
        if not url:
            continue
        snapshot.organic.append(
            OrganicResult(
                position=len(snapshot.organic) + 1,
                url=url,
                domain=domain_of(url),
                title=text(link, 300),
                snippet=text(item.css_first(".result__snippet"), 500),
            )
        )
    if not snapshot.organic and "no results" not in text(tree.body, 2000).lower():
        raise SerpParseError("no organic results found in DuckDuckGo HTML")
    return snapshot
