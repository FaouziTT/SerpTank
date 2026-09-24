"""Keyword-to-page map and cannibalization, from first-party data.

* **Keyword map** - each tracked keyword, the page the team assigned to it
  (``tracked_keywords.target_url``) and the page that actually ranks (latest own
  observation from GSC/Bing/SERP). A mismatch means Google prefers another page.
* **Cannibalization** - Search Console queries where two or more of the site's pages
  each earn a meaningful share of impressions, so they compete with each other.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.modules.integrations.models import GscDaily
from serptank.modules.search_data.models import RankObservation, TrackedKeyword

WINDOW_DAYS = 28
MIN_QUERY_IMPRESSIONS = 50
MIN_PAGE_SHARE = 0.1
MAX_ISSUES = 100


@dataclass
class CompetingPage:
    page: str
    impressions: int
    clicks: int
    position: float
    share: float


@dataclass
class Cannibalization:
    query: str
    impressions: int
    clicks: int
    pages: list[CompetingPage] = field(default_factory=list)


async def cannibalization(
    db: AsyncSession, project_id: uuid.UUID
) -> tuple[list[Cannibalization], bool]:
    """Competing-page issues and whether any Search Console data exists."""
    latest: date | None = (
        await db.execute(select(func.max(GscDaily.date)).where(GscDaily.project_id == project_id))
    ).scalar_one()
    if latest is None:
        return [], False
    impressions = func.sum(GscDaily.impressions)
    rows = await db.execute(
        select(
            GscDaily.query,
            GscDaily.page,
            impressions,
            func.sum(GscDaily.clicks),
            func.sum(GscDaily.position * GscDaily.impressions) / func.nullif(impressions, 0),
        )
        .where(
            GscDaily.project_id == project_id,
            GscDaily.date > latest - timedelta(days=WINDOW_DAYS),
        )
        .group_by(GscDaily.query, GscDaily.page)
    )
    by_query: dict[str, list[tuple[str, int, int, float]]] = {}
    for query, page, imps, clicks, position in rows:
        by_query.setdefault(query.lower(), []).append(
            (page, int(imps or 0), int(clicks or 0), float(position or 0.0))
        )
    issues = []
    for query, pages in by_query.items():
        total = sum(p[1] for p in pages)
        if total < MIN_QUERY_IMPRESSIONS:
            continue
        competing = [
            CompetingPage(page, imps, clicks, round(pos, 1), round(imps / total, 3))
            for page, imps, clicks, pos in pages
            if imps / total >= MIN_PAGE_SHARE
        ]
        if len(competing) >= 2:  # noqa: PLR2004
            competing.sort(key=lambda p: -p.impressions)
            issues.append(Cannibalization(query, total, sum(p[2] for p in pages), competing))
    issues.sort(key=lambda i: -i.impressions)
    return issues[:MAX_ISSUES], True


@dataclass
class MapRow:
    keyword_id: uuid.UUID
    keyword: str
    market_id: uuid.UUID
    target_url: str | None
    ranking_url: str | None
    ranking_source: str | None
    position: float | None
    status: str  # aligned | mismatch | unassigned | not_ranking


async def keyword_map(db: AsyncSession, project_id: uuid.UUID) -> list[MapRow]:
    keywords = list(
        (
            await db.execute(
                select(TrackedKeyword)
                .where(TrackedKeyword.project_id == project_id)
                .order_by(TrackedKeyword.keyword)
            )
        ).scalars()
    )
    latest = (
        select(
            RankObservation.keyword_id,
            RankObservation.url,
            RankObservation.source,
            RankObservation.position,
            func.row_number()
            .over(
                partition_by=RankObservation.keyword_id,
                order_by=(RankObservation.date.desc(), RankObservation.source),
            )
            .label("rn"),
        )
        .where(
            RankObservation.project_id == project_id,
            RankObservation.is_own.is_(True),
            RankObservation.engine == "google",
            RankObservation.url.is_not(None),
        )
        .subquery()
    )
    ranking = {
        kid: (url, source, position)
        for kid, url, source, position in await db.execute(
            select(latest.c.keyword_id, latest.c.url, latest.c.source, latest.c.position).where(
                latest.c.rn == 1
            )
        )
    }
    rows = []
    for kw in keywords:
        url, source, position = ranking.get(kw.id, (None, None, None))
        if not kw.target_url:
            status = "unassigned"
        elif not url:
            status = "not_ranking"
        else:
            status = "aligned" if _same(url, kw.target_url) else "mismatch"
        rows.append(
            MapRow(kw.id, kw.keyword, kw.market_id, kw.target_url, url, source, position, status)
        )
    return rows


def _same(a: str, b: str) -> bool:
    return a.rstrip("/").lower() == b.rstrip("/").lower()
