"""Health score and fix priority.

* **Score (0-100):** ``100 * 100 / (100 + penalty)`` where each rule adds
  ``severity weight x reach``. Reach is 1 for site-level issues, else the square root
  of the share of HTML pages affected (a problem on a few pages still counts, but not
  as much as a site-wide one). The curve never hits 0 and degrades smoothly.
* **Priority:** impact (weight x reach) divided by effort, so quick high-impact fixes
  come first. Scores are computed per engine: Google (baseline + Google deltas) is the
  headline number; Bing etc. add their own deltas.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Rule

WEIGHTS = {
    Severity.CRITICAL: 30.0,
    Severity.HIGH: 12.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 1.5,
    Severity.INFO: 0.0,
}


def reach(site_level: bool, affected: int, total_pages: int) -> float:
    if site_level:
        return 1.0
    if total_pages <= 0:
        return 0.0
    return math.sqrt(min(1.0, affected / total_pages))


def impact(rule: Rule, site_level: bool, affected: int, total_pages: int) -> float:
    return WEIGHTS[rule.severity] * reach(site_level, affected, total_pages)


def priority(rule: Rule, site_level: bool, affected: int, total_pages: int) -> float:
    return round(impact(rule, site_level, affected, total_pages) / max(1, rule.effort), 3)


def score(impacts: Iterable[float]) -> float:
    penalty = sum(impacts)
    return round(100.0 * 100.0 / (100.0 + penalty), 1)
