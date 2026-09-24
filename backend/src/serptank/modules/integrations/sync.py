"""Scheduled and on-demand data syncs, run as jobs (one kind per source).

Every sync is idempotent: it replaces the date range it fetched (delete + insert in one
transaction per day or range), so retries and overlapping runs never double-count.
Provider failures are recorded on the connection and surfaced to users as the job's
user-safe error; revoked grants flip the connection to ``reauth_required``.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, desc, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.http import EgressPolicy
from serptank.core.models import uuid7
from serptank.modules.crawler.models import Crawl, CrawlPage, CrawlStatus
from serptank.modules.integrations.credentials import (
    bing_api_key,
    google_access_token,
    record_provider_failure,
)
from serptank.modules.integrations.models import (
    BingDaily,
    Ga4Daily,
    GscDaily,
    ProjectSource,
    Provider,
    SourceKind,
    VitalsDaily,
)
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.bing import BingWebmasterClient
from serptank.modules.integrations.providers.crux import CruxClient
from serptank.modules.integrations.providers.ga4 import Ga4Client
from serptank.modules.integrations.providers.google_oauth import SCOPES
from serptank.modules.integrations.providers.gsc import GscClient
from serptank.modules.jobs.service import JobContext, JobFailedError, register_handler
from serptank.modules.projects.models import Project

logger = structlog.get_logger(__name__)

GSC_LAG_DAYS = 3  # Search Console data is final after ~2-3 days
GA4_WINDOW_DAYS = 30
VITALS_URLS = 10
INSERT_BATCH = 1000
SYNC_KINDS = {
    SourceKind.GSC: "gsc_sync",
    SourceKind.GA4: "ga4_sync",
    SourceKind.BING: "bing_sync",
}


async def _source(db: AsyncSession, ctx: JobContext, kind: SourceKind) -> ProjectSource:
    source = (
        await db.execute(
            select(ProjectSource).where(
                ProjectSource.project_id == ctx.project_id, ProjectSource.kind == kind
            )
        )
    ).scalar_one_or_none()
    if source is None:
        raise JobFailedError("source_not_linked", "Link a property to this project first.")
    return source


async def _insert(db: AsyncSession, model: Any, rows: list[dict[str, Any]]) -> None:
    for start in range(0, len(rows), INSERT_BATCH):
        await db.execute(insert(model), rows[start : start + INSERT_BATCH])


async def _mark(
    db: AsyncSession, source: ProjectSource, status: str, through: date | None = None
) -> None:
    source.last_sync_at = datetime.now(UTC)
    source.last_sync_status = status
    if through is not None:
        source.synced_through = through
    await db.commit()


async def _guarded(
    ctx: JobContext, provider: Provider, work: Callable[[AsyncSession], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    """Run ``work`` and translate provider errors into user-safe job failures."""
    async with await ctx.session() as db:
        try:
            return await work(db)
        except ProviderError as exc:
            await db.rollback()
            await record_provider_failure(db, ctx.organization_id, provider, exc)
            raise JobFailedError(exc.code, exc.message) from exc


def _http(ctx: JobContext) -> Any:
    return ctx.runtime.http_factory(EgressPolicy(), ctx.runtime.settings.crawler_user_agent)


def _keyring(ctx: JobContext) -> Any:
    if ctx.runtime.keyring is None:
        raise JobFailedError("internal_error", "Credential storage is not configured.")
    return ctx.runtime.keyring


@register_handler("gsc_sync", queue="integrations")
async def sync_gsc(ctx: JobContext) -> dict[str, Any]:
    settings = ctx.runtime.settings
    http = _http(ctx)

    async def work(db: AsyncSession) -> dict[str, Any]:
        source = await _source(db, ctx, SourceKind.GSC)
        token = await google_access_token(
            db,
            ctx.organization_id,
            keyring=_keyring(ctx),
            settings=settings,
            http=http,
            scope=SCOPES["gsc"],
        )
        client = GscClient(http, token)
        end = datetime.now(UTC).date() - timedelta(days=GSC_LAG_DAYS)
        start = (
            source.synced_through + timedelta(days=1)
            if source.synced_through
            else end - timedelta(days=settings.gsc_backfill_days - 1)
        )
        # Re-fetch the last few days too: late-arriving data makes them change.
        start = min(start, end - timedelta(days=GSC_LAG_DAYS))
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        total = 0
        for index, day in enumerate(days):
            rows = await client.search_analytics(source.property_id, day)
            await db.execute(
                delete(GscDaily).where(GscDaily.project_id == ctx.project_id, GscDaily.date == day)
            )
            await _insert(
                db,
                GscDaily,
                [
                    {
                        "id": uuid7(),
                        "organization_id": ctx.organization_id,
                        "project_id": ctx.project_id,
                        "date": r.date,
                        "query": r.query,
                        "page": r.page,
                        "country": r.country,
                        "device": r.device,
                        "clicks": r.clicks,
                        "impressions": r.impressions,
                        "position": r.position,
                    }
                    for r in rows
                ],
            )
            await _mark(db, source, "ok", through=day)
            total += len(rows)
            await ctx.report(
                progress=(index + 1) / max(1, len(days)),
                stage="syncing",
                counters={"days": index + 1, "rows": total},
            )
        return {"days": len(days), "rows": total}

    try:
        return await _guarded(ctx, Provider.GOOGLE, work)
    finally:
        await http.aclose()


@register_handler("ga4_sync", queue="integrations")
async def sync_ga4(ctx: JobContext) -> dict[str, Any]:
    settings = ctx.runtime.settings
    http = _http(ctx)

    async def work(db: AsyncSession) -> dict[str, Any]:
        source = await _source(db, ctx, SourceKind.GA4)
        token = await google_access_token(
            db,
            ctx.organization_id,
            keyring=_keyring(ctx),
            settings=settings,
            http=http,
            scope=SCOPES["ga4"],
        )
        end = datetime.now(UTC).date() - timedelta(days=1)
        start = end - timedelta(days=GA4_WINDOW_DAYS - 1)
        rows = await Ga4Client(http, token).organic_landing_pages(source.property_id, start, end)
        await db.execute(
            delete(Ga4Daily).where(
                Ga4Daily.project_id == ctx.project_id, Ga4Daily.date.between(start, end)
            )
        )
        await _insert(
            db,
            Ga4Daily,
            [
                {
                    "id": uuid7(),
                    "organization_id": ctx.organization_id,
                    "project_id": ctx.project_id,
                    "date": r.date,
                    "landing_page": r.landing_page,
                    "sessions": r.sessions,
                    "engaged_sessions": r.engaged_sessions,
                    "conversions": r.conversions,
                    "revenue": r.revenue,
                }
                for r in rows
            ],
        )
        await _mark(db, source, "ok", through=end)
        return {"rows": len(rows), "from": start.isoformat(), "to": end.isoformat()}

    try:
        return await _guarded(ctx, Provider.GOOGLE, work)
    finally:
        await http.aclose()


@register_handler("bing_sync", queue="integrations")
async def sync_bing(ctx: JobContext) -> dict[str, Any]:
    http = _http(ctx)

    async def work(db: AsyncSession) -> dict[str, Any]:
        source = await _source(db, ctx, SourceKind.BING)
        key = await bing_api_key(db, ctx.organization_id, _keyring(ctx))
        rows = await BingWebmasterClient(http, key).query_stats(source.property_id)
        if rows:
            days = {r.date for r in rows}
            await db.execute(
                delete(BingDaily).where(
                    BingDaily.project_id == ctx.project_id, BingDaily.date.in_(days)
                )
            )
            await _insert(
                db,
                BingDaily,
                [
                    {
                        "id": uuid7(),
                        "organization_id": ctx.organization_id,
                        "project_id": ctx.project_id,
                        "date": r.date,
                        "query": r.query,
                        "clicks": r.clicks,
                        "impressions": r.impressions,
                        "position": r.position,
                    }
                    for r in rows
                ],
            )
        await _mark(db, source, "ok", through=max((r.date for r in rows), default=None))
        return {"rows": len(rows)}

    try:
        return await _guarded(ctx, Provider.BING, work)
    finally:
        await http.aclose()


async def _vitals_targets(db: AsyncSession, project: Project) -> list[str]:
    """Key URLs: homepage and shallow indexable pages from the latest audit."""
    crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.project_id == project.id, Crawl.status == CrawlStatus.COMPLETED)
            .order_by(desc(Crawl.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    urls = [f"https://{project.primary_domain}/"]
    if crawl is not None:
        rows = await db.execute(
            select(CrawlPage.url)
            .where(CrawlPage.crawl_id == crawl.id, CrawlPage.indexable_google.is_(True))
            .order_by(CrawlPage.depth.asc().nulls_last(), desc(CrawlPage.inlinks))
            .limit(VITALS_URLS)
        )
        urls.extend(url for (url,) in rows if url not in urls)
    return urls[:VITALS_URLS]


@register_handler("vitals_sync", queue="integrations")
async def sync_vitals(ctx: JobContext) -> dict[str, Any]:
    api_key = ctx.runtime.settings.google_api_key.get_secret_value()
    if not api_key:
        raise JobFailedError(
            "vitals_unavailable", "Core Web Vitals data isn't configured on this server."
        )
    http = _http(ctx)
    try:
        async with await ctx.session() as db:
            project = await db.get(Project, ctx.project_id)
            if project is None or project.deleted_at is not None:
                raise JobFailedError("project_gone", "The project no longer exists.")
            client = CruxClient(http, api_key)
            today = datetime.now(UTC).date()
            origin = f"https://{project.primary_domain}"
            requests: list[tuple[str, str | None]] = [(origin, None)]
            requests += [(origin, url) for url in await _vitals_targets(db, project)]
            stored = 0
            await db.execute(
                delete(VitalsDaily).where(
                    VitalsDaily.project_id == project.id, VitalsDaily.date == today
                )
            )
            for index, (origin_value, url) in enumerate(requests):
                for form_factor in ("PHONE", "DESKTOP"):
                    try:
                        vitals = await client.query(
                            origin=None if url else origin_value, url=url, form_factor=form_factor
                        )
                    except ProviderError as exc:
                        raise JobFailedError(exc.code, exc.message) from exc
                    if vitals is None:
                        continue  # not enough real-user data: honestly absent
                    db.add(
                        VitalsDaily(
                            organization_id=ctx.organization_id,
                            project_id=project.id,
                            date=today,
                            target=vitals.target,
                            scope=vitals.scope,
                            form_factor=form_factor,
                            **vitals.values,
                        )
                    )
                    stored += 1
                await ctx.report(
                    progress=(index + 1) / len(requests),
                    stage="syncing",
                    counters={"records": stored},
                )
            await db.commit()
            return {"records": stored, "targets": len(requests)}
    finally:
        await http.aclose()


async def latest_vitals(
    db: AsyncSession, project_id: uuid.UUID, days: int = 35
) -> list[VitalsDaily]:
    """Most recent vitals row per (target, form factor) within ``days``."""
    since = datetime.now(UTC).date() - timedelta(days=days)
    newest = (
        select(VitalsDaily.target, VitalsDaily.form_factor, func.max(VitalsDaily.date).label("d"))
        .where(VitalsDaily.project_id == project_id, VitalsDaily.date >= since)
        .group_by(VitalsDaily.target, VitalsDaily.form_factor)
        .subquery()
    )
    rows = await db.execute(
        select(VitalsDaily)
        .join(
            newest,
            (VitalsDaily.target == newest.c.target)
            & (VitalsDaily.form_factor == newest.c.form_factor)
            & (VitalsDaily.date == newest.c.d),
        )
        .where(VitalsDaily.project_id == project_id)
    )
    return list(rows.scalars())
