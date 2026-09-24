"""Crawl orchestration: budgets, starting crawls, and the ``crawl`` job handler.

Pipeline (one job): crawl -> mobile/JS samples -> audit -> scores. Each stage reports
progress; a cancelled job stops at the next report and the crawl is marked cancelled.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.http import EgressPolicy
from serptank.core.models import uuid7
from serptank.modules.audit.service import run_audit
from serptank.modules.billing.entitlements import PlanLimitError, plan_for
from serptank.modules.crawler.engine import (
    CrawlAbortedError,
    CrawlConfig,
    Crawler,
    CrawlSummary,
    PageRecord,
)
from serptank.modules.crawler.models import Crawl, CrawlLink, CrawlPage, CrawlStatus
from serptank.modules.crawler.parser import Link
from serptank.modules.crawler.rendering import RendererClient, render_summary
from serptank.modules.crawler.robots import BINGBOT, GOOGLEBOT
from serptank.modules.crawler.similarity import to_signed
from serptank.modules.crawler.urls import host_of, is_internal, site_hosts
from serptank.modules.jobs.service import (
    JobCancelledError,
    JobContext,
    JobFailedError,
    register_handler,
)
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

JOB_KIND = "crawl"
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Mobile Safari/537.36 SerpTankBot/1.0 (+https://serptank.com/bot)"
)
FLUSH_EVERY = 100
PROGRESS_EVERY_S = 2.0
MAX_SITEMAP_HREFLANG = 5000


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def pages_used_this_month(db: AsyncSession, organization_id: uuid.UUID) -> int:
    used = await db.execute(
        select(func.coalesce(func.sum(Crawl.pages_fetched), 0)).where(
            Crawl.organization_id == organization_id, Crawl.created_at >= month_start()
        )
    )
    return int(used.scalar_one())


async def crawl_budget(
    db: AsyncSession,
    organization: Organization,
    project: Project,
    settings_max: int,
    unverified_max: int,
) -> int:
    """Pages this crawl may fetch: plan budget left this month, capped per crawl."""
    plan = plan_for(organization.plan_code)
    left = plan.max_crawl_pages_per_month - await pages_used_this_month(db, organization.id)
    if left <= 0:
        raise PlanLimitError(
            f"Your {plan.name} plan's monthly crawl budget "
            f"({plan.max_crawl_pages_per_month:,} pages) is used up.",
            extra={"limit": plan.max_crawl_pages_per_month, "resource": "crawl pages per month"},
        )
    cap = settings_max if project.domain_verified_at else unverified_max
    return min(left, cap)


class DbSink:
    """Persists crawl output in batches (bounded memory, few round trips)."""

    def __init__(
        self, ctx: JobContext, crawl: Crawl, summary: CrawlSummary, hosts: frozenset[str]
    ) -> None:
        self.ctx = ctx
        self.crawl = crawl
        self.summary = summary
        self.hosts = hosts
        self.pages: list[dict[str, Any]] = []
        self.link_rows: list[dict[str, Any]] = []
        self.raw_links: dict[str, set[str]] = {}
        self.page_ids: dict[str, uuid.UUID] = {}

    async def page(self, record: PageRecord) -> None:
        data = record.data
        self.page_ids[record.url] = record.id
        self.pages.append(
            {
                "id": record.id,
                "organization_id": self.crawl.organization_id,
                "crawl_id": self.crawl.id,
                "url": record.url,
                "depth": record.depth,
                "found_via": record.found_via,
                "status_code": record.status_code,
                "error": record.error,
                "content_type": (record.content_type or "")[:100] or None,
                "response_ms": record.response_ms,
                "bytes": record.bytes,
                "redirect_to": record.redirect_to,
                "in_sitemap": record.url in self.summary.sitemap_urls,
                "allowed_google": record.allowed.get(GOOGLEBOT, True),
                "allowed_bing": record.allowed.get(BINGBOT, True),
                "title": (data.title or "")[:500] if data else None,
                "canonical": data.canonicals[0] if data and data.canonicals else None,
                "word_count": data.word_count if data else None,
                "content_hash": data.content_hash if data else None,
                "simhash": to_signed(data.simhash) if data else None,
                "x_robots": record.x_robots,
                "data": (data.to_json() | {"headers": record.headers})
                if data
                else {"headers": record.headers},
            }
        )
        if len(self.pages) >= FLUSH_EVERY:
            await self.flush()

    async def links(self, source: PageRecord, links: list[Link]) -> None:
        internal = set()
        for link in links:
            is_int = is_internal(link.url, self.hosts)
            if is_int:
                internal.add(link.url)
            self.link_rows.append(
                {
                    "id": uuid7(),
                    "organization_id": self.crawl.organization_id,
                    "crawl_id": self.crawl.id,
                    "source_page_id": source.id,
                    "target_url": link.url,
                    "internal": is_int,
                    "nofollow": link.nofollow,
                    "anchor": link.anchor[:200],
                }
            )
        self.raw_links[source.url] = internal

    async def flush(self) -> None:
        if not self.pages and not self.link_rows:
            return
        async with await self.ctx.session() as db:
            if self.pages:
                await db.execute(insert(CrawlPage), self.pages)
            if self.link_rows:
                # Links reference pages by id; pages of this batch were inserted above.
                await db.execute(insert(CrawlLink), self.link_rows)
            await db.commit()
        self.pages, self.link_rows = [], []


async def _project_context(ctx: JobContext) -> tuple[Organization, Project, list[str]]:
    async with await ctx.session() as db:
        org = await db.get(Organization, ctx.organization_id)
        project = (
            await db.execute(
                select(Project).where(
                    Project.id == ctx.project_id,
                    Project.organization_id == ctx.organization_id,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if org is None or project is None:
            raise JobFailedError("project_gone", "The project no longer exists.")
        engines = (
            await db.execute(
                select(ProjectMarket.search_engines).where(ProjectMarket.project_id == project.id)
            )
        ).scalars()
        tracked = sorted({str(e) for market in engines for e in market})
        return org, project, tracked


@register_handler(JOB_KIND, queue="crawl")
async def run_crawl(ctx: JobContext) -> dict[str, Any]:
    settings = ctx.runtime.settings
    org, project, engines = await _project_context(ctx)
    async with await ctx.session() as db:
        try:
            max_pages = await crawl_budget(
                db,
                org,
                project,
                settings.crawl_max_pages_per_crawl,
                settings.crawl_max_pages_unverified,
            )
        except PlanLimitError as exc:
            raise JobFailedError(
                "crawl_budget_exhausted", exc.detail or "Crawl budget used up."
            ) from exc
        crawl = Crawl(
            id=uuid7(),
            organization_id=org.id,
            project_id=project.id,
            job_id=ctx.job_id,
            status=CrawlStatus.RUNNING,
            start_url=f"https://{project.primary_domain}/",
            max_pages=max_pages,
            domain_verified=project.domain_verified_at is not None,
            engines=engines,
            render_available=bool(ctx.runtime.extras.get("renderer")),
        )
        db.add(crawl)
        await db.commit()
    try:
        return await _run(ctx, crawl, max_pages)
    except JobCancelledError:
        await _close_crawl(ctx, crawl.id, CrawlStatus.CANCELLED)
        raise
    except BaseException:
        await _close_crawl(ctx, crawl.id, CrawlStatus.FAILED)
        raise


async def _close_crawl(ctx: JobContext, crawl_id: uuid.UUID, status: CrawlStatus) -> None:
    async with await ctx.session() as db:
        await db.execute(
            update(Crawl)
            .where(Crawl.id == crawl_id)
            .values(status=status, finished_at=datetime.now(UTC))
        )
        await db.commit()


async def _run(ctx: JobContext, crawl: Crawl, max_pages: int) -> dict[str, Any]:
    settings = ctx.runtime.settings
    hosts = site_hosts(host_of(crawl.start_url))
    http = ctx.runtime.http_factory(EgressPolicy(), settings.crawler_user_agent)
    last_report = [0.0]

    async def progress(summary: CrawlSummary) -> None:
        if time.monotonic() - last_report[0] < PROGRESS_EVERY_S:
            return
        last_report[0] = time.monotonic()
        await sink.flush()
        await ctx.report(
            progress=0.8 * min(1.0, summary.pages_fetched / max(1, max_pages)),
            stage="crawling",
            counters={"pages_fetched": summary.pages_fetched, "max_pages": max_pages},
        )

    summary_state = CrawlSummary()
    sink = DbSink(ctx, crawl, summary_state, hosts)
    crawler = Crawler(
        http,
        CrawlConfig(
            start_url=crawl.start_url,
            hosts=hosts,
            max_pages=max_pages,
            max_depth=settings.crawl_max_depth,
            min_delay_s=settings.crawl_min_delay_s,
            concurrency=settings.crawl_concurrency,
            mobile_user_agent=MOBILE_UA,
            mobile_sample=settings.crawl_mobile_sample,
        ),
        sink,
        progress=progress,
        summary=summary_state,
    )
    await ctx.report(
        progress=0.0, stage="crawling", counters={"pages_fetched": 0, "max_pages": max_pages}
    )
    try:
        summary = await crawler.run()
    except CrawlAbortedError as exc:
        await sink.flush()
        raise JobFailedError(exc.code, exc.message) from exc
    finally:
        await http.aclose()
    await sink.flush()

    # JS rendering sample (only if the isolated renderer is configured).
    rendered: dict[str, dict[str, Any]] = {}
    renderer: RendererClient | None = ctx.runtime.extras.get("renderer")
    if renderer is not None and settings.render_sample > 0:
        robots = crawler.robots_rules()
        sample = crawler.html_pages[: settings.render_sample]
        for index, url in enumerate(sample):
            await ctx.report(
                progress=0.8 + 0.1 * index / max(1, len(sample)),
                stage="rendering",
                counters={"pages_fetched": summary.pages_fetched, "rendered": index},
            )
            result = await renderer.render(url, user_agent=settings.crawler_user_agent)
            rendered[url] = render_summary(
                url, sink.raw_links.get(url, set()), result, robots, hosts
            )

    await ctx.report(
        progress=0.92, stage="auditing", counters={"pages_fetched": summary.pages_fetched}
    )
    async with await ctx.session() as db:
        page_updates = [
            {"id": sink.page_ids[url], "rendered": value}
            for url, value in rendered.items()
            if url in sink.page_ids
        ] + [
            {"id": sink.page_ids[url], "mobile": value}
            for url, value in summary.mobile.items()
            if url in sink.page_ids
        ]
        for item in page_updates:
            await db.execute(update(CrawlPage), [item])
        stored = await db.get(Crawl, crawl.id)
        if stored is None:  # deleted with its project mid-run
            raise JobFailedError("project_gone", "The project no longer exists.")
        stored.pages_fetched = summary.pages_fetched
        stored.pages_discovered = summary.pages_discovered
        stored.budget_exhausted = summary.budget_exhausted
        stored.site = {
            "robots": summary.robots,
            "sitemaps": summary.sitemaps,
            "sitemap_url_count": len(summary.sitemap_urls),
            "sitemap_hreflang": dict(list(summary.sitemap_hreflang.items())[:MAX_SITEMAP_HREFLANG]),
            "soft404_probe": summary.soft404_probe,
            "https_redirect": summary.https_redirect,
            "rendered_pages": len(rendered),
            "mobile_pages": len(summary.mobile),
        }
        await db.flush()
        audit = await run_audit(db, stored)
        stored.status = CrawlStatus.COMPLETED
        await db.commit()
    return {
        "crawl_id": str(crawl.id),
        "score": audit.scores.get("google"),
        "pages_fetched": summary.pages_fetched,
        "issues": sum(r.affected for r in audit.results),
    }
