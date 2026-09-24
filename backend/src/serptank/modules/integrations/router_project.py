"""Project data sources and indexing: ``/api/v1/orgs/{org_id}/projects/{project_id}/...``."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, desc, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.audit import record_audit_event
from serptank.core.errors import AppError, ConflictError, NotFoundError
from serptank.core.models import uuid7
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.crawler.urls import site_hosts
from serptank.modules.identity.deps import DbSession, Identity
from serptank.modules.integrations.credentials import (
    bing_api_key,
    google_access_token,
)
from serptank.modules.integrations.csv_import import CsvImportError, parse_ai_csv
from serptank.modules.integrations.indexing import (
    clean_urls,
    indexnow_source,
    require_verified,
    submit_bing,
    submit_indexnow,
)
from serptank.modules.integrations.models import (
    AiPerformanceDaily,
    BingDaily,
    GscDaily,
    IndexNowSubmission,
    ProjectSource,
    SourceKind,
    UrlInspection,
)
from serptank.modules.integrations.providers import indexnow
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.bing import BingWebmasterClient
from serptank.modules.integrations.providers.crux import assess
from serptank.modules.integrations.providers.ga4 import Ga4Client
from serptank.modules.integrations.providers.google_oauth import SCOPES
from serptank.modules.integrations.providers.gsc import GscClient
from serptank.modules.integrations.router_org import provider_problem
from serptank.modules.integrations.schemas import (
    AiSurfaceTotals,
    ImportOut,
    IndexNowSettings,
    InspectionOut,
    InspectRequest,
    MetricRow,
    PerformanceOut,
    SitemapSubmit,
    SourceLink,
    SourceOut,
    SubmissionOut,
    UrlList,
    VitalsOut,
)
from serptank.modules.integrations.sync import SYNC_KINDS, latest_vitals
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.projects.models import Project
from serptank.modules.projects.router import ProjectRepository
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects/{project_id}", tags=["integrations"])

ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
IntegrationsManage = Annotated[OrgContext, Depends(org_access(Permission.INTEGRATIONS_MANAGE))]
_SUBMIT_RATE = rate_limit("indexing-submit", Rate(30, 3600))
_INSPECT_RATE = rate_limit("url-inspect", Rate(60, 3600))  # GSC allows 2,000/day per site
_IMPORT_RATE = rate_limit("csv-import", Rate(20, 3600))
LinkableKind = Literal["gsc", "ga4", "bing"]


class ImportRejectedError(AppError):
    status = 422
    code = "import_rejected"
    title = "The file couldn't be imported"


async def _project(db: AsyncSession, ctx: OrgContext, project_id: uuid.UUID) -> Project:
    return await ProjectRepository(db, ctx.organization_id).get(project_id)


async def _source(
    db: AsyncSession, project_id: uuid.UUID, kind: SourceKind
) -> ProjectSource | None:
    return (
        await db.execute(
            select(ProjectSource).where(
                ProjectSource.project_id == project_id, ProjectSource.kind == kind
            )
        )
    ).scalar_one_or_none()


def _gsc_matches(site_url: str, domain: str) -> bool:
    hosts = site_hosts(domain)
    if site_url.startswith("sc-domain:"):
        return site_url.removeprefix("sc-domain:").lower() in {
            h.removeprefix("www.") for h in hosts
        }
    host = site_url.split("://", 1)[-1].split("/", 1)[0].lower()
    return host in hosts


# -------------------------------------------------------------------------- sources
@router.get("/sources", response_model=list[SourceOut])
async def list_sources(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[ProjectSource]:
    await _project(db, ctx, project_id)
    rows = await db.execute(select(ProjectSource).where(ProjectSource.project_id == project_id))
    return list(rows.scalars())


@router.put("/sources/{kind}", response_model=SourceOut)
async def link_source(
    project_id: uuid.UUID,
    kind: LinkableKind,
    body: SourceLink,
    ctx: IntegrationsManage,
    db: DbSession,
    identity: Identity,
) -> ProjectSource:
    """Link a provider property to the project (checked against the account's access)."""
    project = await _project(db, ctx, project_id)
    source_kind = SourceKind(kind)
    try:
        if source_kind is SourceKind.BING:
            key = await bing_api_key(db, ctx.organization_id, identity.keyring)
            sites = {
                s["site_url"]: s for s in await BingWebmasterClient(identity.http, key).sites()
            }
            site = sites.get(body.property_id)
            if site is None or not site["verified"]:
                raise ConflictError(
                    "That site isn't verified in your Bing Webmaster Tools account."
                )
        else:
            token = await google_access_token(
                db,
                ctx.organization_id,
                keyring=identity.keyring,
                settings=identity.settings,
                http=identity.http,
                scope=SCOPES["ga4"] if source_kind is SourceKind.GA4 else None,
            )
            if source_kind is SourceKind.GSC:
                sites = {s["site_url"]: s for s in await GscClient(identity.http, token).sites()}
                site = sites.get(body.property_id)
                if site is None:
                    raise ConflictError(
                        "That Search Console property isn't available to the connected account."
                    )
                if not _gsc_matches(body.property_id, project.primary_domain):
                    raise ConflictError("That Search Console property is for a different domain.")
                # A verified GSC owner/full user proves domain ownership (plan §5.5).
                if project.domain_verified_at is None and site["permission"] in {
                    "siteOwner",
                    "siteFullUser",
                }:
                    project.domain_verified_at = datetime.now(UTC)
                    project.verification_method = "gsc"
            else:
                props = {
                    p["property_id"] for p in await Ga4Client(identity.http, token).properties()
                }
                if body.property_id not in props:
                    raise ConflictError(
                        "That GA4 property isn't available to the connected account."
                    )
    except ProviderError as exc:
        raise provider_problem(exc) from exc
    source = await _source(db, project.id, source_kind)
    if source is None:
        source = ProjectSource(
            organization_id=ctx.organization_id,
            project_id=project.id,
            kind=source_kind,
            property_id=body.property_id,
        )
        db.add(source)
    elif source.property_id != body.property_id:
        source.synced_through = None  # different property: re-backfill
    source.property_id = body.property_id
    record_audit_event(
        db,
        "project.source_linked",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="project",
        target_id=project.id,
        details={"kind": kind},
    )
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/sources/{kind}", status_code=204)
async def unlink_source(
    project_id: uuid.UUID, kind: LinkableKind, ctx: IntegrationsManage, db: DbSession
) -> None:
    await _project(db, ctx, project_id)
    await db.execute(
        delete(ProjectSource).where(
            ProjectSource.project_id == project_id, ProjectSource.kind == SourceKind(kind)
        )
    )
    await db.commit()


@router.post("/sources/{kind}/sync", response_model=JobOut, status_code=202)
async def sync_source(
    project_id: uuid.UUID,
    kind: Literal["gsc", "ga4", "bing", "vitals"],
    ctx: ProjectWrite,
    db: DbSession,
    request: Request,
) -> JobOut:
    project = await _project(db, ctx, project_id)
    if kind == "vitals":
        if not request.app.state.settings.google_api_key.get_secret_value():
            raise ConflictError("Core Web Vitals data isn't configured on this server.")
        job_kind = "vitals_sync"
    else:
        if await _source(db, project.id, SourceKind(kind)) is None:
            raise ConflictError("Link a property to this project first.")
        job_kind = SYNC_KINDS[SourceKind(kind)]
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=job_kind,
        project_id=project.id,
        user_id=ctx.actor_user_id,
    )
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return JobOut.model_validate(job)


