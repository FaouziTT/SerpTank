"""On-page API under ``/orgs/{org}/projects/{project}``.

Routes: optimizer, briefs, cannibalization, keyword-map.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.errors import AppError, ConflictError, NotFoundError
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.billing.entitlements import plan_of
from serptank.modules.crawler.models import CrawlStatus
from serptank.modules.crawler.urls import is_internal, normalize_url, site_hosts
from serptank.modules.identity.deps import DbSession
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.llm.gateway import LlmGateway
from serptank.modules.onpage import mapping
from serptank.modules.onpage.brief import to_markdown
from serptank.modules.onpage.models import ContentBrief, PageOptimization
from serptank.modules.onpage.schemas import (
    AnalysisSummary,
    BriefOut,
    BriefRequest,
    BriefStarted,
    CannibalizationOut,
    CannibalizationReport,
    KeywordMapRow,
    OptimizationOut,
    OptimizationStarted,
    OptimizationSummary,
    OptimizeRequest,
    RewriteSuggestion,
    TargetUpdate,
)
from serptank.modules.onpage.service import BRIEF_KIND, OPTIMIZE_KIND
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.projects.router import ProjectRepository
from serptank.modules.search_data.models import TrackedKeyword
from serptank.modules.search_data.schema import normalize_query
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects/{project_id}", tags=["on-page"])
ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
_START_RATE = rate_limit("onpage-start", Rate(60, 3600))
_REWRITE_RATE = rate_limit("onpage-rewrite", Rate(30, 3600))
MAX_LISTED = 100

REWRITE_INSTRUCTION = (
    "Suggest an improved title (max 60 characters), meta description (max 155 characters) "
    "and H1 for the page described below so it better matches the target keyword and "
    "search intent, plus up to 8 section headings the page is missing and up to 5 short "
    "notes. Stay factual: do not invent claims, prices, statistics or awards that the "
    "page data doesn't support. Write in the page's language."
)


class InvalidPageUrlError(AppError):
    status = 422
    code = "invalid_page_url"
    title = "The URL must be a page on this project's domain"


async def _project(db: AsyncSession, ctx: OrgContext, project_id: uuid.UUID) -> Project:
    return await ProjectRepository(db, ctx.organization_id).get(project_id)


async def _market(db: AsyncSession, project: Project, market_id: uuid.UUID) -> ProjectMarket:
    market = await db.get(ProjectMarket, market_id)
    if market is None or market.project_id != project.id:
        raise NotFoundError("Market not found.")
    return market


def _page_url(project: Project, raw: str) -> str:
    url = normalize_url(raw)
    if url is None or not is_internal(url, site_hosts(project.primary_domain)):
        raise InvalidPageUrlError(f"Use a URL on {project.primary_domain}.")
    return url


async def _start(
    db: AsyncSession, request: Request, ctx: OrgContext, project: Project, kind: str, row: Any
) -> JobOut:
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=kind,
        project_id=project.id,
        user_id=ctx.actor_user_id,
        params={"id": str(row.id)},
    )
    row.job_id = job.id
    db.add(row)
    await db.commit()
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return JobOut.model_validate(job)


# ----------------------------------------------------------------------- optimizer
@router.post(
    "/optimizer",
    response_model=OptimizationStarted,
    status_code=202,
    dependencies=[Depends(_START_RATE)],
)
async def start_optimization(
    project_id: uuid.UUID, body: OptimizeRequest, ctx: ProjectWrite, db: DbSession, request: Request
) -> OptimizationStarted:
    project = await _project(db, ctx, project_id)
    market = await _market(db, project, body.market_id)
    keyword = normalize_query(body.keyword)
    if not keyword:
        raise InvalidPageUrlError("Enter a keyword.")
    row = PageOptimization(
        id=uuid.uuid4(),
        organization_id=ctx.organization_id,
        project_id=project.id,
        market_id=market.id,
        keyword=keyword,
        url=_page_url(project, body.url),
        status=CrawlStatus.RUNNING,
        result={},
    )
    job = await _start(db, request, ctx, project, OPTIMIZE_KIND, row)
    await db.refresh(row)
    return OptimizationStarted(optimization=OptimizationSummary.model_validate(row), job=job)


@router.get("/optimizer", response_model=list[OptimizationSummary])
async def list_optimizations(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[OptimizationSummary]:
    project = await _project(db, ctx, project_id)
    rows = await db.execute(
        select(PageOptimization)
        .where(PageOptimization.project_id == project.id)
        .order_by(desc(PageOptimization.created_at))
        .limit(MAX_LISTED)
    )
    return [OptimizationSummary.model_validate(r) for r in rows.scalars()]


async def _optimization(
    db: AsyncSession, project: Project, optimization_id: uuid.UUID
) -> PageOptimization:
    row = await db.get(PageOptimization, optimization_id)
    if row is None or row.project_id != project.id:
        raise NotFoundError("Analysis not found.")
    return row


@router.get("/optimizer/{optimization_id}", response_model=OptimizationOut)
async def get_optimization(
    project_id: uuid.UUID, optimization_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> OptimizationOut:
    project = await _project(db, ctx, project_id)
    return OptimizationOut.model_validate(await _optimization(db, project, optimization_id))


@router.post(
    "/optimizer/{optimization_id}/rewrite",
    response_model=OptimizationOut,
    dependencies=[Depends(_REWRITE_RATE)],
)
async def suggest_rewrite(
    project_id: uuid.UUID,
    optimization_id: uuid.UUID,
    ctx: ProjectWrite,
    db: DbSession,
    request: Request,
) -> OptimizationOut:
    """Optional AI rewrite of title/meta/H1, grounded in the stored analysis."""
    project = await _project(db, ctx, project_id)
    row = await _optimization(db, project, optimization_id)
    if row.status != CrawlStatus.COMPLETED:
        raise ConflictError("Wait for the analysis to finish first.")
    result = row.result
    page = result.get("page", {})
    gaps = [c for c in result.get("checks", []) if c.get("id") == "topic_coverage"]
    missing = gaps[0].get("detail", {}).get("missing", [])[:15] if gaps else []
    content = "\n".join(
        [
            f"Target keyword: {row.keyword}",
            f"Search intent: {result.get('intent', {}).get('primary', 'unknown')}",
            f"Current title: {page.get('title') or '(none)'}",
            f"Current meta description: {page.get('meta_description') or '(none)'}",
            f"Current H1: {'; '.join(page.get('h1', [])) or '(none)'}",
            "Current headings: " + "; ".join(h[1] for h in page.get("headings", [])[:25]),
            "Subtopics ranking pages cover that this page lacks: " + ", ".join(missing),
            "Ranking page titles: "
            + "; ".join(c.get("title", "") for c in result.get("competitors", [])[:10]),
        ]
    )
    gateway: LlmGateway = request.app.state.job_runtime.extras["llm"]
    suggestion = await gateway.structured(
        db,
        organization_id=ctx.organization_id,
        monthly_token_budget=plan_of(ctx.organization).llm_tokens_per_month,
        purpose="onpage_rewrite",
        instruction=REWRITE_INSTRUCTION,
        content=content,
        output=RewriteSuggestion,
    )
    row.rewrite = {**suggestion.model_dump(), "generated_by": "ai"}
    await db.commit()
    await db.refresh(row)
    return OptimizationOut.model_validate(row)


# -------------------------------------------------------------------------- briefs
@router.post(
    "/briefs", response_model=BriefStarted, status_code=202, dependencies=[Depends(_START_RATE)]
)
async def start_brief(
    project_id: uuid.UUID, body: BriefRequest, ctx: ProjectWrite, db: DbSession, request: Request
) -> BriefStarted:
    project = await _project(db, ctx, project_id)
    market = await _market(db, project, body.market_id)
    keyword = normalize_query(body.keyword)
    if not keyword:
        raise InvalidPageUrlError("Enter a keyword.")
    row = ContentBrief(
        id=uuid.uuid4(),
        organization_id=ctx.organization_id,
        project_id=project.id,
        market_id=market.id,
        keyword=keyword,
        status=CrawlStatus.RUNNING,
        brief={},
    )
    job = await _start(db, request, ctx, project, BRIEF_KIND, row)
    await db.refresh(row)
    return BriefStarted(brief=AnalysisSummary.model_validate(row), job=job)


@router.get("/briefs", response_model=list[AnalysisSummary])
async def list_briefs(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[AnalysisSummary]:
    project = await _project(db, ctx, project_id)
    rows = await db.execute(
        select(ContentBrief)
        .where(ContentBrief.project_id == project.id)
        .order_by(desc(ContentBrief.created_at))
        .limit(MAX_LISTED)
    )
    return [AnalysisSummary.model_validate(r) for r in rows.scalars()]


async def _brief(db: AsyncSession, project: Project, brief_id: uuid.UUID) -> ContentBrief:
    row = await db.get(ContentBrief, brief_id)
    if row is None or row.project_id != project.id:
        raise NotFoundError("Brief not found.")
    return row


@router.get("/briefs/{brief_id}", response_model=BriefOut)
async def get_brief(
    project_id: uuid.UUID, brief_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> BriefOut:
    project = await _project(db, ctx, project_id)
    return BriefOut.model_validate(await _brief(db, project, brief_id))


@router.get("/briefs/{brief_id}/markdown", response_class=Response)
async def export_brief(
    project_id: uuid.UUID, brief_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> Response:
    project = await _project(db, ctx, project_id)
    row = await _brief(db, project, brief_id)
    if row.status != CrawlStatus.COMPLETED:
        raise ConflictError("The brief isn't ready yet.")
    return Response(
        to_markdown(row.brief),
        media_type="text/markdown; charset=utf-8",
        headers={
            "content-disposition": f'attachment; filename="brief-{row.id}.md"',
            "cache-control": "no-store",
        },
    )


# ---------------------------------------------------------- mapping & cannibalization
@router.get("/cannibalization", response_model=CannibalizationReport)
async def get_cannibalization(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> CannibalizationReport:
    project = await _project(db, ctx, project_id)
    issues, has_data = await mapping.cannibalization(db, project.id)
    return CannibalizationReport(
        has_search_console_data=has_data,
        window_days=mapping.WINDOW_DAYS,
        issues=[CannibalizationOut.model_validate(asdict(i)) for i in issues],
    )


@router.get("/keyword-map", response_model=list[KeywordMapRow])
async def get_keyword_map(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[KeywordMapRow]:
    project = await _project(db, ctx, project_id)
    return [
        KeywordMapRow.model_validate(asdict(r)) for r in await mapping.keyword_map(db, project.id)
    ]


@router.put("/keyword-map/{keyword_id}", status_code=204)
async def set_target_page(
    project_id: uuid.UUID,
    keyword_id: uuid.UUID,
    body: TargetUpdate,
    ctx: ProjectWrite,
    db: DbSession,
) -> None:
    project = await _project(db, ctx, project_id)
    keyword = await db.get(TrackedKeyword, keyword_id)
    if keyword is None or keyword.project_id != project.id:
        raise NotFoundError("Keyword not found.")
    keyword.target_url = _page_url(project, body.target_url) if body.target_url else None
    await db.commit()
