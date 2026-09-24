"""Search Presence: one Google-first view of how visible a project is, per market.

Every block is computed from stored first-party or observed data and says when it has
none (``None`` / empty lists) - nothing is estimated to fill gaps.

**Search Presence Score (0-100)** for a market::

    classic = sum_e w_e * sov_e / sum_e w_e      (engines with tracked data)
    score   = 100 * (0.8 * classic + 0.2 * ai)  if AI citation data exists
            = 100 * classic                      otherwise

``sov_e`` is the CTR-weighted share of voice of the tracked keywords on engine ``e``
(``keywords.ctr.share_of_voice``, volume-weighted when volumes are known). ``w_e`` is
the engine's approximate search share in the market's country (``ENGINE_SHARE``,
configurable estimates, Google-dominant by default). ``ai`` is the average citation
rate across sampled AI engines over 30 days.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.modules.ai_visibility.detect import entity_for
from serptank.modules.ai_visibility.service import get_profile, visibility
from serptank.modules.audit.models import AuditIssue
from serptank.modules.crawler.models import Crawl, CrawlStatus
from serptank.modules.integrations.models import GscDaily
from serptank.modules.integrations.providers.crux import assess
from serptank.modules.integrations.sync import latest_vitals
from serptank.modules.keywords.ctr import share_of_voice
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.search_data.models import KeywordMetrics, RankObservation, TrackedKeyword

WINDOW_DAYS = 28
AI_WEIGHT = 0.2
# Approximate search-engine shares by country (2026 estimates; tune as data arrives).
DEFAULT_SHARE = {
    "google": 0.90, "bing": 0.04, "yahoo": 0.01, "duckduckgo": 0.01,
    "yandex": 0.01, "baidu": 0.005, "naver": 0.005, "seznam": 0.005,
}  # fmt: skip
ENGINE_SHARE: dict[str, dict[str, float]] = {
    "RU": {"yandex": 0.65, "google": 0.32, "bing": 0.01},
    "CN": {"baidu": 0.65, "bing": 0.15, "google": 0.03},
    "KR": {"naver": 0.45, "google": 0.45, "bing": 0.03},
    "CZ": {"google": 0.83, "seznam": 0.12, "bing": 0.03},
    "US": {"google": 0.87, "bing": 0.07, "yahoo": 0.02, "duckduckgo": 0.02},
}
BUCKETS = (("top3", 3), ("top10", 10), ("top20", 20), ("top100", 100))


def engine_weight(country: str, engine: str) -> float:
    return ENGINE_SHARE.get(country.upper(), DEFAULT_SHARE).get(
        engine, DEFAULT_SHARE.get(engine, 0.0)
    )


def bucket(position: float | None) -> str:
    if position is None:
        return "not_ranking"
    for name, limit in BUCKETS:
        if position <= limit:
            return name
    return "not_ranking"


async def latest_positions(
    db: AsyncSession, project_id: uuid.UUID, market_id: uuid.UUID
) -> dict[str, dict[str, float | None]]:
    """{engine: {keyword: latest own position}}; live SERP readings preferred on ties."""
    ranked = (
        select(
            TrackedKeyword.keyword,
            RankObservation.engine,
            RankObservation.position,
            func.row_number()
            .over(
                partition_by=(RankObservation.keyword_id, RankObservation.engine),
                order_by=(
                    RankObservation.date.desc(),
                    case((RankObservation.source == "serp", 0), else_=1),
                ),
            )
            .label("rn"),
        )
        .join(TrackedKeyword, TrackedKeyword.id == RankObservation.keyword_id)
        .where(
            RankObservation.project_id == project_id,
            RankObservation.is_own.is_(True),
            TrackedKeyword.market_id == market_id,
        )
        .subquery()
    )
    out: dict[str, dict[str, float | None]] = defaultdict(dict)
    rows = await db.execute(
        select(ranked.c.keyword, ranked.c.engine, ranked.c.position).where(ranked.c.rn == 1)
    )
    for keyword, engine, position in rows:
        out[engine][keyword] = position
    return out


async def _volumes(db: AsyncSession, keywords: list[str], country: str) -> dict[str, int]:
    if not keywords:
        return {}
    rows = await db.execute(
        select(KeywordMetrics.keyword, func.max(KeywordMetrics.avg_monthly_searches))
        .where(KeywordMetrics.keyword.in_(keywords), KeywordMetrics.country == country)
        .group_by(KeywordMetrics.keyword)
    )
    return {k: int(v) for k, v in rows if v}


async def _gsc(db: AsyncSession, project_id: uuid.UUID) -> dict[str, Any] | None:
    latest: date | None = (
        await db.execute(select(func.max(GscDaily.date)).where(GscDaily.project_id == project_id))
    ).scalar_one()
    if latest is None:
        return None
    start = latest - timedelta(days=2 * WINDOW_DAYS)
    rows = (
        await db.execute(
            select(
                GscDaily.date,
                func.sum(GscDaily.clicks),
                func.sum(GscDaily.impressions),
                func.sum(GscDaily.position * GscDaily.impressions),
            )
            .where(GscDaily.project_id == project_id, GscDaily.date > start)
            .group_by(GscDaily.date)
            .order_by(GscDaily.date)
        )
    ).all()
    split = latest - timedelta(days=WINDOW_DAYS)

    def total(current: bool) -> dict[str, Any]:
        part = [r for r in rows if (r[0] > split) == current]
        clicks = sum(int(r[1] or 0) for r in part)
        imps = sum(int(r[2] or 0) for r in part)
        weighted = sum(float(r[3] or 0) for r in part)
        return {
            "clicks": clicks,
            "impressions": imps,
            "ctr": round(clicks / imps, 4) if imps else None,
            "position": round(weighted / imps, 1) if imps else None,
        }

    return {
        "latest_date": latest.isoformat(),
        "current": total(True),
        "previous": total(False),
        "daily": [
            {"date": d.isoformat(), "clicks": int(c or 0), "impressions": int(i or 0)}
            for d, c, i, _ in rows
            if d > split
        ],
    }


async def _opportunities(db: AsyncSession, project_id: uuid.UUID) -> list[dict[str, Any]]:
    """Striking-distance queries: average position 8-20 over the window."""
    latest: date | None = (
        await db.execute(select(func.max(GscDaily.date)).where(GscDaily.project_id == project_id))
    ).scalar_one()
    if latest is None:
        return []
    imps = func.sum(GscDaily.impressions)
    position = func.sum(GscDaily.position * GscDaily.impressions) / func.nullif(imps, 0)
    rows = await db.execute(
        select(GscDaily.query, imps, func.sum(GscDaily.clicks), position)
        .where(
            GscDaily.project_id == project_id,
            GscDaily.date > latest - timedelta(days=WINDOW_DAYS),
        )
        .group_by(GscDaily.query)
        .having(position.between(8, 20))
        .order_by(desc(imps))
        .limit(5)
    )
    return [
        {"query": q, "impressions": int(i or 0), "clicks": int(c or 0), "position": round(p, 1)}
        for q, i, c, p in rows
    ]


async def _audit(db: AsyncSession, project_id: uuid.UUID) -> dict[str, Any] | None:
    crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.project_id == project_id, Crawl.status == CrawlStatus.COMPLETED)
            .order_by(desc(Crawl.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if crawl is None:
        return None
    counts = await db.execute(
        select(AuditIssue.severity, func.count())
        .where(AuditIssue.crawl_id == crawl.id)
        .group_by(AuditIssue.severity)
    )
    return {
        "crawl_id": str(crawl.id),
        "date": crawl.created_at.date().isoformat(),
        "score": crawl.score,
        "pages": crawl.pages_fetched,
        "issues": {sev.value: int(n) for sev, n in counts},
    }


async def _vitals(db: AsyncSession, project_id: uuid.UUID) -> dict[str, Any] | None:
    rows = await latest_vitals(db, project_id)
    if not rows:
        return None
    verdicts = Counter(assess({"lcp_ms": v.lcp_ms, "inp_ms": v.inp_ms, "cls": v.cls}) for v in rows)
    known = sum(n for k, n in verdicts.items() if k != "unknown")
    return {
        "assessed": known,
        "good": verdicts["good"],
        "needs_improvement": verdicts["needs_improvement"],
        "poor": verdicts["poor"],
        "pass_rate": round(verdicts["good"] / known, 4) if known else None,
    }


async def presence(db: AsyncSession, project: Project, market: ProjectMarket) -> dict[str, Any]:
    positions = await latest_positions(db, project.id, market.id)
    keywords = sorted({k for per_engine in positions.values() for k in per_engine})
    volumes = await _volumes(db, keywords, market.country)
    engines: list[dict[str, Any]] = []
    # Google first, then by the engine's share in this market.
    tracked = sorted(
        (e.value for e in market.search_engines),
        key=lambda e: (e != "google", -engine_weight(market.country, e)),
    )
    for engine in tracked + sorted(set(positions) - set(tracked)):
        per_kw = positions.get(engine, {})
        if not per_kw:
            engines.append(
                {
                    "engine": engine,
                    "keywords": 0,
                    "share_of_voice": None,
                    "distribution": {},
                    "weight": engine_weight(market.country, engine),
                }
            )
            continue
        sov = share_of_voice((p, volumes.get(k)) for k, p in per_kw.items())
        engines.append(
            {
                "engine": engine,
                "keywords": len(per_kw),
                "share_of_voice": sov,
                "distribution": dict(Counter(bucket(p) for p in per_kw.values())),
                "weight": engine_weight(market.country, engine),
            }
        )
    profile = await get_profile(db, project)
    own = entity_for(project.primary_domain, profile.brand_terms)
    ai = await visibility(db, project, 30, own.key)
    ai_rates = [
        e["citation_rate"]["rate"] for e in ai["engines"] if e["citation_rate"]["rate"] is not None
    ]
    scored = [e for e in engines if e["share_of_voice"] is not None and e["weight"] > 0]
    classic = (
        sum(e["weight"] * e["share_of_voice"] for e in scored) / sum(e["weight"] for e in scored)
        if scored
        else None
    )
    ai_score = sum(ai_rates) / len(ai_rates) if ai_rates else None
    if classic is None and ai_score is None:
        score = None
    elif ai_score is None:
        score = round(100 * (classic or 0.0))
    elif classic is None:
        score = round(100 * ai_score)
    else:
        score = round(100 * ((1 - AI_WEIGHT) * classic + AI_WEIGHT * ai_score))
    return {
        "market_id": str(market.id),
        "generated_at": datetime.now(UTC).isoformat(),
        "score": score,
        "score_parts": {"classic": classic, "ai": ai_score, "ai_weight": AI_WEIGHT},
        "volumes_known": bool(volumes),
        "engines": engines,
        "gsc": await _gsc(db, project.id),
        "opportunities": await _opportunities(db, project.id),
        "audit": await _audit(db, project.id),
        "vitals": await _vitals(db, project.id),
        "ai": {"engines": ai["engines"], "first_party": ai["first_party"]},
    }