# -------------------------------------------------------------------------- IndexNow
@router.post("/indexnow", response_model=SourceOut)
async def create_indexnow_key(
    project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession
) -> ProjectSource:
    project = await _project(db, ctx, project_id)
    source = await indexnow_source(db, project.id)
    if source is None:
        key = indexnow.new_key()
        source = ProjectSource(
            organization_id=ctx.organization_id,
            project_id=project.id,
            kind=SourceKind.INDEXNOW,
            property_id=key,
            settings={
                "verified": False,
                "auto_submit": False,
                "key_location": indexnow.key_location(project.primary_domain, key),
            },
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)
    return source


@router.post("/indexnow/verify", response_model=SourceOut)
async def verify_indexnow_key(
    project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession, identity: Identity
) -> ProjectSource:
    project = await _project(db, ctx, project_id)
    source = await indexnow_source(db, project.id)
    if source is None:
        raise NotFoundError("Create an IndexNow key first.")
    ok = await indexnow.key_file_ok(identity.http, project.primary_domain, source.property_id)
    source.settings = {
        **source.settings,
        "verified": ok,
        "checked_at": datetime.now(UTC).isoformat(),
    }
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/indexnow", response_model=SourceOut)
async def indexnow_settings(
    project_id: uuid.UUID, body: IndexNowSettings, ctx: ProjectWrite, db: DbSession
) -> ProjectSource:
    project = await _project(db, ctx, project_id)
    source = await indexnow_source(db, project.id)
    if source is None:
        raise NotFoundError("Create an IndexNow key first.")
    if body.auto_submit:
        require_verified(project)
        if not source.settings.get("verified"):
            raise ConflictError(
                "Verify the IndexNow key file before enabling automatic submission."
            )
    source.settings = {**source.settings, "auto_submit": body.auto_submit}
    await db.commit()
    await db.refresh(source)
    return source


