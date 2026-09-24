"""Parser for Bing web results HTML."""

from __future__ import annotations

from selectolax.lexbor import LexborHTMLParser

from serptank.modules.search_data.parsers.common import SerpParseError, clean_href, domain_of, text
from serptank.modules.search_data.schema import OrganicResult, SerpRequest, SerpSnapshotData


def parse_bing(html: str, request: SerpRequest) -> SerpSnapshotData:
    tree = LexborHTMLParser(html)
    snapshot = SerpSnapshotData(
        engine=request.engine,
        query=request.query,
        country=request.country,
        language=request.language,
        device=request.device,
        location=request.location,
    )
    features: set[str] = set()
    for item in tree.css("#b_results > li.b_algo, li.b_algo"):
        link = item.css_first("h2 a[href]")
        url = clean_href(link.attributes.get("href") or "") if link else None
        if not url or any(r.url == url for r in snapshot.organic):
            continue
        snapshot.organic.append(
            OrganicResult(
                position=len(snapshot.organic) + 1,
                url=url,
                domain=domain_of(url),
                title=text(link, 300),
                snippet=text(item.css_first(".b_caption p, .b_lineclamp2, .b_algoSlug"), 500),
            )
        )
        if item.css_first(".b_deep, .b_vlist2col"):
            features.add("sitelinks")
    if tree.css_first("#relatedQnAListDisplay, .df_alsoAskCard"):
        features.add("people_also_ask")
        snapshot.people_also_ask = [text(q, 200) for q in tree.css(".df_qntext, .b_1linetrunc")][
            :20
        ]
    if tree.css_first(".b_ans .b_rs, #b_context .b_rs"):
        features.add("related_searches")
        snapshot.related_searches = [text(a, 100) for a in tree.css(".b_rs a")][:20]
    if tree.css_first("#b_context .b_entityTP"):
        features.add("knowledge_panel")
    if tree.css_first(".b_ans .b_focusTextLarge, .b_ans .df_crd"):
        features.add("featured_snippet")
    if tree.css_first("#b_results .b_ans .vsathm, .b_ans #mc_vtvc"):
        features.add("video")
    if tree.css_first("#lMapContainer, .b_localBox, .b_lclc"):
        features.add("local_pack")
    if not snapshot.organic and "there are no results for" not in text(tree.body, 3000).lower():
        raise SerpParseError("no organic results found in Bing HTML")
    snapshot.features = sorted(features)
    return snapshot
