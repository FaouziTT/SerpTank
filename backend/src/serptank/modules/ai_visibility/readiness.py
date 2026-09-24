"""AI-search readiness: fundamentals first (Google's May 2026 guidance).

No llms.txt or "chunking" points - Google says those aren't needed. We score what lets
any engine find, read, trust and cite a site, from the latest completed crawl:

* **Search access** - Googlebot/Bingbot can reach the homepage (AI Overviews and Copilot
  ground on those indexes) and AI *search* bots (OAI-SearchBot, PerplexityBot, ...)
  aren't blocked. Blocking *training* bots (GPTBot, Google-Extended) is reported but
  not penalised: it doesn't remove a site from AI search answers.
* **Indexable content**, **rendering without JavaScript** (most AI crawlers don't run
  it), **structured data and entity signals**, **content depth**, **page experience**.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.modules.audit.models import AuditIssue
from serptank.modules.crawler.models import Crawl, CrawlPage, CrawlStatus
from serptank.modules.crawler.robots import AI_SEARCH_BOTS, AI_TRAINING_BOTS

BLOCKERS = ("robots_unreachable", "homepage_blocked", "homepage_noindex")
ENTITY_TYPES = frozenset({"Organization", "LocalBusiness", "Corporation", "Store", "WebSite"})


@dataclass
class Component:
    id: str
    label: str
    weight: int
    score: int  # 0-100
    findings: list[str] = field(default_factory=list)


@dataclass
class Readiness:
    available: bool
    score: int | None
    crawl_id: uuid.UUID | None
    components: list[Component]
    bots: dict[str, bool | None]
    note: str | None = None

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["crawl_id"] = str(self.crawl_id) if self.crawl_id else None
        return data


def _share_score(bad: int, total: int) -> int:
    return 100 if total == 0 else round(100 * (1 - min(bad, total) / total))


async def _issue_counts(db: AsyncSession, crawl_id: uuid.UUID) -> dict[str, int]:
    rows = await db.execute(
        select(AuditIssue.rule_id, func.count())
        .where(AuditIssue.crawl_id == crawl_id)
        .group_by(AuditIssue.rule_id)
    )
    return {rule: int(n) for rule, n in rows}


def _access(
    site: dict[str, Any], issues: dict[str, int]
) -> tuple[Component, dict[str, bool | None]]:
    # The start host's robots summary (the crawl records one per host; the first is ours).
    robots: dict[str, Any] = next(iter((site.get("robots") or {}).values()), {})
    bots: dict[str, bool | None] = dict.fromkeys((*AI_SEARCH_BOTS, *AI_TRAINING_BOTS))
    bots.update(robots.get("ai_bots_allowed") or {})
    home = robots.get("home_allowed") or {}
    findings: list[str] = []
    score = 100
    blockers = [b for b in BLOCKERS if issues.get(b)]
    if blockers:
        findings.append("The homepage can't be crawled or indexed (" + ", ".join(blockers) + ").")
        score = 0
    for bot, label in (
        ("googlebot", "Googlebot (AI Overviews, AI Mode)"),
        ("bingbot", "Bingbot (Copilot)"),
    ):
        if home.get(bot) is False:
            findings.append(f"robots.txt blocks {label}.")
            score -= 40
    blocked = [b for b in AI_SEARCH_BOTS if bots.get(b) is False]
    if blocked:
        findings.append("robots.txt blocks AI search bots: " + ", ".join(blocked) + ".")
        score -= 10 * len(blocked)
    training = [b for b in AI_TRAINING_BOTS if bots.get(b) is False]
    if training:
        findings.append(
            "Training bots blocked ("
            + ", ".join(training)
            + "); this doesn't affect AI search citations."
        )
    if not robots.get("ai_bots_allowed"):
        findings.append("Run a new crawl to check AI bot access in robots.txt.")
    return Component("access", "Search and AI bot access", 30, max(0, score), findings), bots


def _schema_types(json_ld: Any) -> set[str]:
    found: set[str] = set()
    for item in json_ld if isinstance(json_ld, list) else []:
        if not isinstance(item, dict):
            continue
        kind = item.get("@type")
        for value in kind if isinstance(kind, list) else [kind]:
            if isinstance(value, str):
                found.add(value)
    return found


async def compute_readiness(db: AsyncSession, project_id: uuid.UUID) -> Readiness:
    crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.project_id == project_id, Crawl.status == CrawlStatus.COMPLETED)
            .order_by(desc(Crawl.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if crawl is None:
        return Readiness(False, None, None, [], {}, "Run a site audit to score AI readiness.")
    issues = await _issue_counts(db, crawl.id)
    pages = list(
        (
            await db.execute(
                select(CrawlPage.url, CrawlPage.indexable_google, CrawlPage.depth, CrawlPage.data)
                .where(
                    CrawlPage.crawl_id == crawl.id,
                    CrawlPage.status_code == 200,  # noqa: PLR2004
                    CrawlPage.content_type.like("text/html%"),
                )
                .limit(20_000)
            )
        ).all()
    )
    total = len(pages)
    access, bots = _access(crawl.site or {}, issues)
    indexable = sum(1 for p in pages if p.indexable_google)
    components = [access]
    components.append(
        Component(
            "indexable",
            "Indexable content",
            20,
            _share_score(total - indexable, total),
            [f"{indexable} of {total} HTML pages are indexable by Google."],
        )
    )
    js = issues.get("js_dependent_content", 0) + issues.get("js_changes_critical_tags", 0)
    components.append(
        Component(
            "rendering",
            "Readable without JavaScript",
            10,
            100 if not js else max(0, 100 - 20 * js),
            [f"{js} page(s) depend on JavaScript for key content; most AI crawlers don't run it."]
            if js
            else ["Key content is in the HTML."],
        )
    )
    home = min(pages, key=lambda p: p.depth if p.depth is not None else 99, default=None)
    home_types = _schema_types((home.data or {}).get("json_ld") if home else None)
    sd_bad = issues.get("structured_data_invalid_json", 0) + issues.get(
        "structured_data_missing_required", 0
    )
    entity = bool(home_types & ENTITY_TYPES)
    components.append(
        Component(
            "entity",
            "Structured data and entity signals",
            15,
            max(0, (60 if entity else 20) + (40 if not sd_bad else max(0, 40 - 10 * sd_bad))),
            [
                "Homepage declares Organization/WebSite structured data."
                if entity
                else "Add Organization (with sameAs profiles) and WebSite markup to the homepage.",
                f"{sd_bad} structured-data error(s)." if sd_bad else "No structured-data errors.",
            ],
        )
    )
    weak = issues.get("thin_content", 0) + issues.get("duplicate_content", 0)
    components.append(
        Component(
            "content",
            "Substantial, original content",
            15,
            _share_score(weak, total),
            [f"{weak} page(s) are thin or duplicated."]
            if weak
            else ["No thin or duplicate pages found."],
        )
    )
    experience = [
        r
        for r in ("not_https", "cwv_origin_poor", "slow_response", "viewport_missing")
        if issues.get(r)
    ]
    components.append(
        Component(
            "experience",
            "Page experience",
            10,
            max(0, 100 - 25 * len(experience)),
            ["Issues: " + ", ".join(experience) + "."]
            if experience
            else ["No page-experience blockers."],
        )
    )
    total_weight = sum(c.weight for c in components)
    score = round(sum(c.score * c.weight for c in components) / total_weight)
    return Readiness(True, score, crawl.id, components, bots)