@router.post(
    "/submissions", response_model=list[SubmissionOut], dependencies=[Depends(_SUBMIT_RATE)]
)
async def submit_urls(
    project_id: uuid.UUID, body: UrlList, ctx: ProjectWrite, db: DbSession, identity: Identity
) -> list[IndexNowSubmission]:
    project = await _project(db, ctx, project_id)
    require_verified(project)
    urls = clean_urls(project, body.urls)
    try:
        if body.channel == "bing":
            source = await _source(db, project.id, SourceKind.BING)
            if source is None:
                raise ConflictError("Link a Bing Webmaster Tools site first.")
            key = await bing_api_key(db, ctx.organization_id, identity.keyring)
            return [
                await submit_bing(
                    db,
                    project=project,
                    site_url=source.property_id,
                    api_key=key,
                    urls=urls,
                    http=identity.http,
                )
            ]
        source = await indexnow_source(db, project.id)
        if source is None:
            raise ConflictError("Create and verify an IndexNow key first.")
        return await submit_indexnow(
            db,
            project=project,
            source=source,
            urls=urls,
            http=identity.http,
            settings=identity.settings,
            trigger="manual",
        )
    except ProviderError as exc:
        raise provider_problem(exc) from exc


@router.get("/submissions", response_model=list[SubmissionOut])
async def list_submissions(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[IndexNowSubmission]:
    await _project(db, ctx, project_id)
    rows = await db.execute(
        select(IndexNowSubmission)
        .where(IndexNowSubmission.project_id == project_id)
        .order_by(desc(IndexNowSubmission.submitted_at))
        .limit(50)
    )
    return list(rows.scalars())


# ----------------------------------------------------------- URL Inspection, sitemaps
@router.post("/inspections", response_model=InspectionOut, dependencies=[Depends(_INSPECT_RATE)])
async def inspect_url(
    project_id: uuid.UUID,
    body: InspectRequest,
    ctx: ProjectWrite,
    db: DbSession,
    identity: Identity,
) -> UrlInspection:
    project = await _project(db, ctx, project_id)
    source = await _source(db, project.id, SourceKind.GSC)
    if source is None:
        raise ConflictError("Link a Search Console property first.")
    url = clean_urls(project, [body.url])[0]
    try:
        token = await google_access_token(
            db,
            ctx.organization_id,
            keyring=identity.keyring,
            settings=identity.settings,
            http=identity.http,
        )
        result = await GscClient(identity.http, token).inspect(source.property_id, url)
    except ProviderError as exc:
        raise provider_problem(exc) from exc
    index = result.get("indexStatusResult") or {}
    crawled = index.get("lastCrawlTime")
    inspection = UrlInspection(
        organization_id=ctx.organization_id,
        project_id=project.id,
        url=url,
        inspected_at=datetime.now(UTC),
        verdict=index.get("verdict"),
        coverage_state=index.get("coverageState"),
        indexing_state=index.get("indexingState"),
        robots_state=index.get("robotsTxtState"),
        page_fetch_state=index.get("pageFetchState"),
        last_crawl_time=datetime.fromisoformat(crawled.replace("Z", "+00:00")) if crawled else None,
        google_canonical=index.get("googleCanonical"),
        user_canonical=index.get("userCanonical"),
        raw={
            k: v
            for k, v in result.items()
            if k in {"indexStatusResult", "mobileUsabilityResult", "richResultsResult"}
        },
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return inspection


@router.get("/inspections", response_model=list[InspectionOut])
async def list_inspections(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[UrlInspection]:
    await _project(db, ctx, project_id)
    rows = await db.execute(
        select(UrlInspection)
        .where(UrlInspection.project_id == project_id)
        .order_by(desc(UrlInspection.inspected_at))
        .limit(50)
    )
    return list(rows.scalars())


@router.get("/gsc/sitemaps")
async def gsc_sitemaps(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession, identity: Identity
) -> list[dict[str, object]]:
    project = await _project(db, ctx, project_id)
    source = await _source(db, project.id, SourceKind.GSC)
    if source is None:
        raise ConflictError("Link a Search Console property first.")
    try:
        token = await google_access_token(
            db,
            ctx.organization_id,
            keyring=identity.keyring,
            settings=identity.settings,
            http=identity.http,
        )
        return await GscClient(identity.http, token).sitemaps(source.property_id)
    except ProviderError as exc:
        raise provider_problem(exc) from exc


@router.post("/gsc/sitemaps", status_code=204, dependencies=[Depends(_SUBMIT_RATE)])
async def gsc_submit_sitemap(
    project_id: uuid.UUID, body: SitemapSubmit, ctx: ProjectWrite, db: DbSession, identity: Identity
) -> None:
    project = await _project(db, ctx, project_id)
    source = await _source(db, project.id, SourceKind.GSC)
    if source is None:
        raise ConflictError("Link a Search Console property first.")
    url = clean_urls(project, [body.url])[0]
    try:
        token = await google_access_token(
            db,
            ctx.organization_id,
            keyring=identity.keyring,
            settings=identity.settings,
            http=identity.http,
            scope=SCOPES["gsc_write"],
        )
        await GscClient(identity.http, token).submit_sitemap(source.property_id, url)
    except ProviderError as exc:
        raise provider_problem(exc) from exc


# --------------------------------------------------------------------- CSV imports
@router.post("/imports/{source}", response_model=ImportOut, dependencies=[Depends(_IMPORT_RATE)])
async def import_csv(
    project_id: uuid.UUID,
    source: Literal["gsc_genai", "bing_ai"],
    ctx: ProjectWrite,
    db: DbSession,
    request: Request,
    surface: Annotated[Literal["ai_overview", "ai_mode", "copilot"] | None, Query()] = None,
) -> ImportOut:
    """Import a CSV export (raw ``text/csv`` body). Replaces the file's date range."""
    project = await _project(db, ctx, project_id)
    limit = request.app.state.settings.max_csv_import_bytes
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise ImportRejectedError(f"The file is larger than {limit // (1024 * 1024)} MB.")
        chunks.append(chunk)
    try:
        parsed = parse_ai_csv(b"".join(chunks), source=source, default_surface=surface)
    except CsvImportError as exc:
        raise ImportRejectedError(str(exc)) from exc
    span = parsed.date_range
    if span is None:
        raise ImportRejectedError("No valid rows found.")
    await db.execute(
        delete(AiPerformanceDaily).where(
            AiPerformanceDaily.project_id == project.id,
            AiPerformanceDaily.source == source,
            AiPerformanceDaily.date.between(span[0], span[1]),
        )
    )
    rows = [
        {
            "id": uuid7(),
            "organization_id": ctx.organization_id,
            "project_id": project.id,
            "source": source,
            "date": r.date,
            "surface": r.surface,
            "page": r.page,
            "query": r.query,
            "country": r.country,
            "device": r.device,
            "impressions": r.impressions,
            "clicks": r.clicks,
            "citations": r.citations,
        }
        for r in parsed.rows
    ]
    for start in range(0, len(rows), 1000):
        await db.execute(insert(AiPerformanceDaily), rows[start : start + 1000])
    record_audit_event(
        db,
        "project.data_imported",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="project",
        target_id=project.id,
        details={"source": source, "rows": len(rows)},
    )
    await db.commit()
    return ImportOut(
        rows=len(rows),
        bad_rows=parsed.bad_rows,
        errors=parsed.errors,
        date_from=span[0],
        date_to=span[1],
        columns=parsed.columns,
        missing_metrics=parsed.missing_metrics,
    )


# ----------------------------------------------------------------------- data views
def _ratio(clicks: int, impressions: int) -> float | None:
    return round(clicks / impressions, 4) if impressions else None


@router.get("/performance", response_model=PerformanceOut)
async def performance(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    source: Literal["gsc", "bing"] = "gsc",
    days: Annotated[int, Query(ge=7, le=480)] = 28,
) -> PerformanceOut:
    """Totals and top queries/pages from first-party data (no estimates)."""
    await _project(db, ctx, project_id)
    model = GscDaily if source == "gsc" else BingDaily
    latest = (
        await db.execute(select(func.max(model.date)).where(model.project_id == project_id))
    ).scalar_one()
    end = latest or datetime.now(UTC).date()
    start = end - timedelta(days=days - 1)
    scope = (model.project_id == project_id) & model.date.between(start, end)
    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(model.clicks), 0),
                func.coalesce(func.sum(model.impressions), 0),
                func.sum(model.position * model.impressions)
                / func.nullif(func.sum(model.impressions), 0),
            ).where(scope)
        )
    ).one()

    async def top(column: Any) -> list[MetricRow]:
        weighted = func.sum(model.position * model.impressions) / func.nullif(
            func.sum(model.impressions), 0
        )
        rows = await db.execute(
            select(column, func.sum(model.clicks), func.sum(model.impressions), weighted)
            .where(scope)
            .group_by(column)
            .order_by(desc(func.sum(model.clicks)), desc(func.sum(model.impressions)))
            .limit(25)
        )
        return [
            MetricRow(
                key=str(k),
                clicks=int(c),
                impressions=int(i),
                ctr=_ratio(int(c), int(i)),
                position=round(float(p), 1) if p is not None else None,
            )
            for k, c, i, p in rows
        ]

    clicks, impressions, position = int(totals[0]), int(totals[1]), totals[2]
    return PerformanceOut(
        source=source,
        days=days,
        date_from=start,
        date_to=end,
        has_data=latest is not None,
        clicks=clicks,
        impressions=impressions,
        ctr=_ratio(clicks, impressions),
        position=round(float(position), 1) if position is not None else None,
        top_queries=await top(model.query),
        top_pages=await top(GscDaily.page) if source == "gsc" else [],
    )


