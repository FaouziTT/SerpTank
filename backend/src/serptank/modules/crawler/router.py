"""Technical audit API: ``/api/v1/orgs/{org_id}/projects/{project_id}/crawls``."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import ColumnElement, Select, func, or_, select

from serptank.core.errors import NotFoundError
from serptank.core.ratelimit import Rate, rate_limit
from serptank.core.repository import TenantRepository
from serptank.modules.audit.evaluate import SITE_LEVEL_RULES
from serptank.modules.audit.models import AuditIssue
from serptank.modules.audit.rules import CATEGORIES, RULES
from serptank.modules.audit.scoring import priority
from serptank.modules.billing.entitlements import plan_for
from serptank.modules.crawler.models import Crawl, CrawlPage
from serptank.modules.crawler.schemas import (
    CrawlOut,
    CrawlStarted,
    CrawlUsage,
    IssueOccurrence,
    IssuePage,
    IssueSummary,
    PageList,
    PageOut,
)
from serptank.modules.crawler.service import JOB_KIND, crawl_budget, pages_used_this_month
from serptank.modules.identity.deps import DbSession
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.router import ProjectRepository
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects/{project_id}/crawls", tags=["audit"])

ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
_START_RATE = rate_limit("crawl-start", Rate(10, 3600))
EXAMPLES = 5


class CrawlRepository(TenantRepository[Crawl]):
    model = Crawl
    not_found_message = "Audit not found."


async def _crawl(
    db: DbSession, ctx: OrgContext, project_id: uuid.UUID, crawl_id: uuid.UUID
) -> Crawl:
    crawl = await CrawlRepository(db, ctx.organization_id).get(crawl_id)
    if crawl.project_id != project_id:
        raise NotFoundError("Audit not found.")
    return crawl


@router.get("/usage", response_model=CrawlUsage)
async def crawl_usage(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession, request: Request
) -> CrawlUsage:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    settings = request.app.state.settings
    plan = plan_for(ctx.organization.plan_code)
    used = await pages_used_this_month(db, ctx.organization_id)
    cap = (
        settings.crawl_max_pages_per_crawl
        if project.domain_verified_at
        else settings.crawl_max_pages_unverified
    )
    return CrawlUsage(
        pages_used_this_month=used,
        pages_per_month=plan.max_crawl_pages_per_month,
        max_pages_next_crawl=max(0, min(cap, plan.max_crawl_pages_per_month - used)),
        domain_verified=project.domain_verified_at is not None,
    )


@router.post("", response_model=CrawlStarted, status_code=202, dependencies=[Depends(_START_RATE)])
async def start_crawl(
    project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession, request: Request
) -> CrawlStarted:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    settings = request.app.state.settings
    budget = await crawl_budget(
        db,
        ctx.organization,
        project,
        settings.crawl_max_pages_per_crawl,
        settings.crawl_max_pages_unverified,
    )
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=JOB_KIND,
        project_id=project.id,
        user_id=ctx.actor_user_id,
    )
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return CrawlStarted(job=JobOut.model_validate(job), pages_budget=budget)


@router.get("", response_model=list[CrawlOut])
async def list_crawls(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[Crawl]:
    await ProjectRepository(db, ctx.organization_id).get(project_id)
    rows = await db.execute(
        select(Crawl)
        .where(Crawl.organization_id == ctx.organization_id, Crawl.project_id == project_id)
        .order_by(Crawl.created_at.desc())
        .limit(limit)
    )
    return list(rows.scalars())


@router.get("/{crawl_id}", response_model=CrawlOut)
async def get_crawl(
    project_id: uuid.UUID, crawl_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> Crawl:
    return await _crawl(db, ctx, project_id, crawl_id)


@router.get("/{crawl_id}/issues", response_model=list[IssueSummary])
async def list_issues(
    project_id: uuid.UUID,
    crawl_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    engine: Annotated[str, Query(max_length=20)] = "google",
) -> list[IssueSummary]:
    """Issues grouped by rule, highest priority first. ``engine`` selects the lens:
    baseline rules always apply; engine-specific deltas only for that engine."""
    crawl = await _crawl(db, ctx, project_id, crawl_id)
    counts = await db.execute(
        select(AuditIssue.rule_id, func.count(func.distinct(func.coalesce(AuditIssue.url, ""))))
        .where(AuditIssue.crawl_id == crawl.id, AuditIssue.scope.in_(["all", engine]))
        .group_by(AuditIssue.rule_id)
    )
    affected = {rule_id: int(n) for rule_id, n in counts}
    examples: dict[str, list[str]] = defaultdict(list)
    if affected:
        ranked = (
            select(
                AuditIssue.rule_id,
                AuditIssue.url,
                func.row_number()
                .over(partition_by=AuditIssue.rule_id, order_by=AuditIssue.id)
                .label("n"),
            )
            .where(AuditIssue.crawl_id == crawl.id, AuditIssue.url.is_not(None))
            .subquery()
        )
        for rule_id, url in await db.execute(
            select(ranked.c.rule_id, ranked.c.url).where(ranked.c.n <= EXAMPLES)
        ):
            examples[rule_id].append(url)
    total_pages = int(crawl.issue_counts.get("pages_audited", 0)) or 1
    out: list[IssueSummary] = []
    for rule_id, count in affected.items():
        rule = RULES.get(rule_id)
        if rule is None:
            continue  # rule retired since this audit ran
        site_level = not examples.get(rule_id) or rule_id in SITE_LEVEL_RULES
        out.append(
            IssueSummary(
                rule_id=rule.id,
                title=rule.title,
                category=rule.category,
                category_label=CATEGORIES[rule.category],
                severity=rule.severity,
                scope=rule.scope,
                description=rule.description,
                fix=rule.fix,
                reference=rule.reference,
                effort=rule.effort,
                affected=count,
                priority=priority(rule, site_level, count, total_pages),
                examples=examples.get(rule_id, []),
            )
        )
    out.sort(key=lambda i: (-i.priority, i.rule_id))
    return out


@router.get("/{crawl_id}/issues/{rule_id}", response_model=IssuePage)
async def issue_detail(
    project_id: uuid.UUID,
    crawl_id: uuid.UUID,
    rule_id: Annotated[str, Path(max_length=80)],
    ctx: ProjectRead,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> IssuePage:
    crawl = await _crawl(db, ctx, project_id, crawl_id)
    base = select(AuditIssue).where(AuditIssue.crawl_id == crawl.id, AuditIssue.rule_id == rule_id)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = await db.execute(
        base.order_by(AuditIssue.url, AuditIssue.id).limit(limit).offset(offset)
    )
    return IssuePage(
        rule_id=rule_id,
        total=total,
        items=[IssueOccurrence(url=r.url, details=r.details) for r in rows.scalars()],
    )


PageFilter = Literal["all", "html", "indexable", "non_indexable", "redirects", "errors", "blocked"]


_PAGE_FILTERS: dict[str, Callable[[], tuple[ColumnElement[bool], ...]]] = {
    "html": lambda: (CrawlPage.status_code == 200, CrawlPage.content_type.like("%html%")),  # noqa: PLR2004
    "indexable": lambda: (CrawlPage.indexable_google.is_(True),),
    "non_indexable": lambda: (CrawlPage.indexable_google.is_(False),),
    "redirects": lambda: (CrawlPage.status_code.between(300, 399),),
    "errors": lambda: (or_(CrawlPage.status_code >= 400, CrawlPage.error.is_not(None)),),  # noqa: PLR2004
    "blocked": lambda: (CrawlPage.error == "blocked_by_robots",),
}


def _page_filter(stmt: Select[tuple[CrawlPage]], kind: PageFilter) -> Select[tuple[CrawlPage]]:
    conditions = _PAGE_FILTERS.get(kind)
    return stmt.where(*conditions()) if conditions else stmt


@router.get("/{crawl_id}/pages", response_model=PageList)
async def list_pages(
    project_id: uuid.UUID,
    crawl_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    kind: PageFilter = "all",
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> PageList:
    crawl = await _crawl(db, ctx, project_id, crawl_id)
    stmt = _page_filter(select(CrawlPage).where(CrawlPage.crawl_id == crawl.id), kind)
    if q:
        # Literal substring match (escape LIKE wildcards in user input).
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(CrawlPage.url.ilike(f"%{escaped}%", escape="\\"))
    total = int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
    rows = await db.execute(
        stmt.order_by(CrawlPage.depth.asc().nulls_last(), CrawlPage.url).limit(limit).offset(offset)
    )
    return PageList(total=total, items=[PageOut.model_validate(p) for p in rows.scalars()])
