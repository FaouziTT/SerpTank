"""Audit rule registry.

Every rule has stable metadata (id, category, severity, scope, effort, explanation and
fix) and a pure check function over a :class:`~serptank.modules.audit.site.Site`. Rules
encode Google Search Essentials as the baseline (``scope="all"`` - they matter for
every engine); engine-specific deltas carry that engine as their scope and are only
evaluated when the project tracks the engine (plan §4.5).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from serptank.modules.audit.models import Severity

if TYPE_CHECKING:
    from serptank.modules.audit.site import Site

CATEGORIES = {
    "indexability": "Indexability",
    "crawlability": "Crawlability and site structure",
    "links": "Internal links",
    "content": "Titles, descriptions and content",
    "page_experience": "Mobile and page experience",
    "structured_data": "Structured data",
    "international": "International (hreflang)",
    "rendering": "JavaScript rendering",
    "spam": "Spam-policy red flags",
    "engines": "Other search engines",
}


@dataclass(frozen=True)
class Finding:
    url: str | None = None  # None = site-level
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    category: str
    severity: Severity
    description: str
    fix: str
    scope: str = "all"
    effort: int = 2  # 1 = quick fix, 3 = project
    reference: str | None = None
    check: Callable[[Site], Iterable[Finding]] = field(default=lambda _s: (), compare=False)


RULES: dict[str, Rule] = {}


def rule(
    id: str,
    *,
    title: str,
    category: str,
    severity: Severity,
    description: str,
    fix: str,
    scope: str = "all",
    effort: int = 2,
    reference: str | None = None,
) -> Callable[[Callable[[Site], Iterable[Finding]]], Callable[[Site], Iterable[Finding]]]:
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category}")

    def decorator(fn: Callable[[Site], Iterable[Finding]]) -> Callable[[Site], Iterable[Finding]]:
        if id in RULES:
            raise ValueError(f"duplicate rule id {id}")
        RULES[id] = Rule(
            id=id,
            title=title,
            category=category,
            severity=severity,
            description=description,
            fix=fix,
            scope=scope,
            effort=effort,
            reference=reference,
            check=fn,
        )
        return fn

    return decorator
