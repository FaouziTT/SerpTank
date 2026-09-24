"""Page content extraction and text statistics for on-page analysis.

Deliberately small and dependency-free: a tokenizer, stop words (English plus the
most common function words of our main European markets), n-gram term counts and a
Flesch reading-ease score. Scores are only computed for English; other languages get
``None`` (honest "not available") instead of a misleading number.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from selectolax.lexbor import LexborHTMLParser

from serptank.modules.crawler.parser import parse_html
from serptank.modules.crawler.urls import is_internal

# Letters, allowing inner apostrophes (ASCII or U+2019) and hyphens: "don't", "e-mail".
WORD = re.compile(r"[^\W\d_](?:[^\W_]|['\u2019-][^\W\d_])*", re.UNICODE)
MAX_TEXT_CHARS = 200_000
MAX_HEADINGS = 80

_STOPWORD_TEXT = """
a about above after again against all am an and any are as at be because been before
being below between both but by can could did do does doing down during each few for
from further had has have having he her here hers herself him himself his how i if in
into is it its itself just me more most my myself no nor not now of off on once only or
other our ours ourselves out over own same she should so some such than that the their
theirs them themselves then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours
yourself yourselves also get got may might must shall us via vs etc one two new use
using used like der die das und ist nicht ein eine mit von für auf den dem des im zu
sich es le la les et est un une des du en pour que qui dans sur au aux pas el los las y
es una por con para del al lo se como más
"""
STOPWORDS = frozenset(_STOPWORD_TEXT.split())


def words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text)]


def content_terms(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]  # noqa: PLR2004


def term_counts(text: str) -> Counter[str]:
    """Unigram and bigram counts of content words (bigrams skip stop words)."""
    tokens = words(text)
    counts: Counter[str] = Counter(content_terms(tokens))
    for left, right in pairwise(tokens):
        if left not in STOPWORDS and right not in STOPWORDS and len(left) > 2 and len(right) > 2:  # noqa: PLR2004
            counts[f"{left} {right}"] += 1
    return counts


def contains_phrase(haystack: str | None, phrase: str) -> bool:
    """Word-boundary, case-insensitive phrase match (all words, in order)."""
    if not haystack:
        return False
    return f" {' '.join(words(phrase))} " in f" {' '.join(words(haystack))} "


def term_coverage(haystack: str | None, phrase: str) -> float:
    """Share of the phrase's content words present anywhere in ``haystack`` (0-1)."""
    wanted = set(content_terms(words(phrase))) or set(words(phrase))
    if not wanted or not haystack:
        return 0.0
    present = set(words(haystack))
    return len(wanted & present) / len(wanted)


def _syllables(word: str) -> int:
    groups = re.findall(r"[aeiouy]+", word.lower())
    count = len(groups) - (1 if word.lower().endswith("e") and len(groups) > 1 else 0)
    return max(1, count)


def flesch_reading_ease(text: str, language: str) -> float | None:
    """Flesch reading ease (0-100, higher = easier); English only."""
    if not language.lower().startswith("en"):
        return None
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if words(s)]
    tokens = words(text)
    if len(tokens) < 100 or not sentences:  # noqa: PLR2004 - too short to be meaningful
        return None
    syllables = sum(_syllables(t) for t in tokens)
    score = 206.835 - 1.015 * (len(tokens) / len(sentences)) - 84.6 * (syllables / len(tokens))
    return round(max(0.0, min(100.0, score)), 1)


@dataclass
class PageContent:
    """What on-page analysis needs from one page (never stored as full HTML)."""

    url: str
    title: str | None = None
    meta_description: str | None = None
    h1: list[str] = field(default_factory=list)
    headings: list[tuple[int, str]] = field(default_factory=list)  # (level, text), h2-h3
    text: str = ""
    word_count: int = 0
    schema_types: list[str] = field(default_factory=list)
    modified: str | None = None  # ISO date from structured data / meta, if any
    lang: str | None = None
    internal_links: int = 0
    images: int = 0
    images_missing_alt: int = 0

    def summary(self) -> dict[str, Any]:
        """Compact, storable form (headings kept; body text is not)."""
        return {
            "url": self.url,
            "title": self.title,
            "meta_description": self.meta_description,
            "h1": self.h1[:3],
            "headings": [[level, text] for level, text in self.headings[:MAX_HEADINGS]],
            "word_count": self.word_count,
            "schema_types": self.schema_types,
            "modified": self.modified,
        }


def _schema_types(json_ld: list[Any]) -> list[str]:
    found: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("@type")
            for value in kind if isinstance(kind, list) else [kind]:
                if isinstance(value, str) and value not in found:
                    found.append(value)
            for key in ("@graph", "mainEntity", "itemListElement"):
                if key in node:
                    visit(node[key])
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(json_ld)
    return found[:20]


def _modified(json_ld: list[Any], tree: LexborHTMLParser) -> str | None:
    for node in json_ld if isinstance(json_ld, list) else []:
        if isinstance(node, dict):
            for key in ("dateModified", "datePublished"):
                value = node.get(key)
                if isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value):
                    return value[:10]
    for prop in ("article:modified_time", "article:published_time"):
        meta = tree.css_first(f'meta[property="{prop}"]')
        value = (meta.attributes.get("content") or "") if meta else ""
        if re.match(r"\d{4}-\d{2}-\d{2}", value):
            return value[:10]
    return None


def extract_content(html: str, url: str, hosts: frozenset[str] | None = None) -> PageContent:
    """Extract the facts on-page analysis compares (headings, main text, schema)."""
    facts = parse_html(html, url)
    tree = LexborHTMLParser(html)
    headings: list[tuple[int, str]] = []
    for node in tree.css("h2, h3"):
        text = " ".join(node.text(separator=" ").split())[:200]
        if text:
            headings.append((int((node.tag or "h2")[1]), text))
    for tag in ("script", "style", "noscript", "template", "svg", "nav", "footer", "header"):
        for node in tree.css(tag):
            node.decompose()
    body = tree.body
    text = " ".join((body.text(separator=" ") if body else "").split())[:MAX_TEXT_CHARS]
    internal = 0
    if hosts:
        internal = sum(1 for link in facts.links if is_internal(link.url, hosts))
    return PageContent(
        url=url,
        title=facts.title,
        meta_description=facts.meta_description,
        h1=facts.h1,
        headings=headings[:MAX_HEADINGS],
        text=text,
        word_count=len(words(text)),
        schema_types=_schema_types(facts.json_ld),
        modified=_modified(facts.json_ld, tree),
        lang=facts.lang,
        internal_links=internal,
        images=facts.images,
        images_missing_alt=facts.images_missing_alt,
    )
