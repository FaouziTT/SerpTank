"""Hybrid, engine-aware rank tracking (plan §4.6).

For every tracked keyword in every market:

1. **Own positions for free** - Google from Search Console (impression-weighted average
   position over the last 7 days of data, filtered to the market's country and device),
   Bing from Bing Webmaster Tools. Source ``gsc`` / ``bing``.
2. **Live SERP checks** (paid, shared via the global cache) for each entitled engine the
   market tracks: own position in the top 100, competitors' positions, SERP features and
   whether an AI answer cites the site. Source ``serp``.

When the daily SERP budget runs out, the job still records first-party positions and
reports how many live checks were skipped - it never guesses the missing ones.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.models import uuid7
from serptank.modules.billing.entitlements import Plan, plan_of
from serptank.modules.crawler.urls import site_hosts
from serptank.modules.integrations.models import BingDaily, GscDaily
from serptank.modules.jobs.service import JobContext, JobFailedError, register_handler
from serptank.modules.keywords.countries import gsc_country
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.search_data.collector import CollectorRouter, SerpUnavailableError
from serptank.modules.search_data.models import Competitor, RankObservation, TrackedKeyword
from serptank.modules.search_data.schema import SerpRequest
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

JOB_KIND = "rank_check"
FIRST_PARTY_DAYS = 7


@dataclass
class FirstParty:
    position: float
    url: str | None
    day: date


async def gsc_position(
    db: AsyncSession, project_id: uuid.UUID, keyword: str, market: ProjectMarket
) -> FirstParty | None:
    latest: date | None = (
        await db.execute(select(func.max(GscDaily.date)).where(GscDaily.project_id == project_id))
    ).scalar_one()
    if latest is None:
        return None
    scope = [
        GscDaily.project_id == project_id,
        GscDaily.date > latest - timedelta(days=FIRST_PARTY_DAYS),
        func.lower(GscDaily.query) == keyword,
        GscDaily.device == market.device.value,
    ]
    country = gsc_country(market.country)
    if country:
        scope.append(GscDaily.country == country)
    row: float | None = (
        await db.execute(
            select(
                func.sum(GscDaily.position * GscDaily.impressions)
                / func.nullif(func.sum(GscDaily.impressions), 0),
            ).where(*scope)
        )
    ).scalar_one()
    if row is None:
        return None
    top_page = (
        await db.execute(
            select(GscDaily.page)
            .where(*scope)
            .group_by(GscDaily.page)
            .order_by(func.sum(GscDaily.clicks).desc(), func.sum(GscDaily.impressions).desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return FirstParty(round(float(row), 1), top_page, latest)


async def bing_position(db: AsyncSession, project_id: uuid.UUID, keyword: str) -> FirstParty | None:
    latest: date | None = (
        await db.execute(select(func.max(BingDaily.date)).where(BingDaily.project_id == project_id))
    ).scalar_one()
    if latest is None:
        return None
    row = (
        await db.execute(
            select(
                func.sum(BingDaily.position * BingDaily.impressions)
                / func.nullif(func.sum(BingDaily.impressions), 0)
            ).where(
                BingDaily.project_id == project_id,
                BingDaily.date > latest - timedelta(days=FIRST_PARTY_DAYS),
                func.lower(BingDaily.query) == keyword,
                BingDaily.position.is_not(None),
            )
        )
    ).scalar_one()
    return FirstParty(round(float(row), 1), None, latest) if row is not None else None


def _row(
    ctx: JobContext, project: Project, keyword: TrackedKeyword, day: date, **values: Any
) -> dict[str, Any]:
    return {
        "id": uuid7(),
        "organization_id": ctx.organization_id,
        "project_id": project.id,
        "keyword_id": keyword.id,
        "date": day,
        "features": [],
        **values,
    }


@dataclass
class _RankRun:
    """State for one rank-check job (keeps the handler readable)."""

    ctx: JobContext
    router: CollectorRouter | None
    project: Project
    plan: Plan
    competitors: list[Competitor]
    today: date
    counts: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(
            ("keywords", "first_party", "serp", "cached", "skipped"), 0
        )
    )
    stopped: str | None = None  # user-safe reason live checks stopped (budget)

    @property
    def hosts(self) -> frozenset[str]:
        return site_hosts(self.project.primary_domain)

    def row(self, keyword: TrackedKeyword, day: date, **values: Any) -> dict[str, Any]:
        return _row(self.ctx, self.project, keyword, day, **values)

    async def first_party(
        self, db: AsyncSession, keyword: TrackedKeyword, market: ProjectMarket
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        engines = {e.value for e in market.search_engines}
        readings: list[tuple[str, FirstParty | None]] = []
        if "google" in engines:
            readings.append(
                ("gsc", await gsc_position(db, self.project.id, keyword.keyword, market))
            )
        if "bing" in engines:
            readings.append(("bing", await bing_position(db, self.project.id, keyword.keyword)))
        for source, own in readings:
            if own is None:
                continue
            await db.execute(
                delete(RankObservation).where(
                    RankObservation.keyword_id == keyword.id,
                    RankObservation.date == own.day,
                    RankObservation.source == source,
                )
            )
            rows.append(
                self.row(
                    keyword,
                    own.day,
                    engine="google" if source == "gsc" else "bing",
                    source=source,
                    domain=self.project.primary_domain,
                    is_own=True,
                    position=own.position,
                    url=own.url,
                )
            )
        self.counts["first_party"] += len(rows)
        return rows

    async def live(
        self, db: AsyncSession, keyword: TrackedKeyword, market: ProjectMarket, engine: str
    ) -> list[dict[str, Any]]:
        if engine not in {e.value for e in self.plan.search_engines}:
            return []  # plan no longer includes this engine: history kept, no new checks
        if self.router is None or not self.router.supports(engine) or self.stopped:
            self.counts["skipped"] += 1  # no live source configured, or budget used up
            return []
        request = SerpRequest(
            engine=engine,
            query=keyword.keyword,
            country=market.country,
            language=market.language,
            device=market.device.value,
            location=market.location,
        )
        try:
            serp = await self.router.get(
                db,
                request,
                organization_id=self.ctx.organization_id,
                org_daily_cap=self.plan.serp_requests_per_day,
                today=self.today,
            )
        except SerpUnavailableError as exc:
            self.counts["skipped"] += 1
            if exc.code in {"serp_org_budget", "serp_global_budget"}:
                self.stopped = exc.message
            return []
        self.counts["cached" if serp.from_cache else "serp"] += 1
        data = serp.data
        rows: list[dict[str, Any]] = []
        targets = [(self.project.primary_domain, True)] + [
            (c.domain, False) for c in self.competitors
        ]
        for domain, is_own in targets:
            hosts = site_hosts(domain)
            result = data.position_of(hosts)
            rows.append(
                self.row(
                    keyword,
                    self.today,
                    engine=engine,
                    source="serp",
                    domain=domain,
                    is_own=is_own,
                    position=float(result.position) if result else None,
                    url=result.url if result else None,
                    features=list(data.features) if is_own else [],
                    ai_cited=data.cites(hosts) if data.ai_answer else None,
                    snapshot_id=serp.snapshot_id,
                )
            )
        return rows


@register_handler(JOB_KIND, queue="serp")
async def run_rank_check(ctx: JobContext) -> dict[str, Any]:
    async with await ctx.session() as db:
        project = await db.get(Project, ctx.project_id)
        org = await db.get(Organization, ctx.organization_id)
        if project is None or project.deleted_at is not None or org is None:
            raise JobFailedError("project_gone", "The project no longer exists.")
        run = _RankRun(
            ctx=ctx,
            router=ctx.runtime.extras.get("serp"),
            project=project,
            plan=plan_of(org),
            competitors=list(
                (
                    await db.execute(select(Competitor).where(Competitor.project_id == project.id))
                ).scalars()
            ),
            today=datetime.now(UTC).date(),
        )
        markets = {
            m.id: m
            for m in (
                await db.execute(
                    select(ProjectMarket).where(ProjectMarket.project_id == project.id)
                )
            ).scalars()
        }
        keywords = list(
            (
                await db.execute(
                    select(TrackedKeyword)
                    .where(TrackedKeyword.project_id == project.id)
                    .order_by(TrackedKeyword.created_at)
                )
            ).scalars()
        )
        await db.execute(
            delete(RankObservation).where(
                RankObservation.project_id == project.id,
                RankObservation.date == run.today,
                RankObservation.source == "serp",
            )
        )
        await db.commit()
        for index, keyword in enumerate(keywords):
            market = markets.get(keyword.market_id)
            if market is None:
                continue
            run.counts["keywords"] += 1
            rows = await run.first_party(db, keyword, market)
            for engine in (e.value for e in market.search_engines):
                rows += await run.live(db, keyword, market, engine)
            if rows:
                await db.execute(insert(RankObservation), rows)
            await db.commit()
            await ctx.report(
                progress=(index + 1) / len(keywords), stage="checking", counters=dict(run.counts)
            )
    result: dict[str, Any] = dict(run.counts)
    if run.stopped:
        result["note"] = run.stopped
    return result