@router.get("/vitals", response_model=list[VitalsOut])
async def vitals(project_id: uuid.UUID, ctx: ProjectRead, db: DbSession) -> list[VitalsOut]:
    await _project(db, ctx, project_id)
    return [
        VitalsOut(
            target=v.target,
            scope=v.scope,
            form_factor=v.form_factor,
            date=v.date,
            lcp_ms=v.lcp_ms,
            inp_ms=v.inp_ms,
            cls=v.cls,
            fcp_ms=v.fcp_ms,
            ttfb_ms=v.ttfb_ms,
            assessment=assess({"lcp_ms": v.lcp_ms, "inp_ms": v.inp_ms, "cls": v.cls}),
        )
        for v in sorted(
            await latest_vitals(db, project_id),
            key=lambda v: (v.scope != "origin", v.target, v.form_factor),
        )
    ]


@router.get("/ai-performance", response_model=list[AiSurfaceTotals])
async def ai_performance(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    days: Annotated[int, Query(ge=7, le=480)] = 90,
) -> list[AiSurfaceTotals]:
    await _project(db, ctx, project_id)
    since = datetime.now(UTC).date() - timedelta(days=days)
    rows = await db.execute(
        select(
            AiPerformanceDaily.source,
            AiPerformanceDaily.surface,
            func.sum(AiPerformanceDaily.impressions),
            func.sum(AiPerformanceDaily.clicks),
            func.sum(AiPerformanceDaily.citations),
            func.min(AiPerformanceDaily.date),
            func.max(AiPerformanceDaily.date),
        )
        .where(AiPerformanceDaily.project_id == project_id, AiPerformanceDaily.date >= since)
        .group_by(AiPerformanceDaily.source, AiPerformanceDaily.surface)
    )
    return [
        AiSurfaceTotals(
            source=s,
            surface=f,
            impressions=int(i),
            clicks=int(c),
            citations=int(ci),
            date_from=d0,
            date_to=d1,
        )
        for s, f, i, c, ci, d0, d1 in rows
    ]
