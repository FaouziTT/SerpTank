"""Run every applicable rule over a :class:`Site` and score the result (pure function)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import structlog

from serptank.modules.audit import checks  # noqa: F401 - registers the rules
from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import RULES, Finding, Rule
from serptank.modules.audit.scoring import impact, priority, score
from serptank.modules.audit.site import Site

logger = structlog.get_logger(__name__)
MAX_FINDINGS_PER_RULE = 5000


@dataclass
class RuleResult:
    rule: Rule
    findings: list[Finding]
    site_level: bool
    affected: int
    impact: float
    priority: float


@dataclass
class AuditResult:
    results: list[RuleResult] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)  # engine -> 0..100
    by_severity: dict[str, int] = field(default_factory=dict)
    pages_audited: int = 0
    failed_rules: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, object]:
        return {
            "scores": self.scores,
            "by_severity": self.by_severity,
            "by_rule": {r.rule.id: r.affected for r in self.results},
            "pages_audited": self.pages_audited,
            "failed_rules": self.failed_rules,
        }


def applicable(rule: Rule, engines: frozenset[str]) -> bool:
    return rule.scope in {"all", "google"} or rule.scope in engines


def evaluate(site: Site) -> AuditResult:
    result = AuditResult(pages_audited=len(site.html_pages))
    total = max(1, len(site.html_pages))
    for rule in RULES.values():
        if not applicable(rule, site.engines):
            continue
        try:
            findings = list(rule.check(site))[:MAX_FINDINGS_PER_RULE]
        except Exception:
            # One faulty rule must not sink the audit; it is reported, not hidden.
            logger.exception("audit_rule_failed", rule=rule.id)
            result.failed_rules.append(rule.id)
            continue
        if not findings:
            continue
        site_level = all(f.url is None for f in findings) or rule.id in SITE_LEVEL_RULES
        affected = len({f.url for f in findings})
        result.results.append(
            RuleResult(
                rule=rule,
                findings=findings,
                site_level=site_level,
                affected=affected,
                impact=impact(rule, site_level, affected, total),
                priority=priority(rule, site_level, affected, total),
            )
        )
    result.results.sort(key=lambda r: (-r.priority, r.rule.id))
    engines = {"google", *site.engines}
    for engine in sorted(engines):
        result.scores[engine] = score(
            r.impact for r in result.results if r.rule.scope in {"all", engine}
        )
    severities: Counter[str] = Counter()
    for r in result.results:
        severities[r.rule.severity.value] += r.affected
    result.by_severity = {s.value: severities.get(s.value, 0) for s in Severity}
    return result


# Rules whose single finding describes the whole site even though it carries a URL.
SITE_LEVEL_RULES = frozenset(
    {
        "robots_unreachable",
        "homepage_blocked",
        "homepage_noindex",
        "soft_404_site",
        "sitemap_not_in_robots",
        "bing_crawl_delay",
        "google_ignores_crawl_delay",
        "yandex_directives",
        "baidu_language",
    }
)
