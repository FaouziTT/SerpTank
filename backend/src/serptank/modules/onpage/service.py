"""On-page jobs: ``page_optimize`` (score one URL for a keyword) and ``content_brief``.

Both start from the live SERP for the market (through the shared, budgeted collector
cache), read the top organic pages politely, and compute everything in-house. When
the SERP is unavailable (no vendor, budget spent) the optimizer still runs the checks
that don't need competitors and says what is missing; the brief is built from what
evidence exists and lists the gaps in ``notes``.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.http import EgressPolicy, SafeHttpClient
from serptank.modules.billing.entitlements import plan_of
from serptank.modules.crawler.models import Crawl, CrawlLink, CrawlPage, CrawlStatus
from serptank.modules.crawler.urls import normalize_url, site_hosts
from serptank.modules.jobs.service import JobContext, JobFailedError, register_handler
from serptank.modules.keywords.intent import classify
from serptank.modules.onpage.analyzer import analyze
from serptank.modules.onpage.brief import build_brief
from serptank.modules.onpage.fetch import FetchOutcome, fetch_many, fetch_page
from serptank.modules.onpage.models import ContentBrief, PageOptimization
from serptank.modules.onpage.text import content_terms, words
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.search_data.collector import CollectorRouter, SerpUnavailableError
from serptank.modules.search_data.schema import SerpRequest, SerpSnapshotData
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

OPTIMIZE_KIND = "page_optimize"
BRIEF_KIND = "content_brief"
TOP_N = 10
MAX_LINK_SUGGESTIONS = 10


# ------------------------------------------------------------------------- helpers
async def live_serp(
    ctx: JobContext, db: AsyncSession, market: ProjectMarket, keyword: str
) -> tuple[SerpSnapshotData | None, str | None]:
    """The market's Google SERP (the primary engine), or ``(None, reason)``."""
    router: CollectorRouter | None = ctx.runtime.extras.get("serp")
    org = await db.get(Organization, ctx.organization_id)
    if router is None or org is None:
        return None, "Live search results aren't configured on this server."
    request = SerpRequest(
        engine="google",
        query=keyword,
        country=market.country,
        language=market.language,
        device=market.device.value,
        location=market.location,
        depth=TOP_N * 2,
    )
    try:
        result = await router.get(
            db,
            request,
            organization_id=ctx.organization_id,
            org_daily_cap=plan_of(org).serp_requests_per_day,
            today=datetime.now(UTC).date(),
        )
    except SerpUnavailableError as exc:
        return None, exc.message
    return result.data, None


def competitor_rows(
    serp: SerpSnapshotData, outcomes: dict[str, FetchOutcome]
) -> list[dict[str, Any]]:
    rows = []
    for result in serp.organic[:TOP_N]:
        outcome = outcomes.get(result.url)
        if outcome is None:
            continue
        rows.append(
            {
                "position": result.position,
                "domain": result.domain,
                "url": result.url,
                "title": result.title,
                "word_count": outcome.page.word_count if outcome.page else None,
                "skipped": outcome.skipped,
                "headings": [t for level, t in outcome.page.headings if level == 2][:15]  # noqa: PLR2004
                if outcome.page
                else [],
            }
        )
    return rows


async def read_competitors(
    http: SafeHttpClient, serp: SerpSnapshotData | None, own_hosts: frozenset[str]
) -> dict[str, FetchOutcome]:
    if serp is None:
        return {}
    urls = [r.url for r in serp.organic if r.domain.lower() not in own_hosts][:TOP_N]
    return {o.url: o for o in await fetch_many(http, urls)}


