"""AI visibility API: ``/orgs/{org}/projects/{project}/ai/...``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.errors import AppError, NotFoundError
from serptank.core.models import AIEngine
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.ai_visibility import service
from serptank.modules.ai_visibility.models import AiObservation, AiProfile, AiPrompt
from serptank.modules.ai_visibility.readiness import compute_readiness
from serptank.modules.ai_visibility.schemas import (
    AiSettingsIn,
    AiSettingsOut,
    AnswerOut,
    EngineStatus,
    PromptOut,
    PromptsAdded,
    PromptsIn,
    PromptSuggestion,
    PromptUpdate,
    ReadinessOut,
    VisibilityOut,
)
from serptank.modules.billing.entitlements import PlanLimitError, plan_for
from serptank.modules.identity.deps import DbSession
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.keywords.intent import classify
from serptank.modules.llm.gateway import requests_this_month
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.projects.router import ProjectRepository
from serptank.modules.search_data.models import TrackedKeyword
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects/{project_id}/ai", tags=["ai-visibility"])
ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
_RUN_RATE = rate_limit("ai-run", Rate(20, 3600))
MAX_ANSWERS = 100
ENGINE_NOTES = {
    "google_ai_overview": "Needs a SERP data vendor (see Search data).",
    "google_ai_mode": "No AI Mode source yet; use the Search Console Gen-AI import.",
    "chatgpt": "Needs an OpenAI API key on the server.",
    "perplexity": "Needs a Perplexity API key on the server.",
    "gemini": "No sampling adapter yet.",
    "copilot": "No sampling adapter yet; import Bing AI Performance for Copilot citations.",
    "claude": "No sampling adapter yet.",
}


class InvalidPromptError(AppError):
    status = 422
    code = "invalid_prompt"
    title = "Invalid prompt"


async def _project(db: AsyncSession, ctx: OrgContext, project_id: uuid.UUID) -> Project:
    return await ProjectRepository(db, ctx.organization_id).get(project_id)


async def _markets(db: AsyncSession, project: Project) -> list[ProjectMarket]:
    return list(
        (
            await db.execute(select(ProjectMarket).where(ProjectMarket.project_id == project.id))
        ).scalars()
    )


# -------------------------------------------------------------------------- settings
@router.get("/settings", response_model=AiSettingsOut)
async def get_settings(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession, request: Request
) -> AiSettingsOut:
    project = await _project(db, ctx, project_id)
    profile = await service.get_profile(db, project)
    plan = plan_for(ctx.organization.plan_code)
    selected = {e.value for m in await _markets(db, project) for e in m.ai_engines}
    available = service.available_engines(request.app.state.job_runtime.extras)
    entitled = {e.value for e in plan.ai_engines}
    return AiSettingsOut(
        brand_terms=profile.brand_terms,
        samples_per_prompt=profile.samples_per_prompt,
        prompts_used_this_month=await requests_this_month(
            db, ctx.organization_id, service.USAGE_PREFIX
        ),
        prompts_per_month=plan.ai_prompts_per_month,
        engines=[
            EngineStatus(
                engine=e.value,
                selected=e.value in selected,
                entitled=e.value in entitled,
                available=e.value in available,
                note=None if e.value in available else ENGINE_NOTES.get(e.value),
            )
            for e in AIEngine
        ],
    )


@router.put("/settings", status_code=204)
async def update_settings(
    project_id: uuid.UUID, body: AiSettingsIn, ctx: ProjectWrite, db: DbSession
) -> None:
    project = await _project(db, ctx, project_id)
    terms = list(dict.fromkeys(t.strip()[:80] for t in body.brand_terms if len(t.strip()) >= 2))  # noqa: PLR2004
    profile = await db.get(AiProfile, project.id)
    if profile is None:
        db.add(
            AiProfile(
                project_id=project.id,
                organization_id=ctx.organization_id,
                brand_terms=terms,
                samples_per_prompt=body.samples_per_prompt,
            )
        )
    else:
        profile.brand_terms = terms
        profile.samples_per_prompt = body.samples_per_prompt
    await db.commit()


# --------------------------------------------------------------------------- prompts
@router.get("/prompts", response_model=list[PromptOut])
async def list_prompts(project_id: uuid.UUID, ctx: ProjectRead, db: DbSession) -> list[PromptOut]:
    project = await _project(db, ctx, project_id)
    rows = await db.execute(
        select(AiPrompt).where(AiPrompt.project_id == project.id).order_by(AiPrompt.created_at)
    )
    return [PromptOut.model_validate(r) for r in rows.scalars()]


@router.post("/prompts", response_model=PromptsAdded, status_code=201)
async def add_prompts(
    project_id: uuid.UUID, body: PromptsIn, ctx: ProjectWrite, db: DbSession
) -> PromptsAdded:
    project = await _project(db, ctx, project_id)
    market = await db.get(ProjectMarket, body.market_id)
    if market is None or market.project_id != project.id:
        raise NotFoundError("Market not found.")
    cleaned = [" ".join(p.split())[:500] for p in body.prompts]
    if any(len(p) < 3 for p in cleaned):  # noqa: PLR2004
        raise InvalidPromptError("Prompts need at least 3 characters.")
    # Duplicates are case-insensitive: "Best shoes?" and "best shoes?" are one prompt.
    seen = {
        p.lower()
        for p in (
            await db.execute(select(AiPrompt.prompt).where(AiPrompt.market_id == market.id))
        ).scalars()
    }
    new: list[str] = []
    for prompt in cleaned:
        if prompt.lower() not in seen:
            seen.add(prompt.lower())
            new.append(prompt)
    count = int(
        (
            await db.execute(
                select(func.count()).select_from(AiPrompt).where(AiPrompt.project_id == project.id)
            )
        ).scalar_one()
    )
    if count + len(new) > service.MAX_PROMPTS:
        raise PlanLimitError(
            f"A project can track up to {service.MAX_PROMPTS} prompts.",
            extra={"limit": service.MAX_PROMPTS, "resource": "AI prompts"},
        )
    for prompt in new:
        db.add(
            AiPrompt(
                organization_id=ctx.organization_id,
                project_id=project.id,
                market_id=market.id,
                prompt=prompt,
                keyword=body.keyword,
                engines=[e.value for e in body.engines],
                active=True,
            )
        )
    await db.commit()
    return PromptsAdded(added=len(new), skipped_existing=len(cleaned) - len(new))


async def _prompt(db: AsyncSession, project: Project, prompt_id: uuid.UUID) -> AiPrompt:
    prompt = await db.get(AiPrompt, prompt_id)
    if prompt is None or prompt.project_id != project.id:
        raise NotFoundError("Prompt not found.")
    return prompt


@router.patch("/prompts/{prompt_id}", response_model=PromptOut)
async def update_prompt(
    project_id: uuid.UUID,
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    ctx: ProjectWrite,
    db: DbSession,
) -> PromptOut:
    project = await _project(db, ctx, project_id)
    prompt = await _prompt(db, project, prompt_id)
    prompt.active = body.active
    await db.commit()
    await db.refresh(prompt)
    return PromptOut.model_validate(prompt)


@router.delete("/prompts/{prompt_id}", status_code=204)
async def delete_prompt(
    project_id: uuid.UUID, prompt_id: uuid.UUID, ctx: ProjectWrite, db: DbSession
) -> None:
    project = await _project(db, ctx, project_id)
    await db.delete(await _prompt(db, project, prompt_id))
    await db.commit()


def suggest_prompt(keyword: str, intent: str) -> str:
    """A natural question a user might ask an AI assistant about ``keyword``."""
    text = keyword.strip()
    if intent == "informational" or text.split(" ", 1)[0] in {
        "how",
        "what",
        "why",
        "when",
        "who",
        "where",
        "which",
        "can",
        "is",
        "are",
        "do",
        "does",
    }:
        return text[0].upper() + text[1:] + ("" if text.endswith("?") else "?")
    if intent == "transactional":
        return f"Where is the best place to buy {text}?"
    if intent == "local":
        return f"What are the best options for {text}?"
    return f"What are the best {text}? Please recommend specific brands or sites."


@router.get("/prompts/suggestions", response_model=list[PromptSuggestion])
async def prompt_suggestions(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession, market_id: uuid.UUID
) -> list[PromptSuggestion]:
    """Deterministic suggestions from tracked keywords (no LLM, no cost)."""
    project = await _project(db, ctx, project_id)
    used = set(
        (
            await db.execute(select(AiPrompt.keyword).where(AiPrompt.project_id == project.id))
        ).scalars()
    )
    keywords = (
        await db.execute(
            select(TrackedKeyword.keyword)
            .where(TrackedKeyword.project_id == project.id, TrackedKeyword.market_id == market_id)
            .order_by(TrackedKeyword.created_at)
            .limit(200)
        )
    ).scalars()
    out = []
    for keyword in keywords:
        if keyword in used:
            continue
        intent = classify(keyword).primary
        out.append(
            PromptSuggestion(prompt=suggest_prompt(keyword, intent), keyword=keyword, intent=intent)
        )
        if len(out) >= 20:  # noqa: PLR2004
            break
    return out


# ------------------------------------------------------------------ runs and results
@router.post("/run", response_model=JobOut, status_code=202, dependencies=[Depends(_RUN_RATE)])
async def run_sampling(
    project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession, request: Request
) -> JobOut:
    project = await _project(db, ctx, project_id)
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=service.JOB_KIND,
        project_id=project.id,
        user_id=ctx.actor_user_id,
    )
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return JobOut.model_validate(job)


@router.get("/visibility", response_model=VisibilityOut)
async def get_visibility(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> VisibilityOut:
    project = await _project(db, ctx, project_id)
    own, _ = await service.entities(db, project, await service.get_profile(db, project))
    return VisibilityOut.model_validate(await service.visibility(db, project, days, own.key))


@router.get("/answers", response_model=list[AnswerOut])
async def list_answers(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    prompt_id: uuid.UUID | None = None,
    engine: str | None = Query(default=None, max_length=30),
) -> list[AnswerOut]:
    project = await _project(db, ctx, project_id)
    query = select(AiObservation).where(AiObservation.project_id == project.id)
    if prompt_id is not None:
        query = query.where(AiObservation.prompt_id == prompt_id)
    if engine is not None:
        query = query.where(AiObservation.engine == engine)
    rows = await db.execute(
        query.order_by(desc(AiObservation.date), AiObservation.engine, AiObservation.sample).limit(
            MAX_ANSWERS
        )
    )
    return [AnswerOut.model_validate(r) for r in rows.scalars()]


@router.get("/readiness", response_model=ReadinessOut)
async def get_readiness(project_id: uuid.UUID, ctx: ProjectRead, db: DbSession) -> ReadinessOut:
    project = await _project(db, ctx, project_id)
    return ReadinessOut.model_validate((await compute_readiness(db, project.id)).to_json())
