"""Projects, target markets and domain verification (``/api/v1/orgs/{org_id}/projects``)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.audit import record_audit_event
from serptank.core.errors import ConflictError, NotFoundError
from serptank.core.ratelimit import Rate, rate_limit
from serptank.core.repository import TenantRepository
from serptank.modules.billing.entitlements import plan_for, require_below_limit, require_engines
from serptank.modules.identity.deps import DbSession, Identity
from serptank.modules.projects.domains import normalize_domain, registrable_domain
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.projects.schemas import (
    MarketIn,
    MarketOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    VerificationInstructions,
    VerificationResult,
    VerificationStart,
)
from serptank.modules.projects.verification import (
    TXT_PREFIX,
    WELL_KNOWN_PATH,
    TxtResolver,
    VerificationMethod,
    check_dns,
    check_html,
    new_verification_token,
    system_txt_resolver,
)
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects", tags=["projects"])

ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
_VERIFY_RATE = rate_limit("verify-domain", Rate(10, 600))


class ProjectRepository(TenantRepository[Project]):
    model = Project
    not_found_message = "Project not found."

    def _scoped(self):  # type: ignore[no-untyped-def]
        return super()._scoped().where(Project.deleted_at.is_(None))


async def _markets(db: AsyncSession, project_id: uuid.UUID) -> list[ProjectMarket]:
    rows = await db.execute(
        select(ProjectMarket)
        .where(ProjectMarket.project_id == project_id)
        # UUIDv7 ids are time-ordered, making same-transaction inserts deterministic.
        .order_by(ProjectMarket.created_at, ProjectMarket.id)
    )
    return list(rows.scalars())


async def _out(db: AsyncSession, project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        primary_domain=project.primary_domain,
        verified=project.domain_verified_at is not None,
        verification_method=project.verification_method,
        created_at=project.created_at,
        markets=[MarketOut.model_validate(m) for m in await _markets(db, project.id)],
    )


def _market(ctx: OrgContext, project: Project, body: MarketIn) -> ProjectMarket:
    require_engines(plan_for(ctx.organization.plan_code), body.search_engines, body.ai_engines)
    return ProjectMarket(
        organization_id=ctx.organization_id,
        project_id=project.id,
        country=body.country.upper(),
        language=body.language,
        location=body.location or None,
        device=body.device,
        search_engines=sorted(set(body.search_engines), key=lambda e: e.value),
        ai_engines=sorted(set(body.ai_engines), key=lambda e: e.value),
    )


@router.get("", response_model=list[ProjectOut])
async def list_projects(ctx: ProjectRead, db: DbSession) -> list[ProjectOut]:
    projects = await ProjectRepository(db, ctx.organization_id).list(limit=500)
    return [await _out(db, p) for p in sorted(projects, key=lambda p: p.name.lower())]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, ctx: ProjectWrite, db: DbSession) -> ProjectOut:
    plan = plan_for(ctx.organization.plan_code)
    repo = ProjectRepository(db, ctx.organization_id)
    require_below_limit(await repo.count(), plan.max_projects, "projects", plan)
    if len(body.markets) > plan.max_markets_per_project:
        require_below_limit(
            plan.max_markets_per_project, plan.max_markets_per_project, "markets per project", plan
        )
    project = repo.add(Project(name=body.name, primary_domain=normalize_domain(body.domain)))
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A project for this domain already exists.") from exc
    for market in body.markets:
        db.add(_market(ctx, project, market))
    record_audit_event(
        db,
        "project.created",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="project",
        target_id=project.id,
        details={"domain": project.primary_domain},
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Duplicate markets in the request.") from exc
    await db.refresh(project)
    return await _out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, ctx: ProjectRead, db: DbSession) -> ProjectOut:
    return await _out(db, await ProjectRepository(db, ctx.organization_id).get(project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID, body: ProjectUpdate, ctx: ProjectWrite, db: DbSession
) -> ProjectOut:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    project.name = body.name
    await db.commit()
    return await _out(db, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession) -> None:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    project.deleted_at = datetime.now(UTC)
    record_audit_event(
        db,
        "project.deleted",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="project",
        target_id=project.id,
    )
    await db.commit()


# ------------------------------------------------------------------------ markets
@router.post("/{project_id}/markets", response_model=MarketOut, status_code=201)
async def add_market(
    project_id: uuid.UUID, body: MarketIn, ctx: ProjectWrite, db: DbSession
) -> ProjectMarket:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    plan = plan_for(ctx.organization.plan_code)
    count = await db.execute(select(func.count()).where(ProjectMarket.project_id == project.id))
    require_below_limit(
        int(count.scalar_one()), plan.max_markets_per_project, "markets per project", plan
    )
    market = _market(ctx, project, body)
    db.add(market)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("This market already exists for the project.") from exc
    return market


@router.delete("/{project_id}/markets/{market_id}", status_code=204)
async def remove_market(
    project_id: uuid.UUID, market_id: uuid.UUID, ctx: ProjectWrite, db: DbSession
) -> None:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    market = await db.get(ProjectMarket, market_id)
    if market is None or market.project_id != project.id:
        raise NotFoundError("Market not found.")
    remaining = await db.execute(select(func.count()).where(ProjectMarket.project_id == project.id))
    if int(remaining.scalar_one()) <= 1:
        # Every feature (audits, rankings, AI visibility) is scoped to a market.
        raise ConflictError("A project needs at least one market.")
    await db.delete(market)
    await db.commit()


# ------------------------------------------------------------------- verification
def _instructions(
    project: Project, method: VerificationMethod, token: str
) -> VerificationInstructions:
    if method is VerificationMethod.DNS:
        return VerificationInstructions(
            method=method,
            token=token,
            dns_record_name=registrable_domain(project.primary_domain),
            dns_record_value=TXT_PREFIX + token,
        )
    return VerificationInstructions(
        method=method,
        token=token,
        file_url=f"https://{project.primary_domain}{WELL_KNOWN_PATH}",
        file_contents=token,
    )


@router.post("/{project_id}/verification", response_model=VerificationInstructions)
async def start_verification(
    project_id: uuid.UUID, body: VerificationStart, ctx: ProjectWrite, db: DbSession
) -> VerificationInstructions:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    # The token is published by the customer (DNS/file), so it is not a secret.
    token = project.verification_token or new_verification_token()
    project.verification_token = token
    project.verification_method = body.method.value
    await db.commit()
    return _instructions(project, body.method, token)


@router.post(
    "/{project_id}/verification/check",
    response_model=VerificationResult,
    dependencies=[Depends(_VERIFY_RATE)],
)
async def check_verification(
    project_id: uuid.UUID, request: Request, ctx: ProjectWrite, db: DbSession, identity: Identity
) -> VerificationResult:
    project = await ProjectRepository(db, ctx.organization_id).get(project_id)
    if not project.verification_token or not project.verification_method:
        raise ConflictError("Start verification first.")
    method = VerificationMethod(project.verification_method)
    if method is VerificationMethod.DNS:
        resolver: TxtResolver = getattr(request.app.state, "txt_resolver", system_txt_resolver)
        ok = await check_dns(project.primary_domain, project.verification_token, resolver)
    else:
        ok = await check_html(project.primary_domain, project.verification_token, identity.http)
    if not ok:
        return VerificationResult(
            verified=False,
            detail="We could not find the verification token yet. DNS changes can take a while.",
        )
    project.domain_verified_at = datetime.now(UTC)
    record_audit_event(
        db,
        "project.domain_verified",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="project",
        target_id=project.id,
        details={"method": method.value},
    )
    await db.commit()
    return VerificationResult(verified=True, detail="Domain verified.")
