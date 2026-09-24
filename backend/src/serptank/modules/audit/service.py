"""Build a :class:`Site` from a stored crawl, evaluate it, persist findings and scores."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.models import uuid7
from serptank.modules.audit.evaluate import AuditResult, evaluate
from serptank.modules.audit.models import AuditIssue
from serptank.modules.audit.site import Page, Site
from serptank.modules.crawler.models import Crawl, CrawlLink, CrawlPage
from serptank.modules.crawler.urls import host_of, site_hosts

BATCH = 500


async def load_site(db: AsyncSession, crawl: Crawl) -> Site:
    rows = (await db.execute(select(CrawlPage).where(CrawlPage.crawl_id == crawl.id))).scalars()
    pages = {
        row.url: Page(
            id=row.id,
            url=row.url,
            depth=row.depth,
            found_via=row.found_via,
            status_code=row.status_code,
            error=row.error,
            content_type=row.content_type,
            response_ms=row.response_ms,
            bytes=row.bytes,
            redirect_to=row.redirect_to,
            in_sitemap=row.in_sitemap,
            allowed_google=row.allowed_google,
            allowed_bing=row.allowed_bing,
            x_robots=list(row.x_robots or []),
            data=dict(row.data or {}),
            content_hash=row.content_hash,
            simhash=row.simhash,
            rendered=row.rendered,
            mobile=row.mobile,
        )
        for row in rows
    }
    by_id = {p.id: p.url for p in pages.values()}
    inbound: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    link_rows = await db.execute(
        select(CrawlLink.source_page_id, CrawlLink.target_url, CrawlLink.nofollow).where(
            CrawlLink.crawl_id == crawl.id, CrawlLink.internal.is_(True)
        )
    )
    for source_id, target, nofollow in link_rows:
        source = by_id.get(source_id)
        if source is not None and source != target:
            inbound[target].append((source, nofollow))
    for url, sources in inbound.items():
        page = pages.get(url)
        if page is not None:
            page.inlinks = len({s for s, nofollow in sources if not nofollow})
    start = crawl.start_url
    return Site(
        start_url=start,
        hosts=site_hosts(host_of(start)),
        engines=frozenset(crawl.engines),
        pages=pages,
        inbound=inbound,
        site=dict(crawl.site or {}),
        budget_exhausted=crawl.budget_exhausted,
        domain_verified=crawl.domain_verified,
        render_available=crawl.render_available,
    )


async def run_audit(db: AsyncSession, crawl: Crawl) -> AuditResult:
    """Evaluate the crawl and store issues, scores and per-page flags (caller commits)."""
    site = await load_site(db, crawl)
    result = evaluate(site)
    rows: list[dict[str, object]] = []
    for rule_result in result.results:
        for finding in rule_result.findings:
            rows.append(
                {
                    "id": uuid7(),
                    "organization_id": crawl.organization_id,
                    "crawl_id": crawl.id,
                    "rule_id": rule_result.rule.id,
                    "severity": rule_result.rule.severity,
                    "scope": rule_result.rule.scope,
                    "url": finding.url,
                    "details": finding.details,
                }
            )
    for start in range(0, len(rows), BATCH):
        await db.execute(insert(AuditIssue), rows[start : start + BATCH])
    # Persist derived per-page facts used by page listings and later modules
    # (bulk UPDATE by primary key: one round trip per batch).
    updates = [
        {
            "id": page.id,
            "inlinks": page.inlinks,
            "indexable_google": page.indexable("googlebot"),
            "indexable_bing": page.indexable("bingbot"),
        }
        for page in site.pages.values()
        if page.is_html or page.inlinks
    ]
    for start in range(0, len(updates), BATCH):
        await db.execute(update(CrawlPage), updates[start : start + BATCH])
    crawl.score = result.scores.get("google")
    crawl.issue_counts = result.counts
    crawl.finished_at = datetime.now(UTC)
    return result


async def issue_totals(db: AsyncSession, crawl_id: uuid.UUID) -> dict[str, int]:
    rows = await db.execute(
        select(AuditIssue.rule_id, func.count())
        .where(AuditIssue.crawl_id == crawl_id)
        .group_by(AuditIssue.rule_id)
    )
    return {rule_id: int(count) for rule_id, count in rows}