async def link_graph(
    db: AsyncSession, project_id: uuid.UUID, keyword: str, target_url: str | None
) -> tuple[int | None, list[dict[str, str]]]:
    """Inlinks to ``target_url`` and relevant pages that could link to it.

    From the latest completed crawl; ``(None, [])`` when there is none (honest: unknown).
    """
    crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.project_id == project_id, Crawl.status == CrawlStatus.COMPLETED)
            .order_by(desc(Crawl.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if crawl is None:
        return None, []
    inlinks: int | None = None
    linking: set[uuid.UUID] = set()
    if target_url:
        target = await db.execute(
            select(CrawlPage.inlinks).where(
                CrawlPage.crawl_id == crawl.id, CrawlPage.url == target_url
            )
        )
        inlinks = target.scalar_one_or_none()
        linking = set(
            (
                await db.execute(
                    select(CrawlLink.source_page_id).where(
                        CrawlLink.crawl_id == crawl.id, CrawlLink.target_url == target_url
                    )
                )
            ).scalars()
        )
    terms = set(content_terms(words(keyword)))
    if not terms:
        return inlinks, []
    candidates = await db.execute(
        select(CrawlPage.id, CrawlPage.url, CrawlPage.title)
        .where(
            CrawlPage.crawl_id == crawl.id,
            CrawlPage.status_code == 200,  # noqa: PLR2004
            CrawlPage.indexable_google.is_(True),
            CrawlPage.title.is_not(None),
        )
        .order_by(desc(CrawlPage.inlinks))
        .limit(2000)
    )
    suggestions = []
    for page_id, url, title in candidates:
        if url == target_url or page_id in linking:
            continue
        overlap = len(terms & set(words(title or ""))) / len(terms)
        if overlap >= 0.5:  # noqa: PLR2004
            suggestions.append(
                {"url": url, "title": title or "", "relevance": f"{round(overlap * 100)}%"}
            )
        if len(suggestions) >= MAX_LINK_SUGGESTIONS:
            break
    return inlinks, suggestions


async def _load[T: (PageOptimization, ContentBrief)](
    db: AsyncSession, ctx: JobContext, model: type[T]
) -> tuple[T, Project, ProjectMarket]:
    row: T | None = await db.get(model, uuid.UUID(str(ctx.params.get("id"))))
    project = await db.get(Project, ctx.project_id)
    if row is None or project is None or project.deleted_at is not None:
        raise JobFailedError("project_gone", "The project or analysis no longer exists.")
    market = await db.get(ProjectMarket, row.market_id)
    if market is None:
        raise JobFailedError("market_gone", "The market no longer exists.")
    return row, project, market


# ---------------------------------------------------------------------------- jobs
@register_handler(OPTIMIZE_KIND, queue="serp")
async def run_page_optimize(ctx: JobContext) -> dict[str, Any]:
    return await _guarded(ctx, PageOptimization, _page_optimize)


async def _page_optimize(ctx: JobContext) -> dict[str, Any]:
    async with await ctx.session() as db:
        row, project, market = await _load(db, ctx, PageOptimization)
        hosts = frozenset(site_hosts(project.primary_domain))
        http = ctx.runtime.http_factory(EgressPolicy(), ctx.runtime.settings.crawler_user_agent)
        try:
            await ctx.report(progress=0.05, stage="reading your page")
            own = await fetch_page(http, row.url, hosts)
            if own.page is None:
                message = {
                    "robots": "robots.txt blocks SerpTankBot from this page.",
                    "robots_error": "The site's robots.txt returned a server error, "
                    "so we didn't fetch the page.",
                    "unreachable": "The page could not be reached.",
                    "not_html": "The URL is not an HTML page.",
                }.get(own.skipped or "", f"The page returned {own.skipped}.")
                raise JobFailedError("page_unavailable", message)
            await ctx.report(progress=0.2, stage="checking the SERP")
            serp, serp_note = await live_serp(ctx, db, market, row.keyword)
            await ctx.report(progress=0.3, stage="reading ranking pages")
            outcomes = await read_competitors(http, serp, hosts)
        finally:
            await http.aclose()
        pages = [o.page for o in outcomes.values() if o.page]
        intent = classify(row.keyword, serp.features if serp else None)
        inlinks, suggestions = await link_graph(db, project.id, row.keyword, normalize_url(row.url))
        result = analyze(
            own.page,
            row.keyword,
            pages,
            intent=intent.primary,
            language=market.language,
            today=datetime.now(UTC).date(),
            inlinks=inlinks,
            link_suggestions=suggestions,
        )
        own_rank = serp.position_of(hosts) if serp else None
        row.score = result.score
        row.result = {
            **result.to_json(),
            "page": own.page.summary(),
            "intent": {"primary": intent.primary, "reasons": intent.reasons},
            "competitors": competitor_rows(serp, outcomes) if serp else [],
            "serp": {
                "available": serp is not None,
                "note": serp_note,
                "features": list(serp.features) if serp else [],
                "own_position": own_rank.position if own_rank else None,
                "ai_answer": serp.ai_answer is not None if serp else None,
                "ai_cited": serp.cites(hosts) if serp and serp.ai_answer else None,
            },
        }
        row.status = CrawlStatus.COMPLETED
        await db.commit()
        return {"score": result.score, "competitors_read": len(pages)}


@register_handler(BRIEF_KIND, queue="serp")
async def run_content_brief(ctx: JobContext) -> dict[str, Any]:
    return await _guarded(ctx, ContentBrief, _content_brief)


async def _content_brief(ctx: JobContext) -> dict[str, Any]:
    async with await ctx.session() as db:
        row, project, market = await _load(db, ctx, ContentBrief)
        hosts = frozenset(site_hosts(project.primary_domain))
        await ctx.report(progress=0.1, stage="checking the SERP")
        serp, serp_note = await live_serp(ctx, db, market, row.keyword)
        http = ctx.runtime.http_factory(EgressPolicy(), ctx.runtime.settings.crawler_user_agent)
        try:
            await ctx.report(progress=0.3, stage="reading ranking pages")
            outcomes = await read_competitors(http, serp, hosts)
        finally:
            await http.aclose()
        pages = [o.page for o in outcomes.values() if o.page]
        intent = classify(row.keyword, serp.features if serp else None)
        _, links = await link_graph(db, project.id, row.keyword, None)
        brief = build_brief(
            row.keyword,
            serp,
            pages,
            intent=intent.primary,
            intent_reasons=intent.reasons,
            competitors=competitor_rows(serp, outcomes) if serp else [],
            internal_links=links,
        )
        data = brief.to_json()
        if serp_note:
            data["notes"].insert(0, serp_note)
        row.brief = data
        row.status = CrawlStatus.COMPLETED
        await db.commit()
        return {"sections": len(brief.outline), "competitors_read": len(pages)}


async def _guarded(
    ctx: JobContext,
    model: type[PageOptimization] | type[ContentBrief],
    body: Callable[[JobContext], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    """Run ``body``; on any failure mark the analysis row failed (never left "running")."""
    try:
        return await body(ctx)
    except Exception as exc:
        message = exc.message if isinstance(exc, JobFailedError) else "The analysis failed."
        async with await ctx.session() as db:
            await db.execute(
                update(model)
                .where(model.id == uuid.UUID(str(ctx.params.get("id"))))
                .values(status=CrawlStatus.FAILED, error=message[:200])
            )
            await db.commit()
        raise
