"""``GET /orgs/{org}/ai-usage``: this month's LLM token use against the plan budget."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select

from serptank.modules.billing.entitlements import plan_for
from serptank.modules.identity.deps import DbSession
from serptank.modules.llm.gateway import LlmGateway, month_start
from serptank.modules.llm.models import LlmUsage
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}", tags=["ai"])
OrgRead = Annotated[OrgContext, Depends(org_access(Permission.ORG_READ))]


class PurposeUsage(BaseModel):
    purpose: str
    requests: int
    tokens: int


class AiUsageOut(BaseModel):
    available: bool  # a provider is configured and enabled
    month: str
    tokens_used: int
    tokens_per_month: int
    by_purpose: list[PurposeUsage]


@router.get("/ai-usage", response_model=AiUsageOut)
async def ai_usage(ctx: OrgRead, db: DbSession, request: Request) -> AiUsageOut:
    gateway: LlmGateway = request.app.state.job_runtime.extras["llm"]
    rows = (
        await db.execute(
            select(LlmUsage).where(
                LlmUsage.organization_id == ctx.organization_id, LlmUsage.month == month_start()
            )
        )
    ).scalars()
    by_purpose = [
        PurposeUsage(
            purpose=r.purpose, requests=r.requests, tokens=r.input_tokens + r.output_tokens
        )
        for r in rows
    ]
    return AiUsageOut(
        available=gateway.enabled and gateway.provider is not None,
        month=month_start().isoformat(),
        tokens_used=sum(p.tokens for p in by_purpose),
        tokens_per_month=plan_for(ctx.organization.plan_code).llm_tokens_per_month,
        by_purpose=by_purpose,
    )
