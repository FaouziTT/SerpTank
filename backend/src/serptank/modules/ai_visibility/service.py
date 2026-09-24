"""AI-visibility sampling job and aggregation.

``ai_sampling`` runs every active prompt against each engine that is (a) selected for
the prompt or market, (b) included in the plan, and (c) available on this server:

* ``google_ai_overview`` - the Google SERP for the prompt through the shared collector
  (one sample per day; the SERP is the same for everyone). Records whether an AI
  Overview appeared, and if so whether it names or cites the brand.
* answer engines (``chatgpt``, ``perplexity``) - ``samples_per_prompt`` independent
  answers, because answers vary between runs. Each sample counts against the plan's
  ``ai_prompts_per_month`` and the LLM token budget; when either runs out the job stops
  sampling and says so.

Aggregates report rates with Wilson 95% intervals, never bare percentages from 1 sample.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.modules.ai_visibility.detect import Entity, detect, entity_for
from serptank.modules.ai_visibility.engines import AnswerEngine
from serptank.modules.ai_visibility.models import AiObservation, AiProfile, AiPrompt
from serptank.modules.ai_visibility.stats import wilson
from serptank.modules.billing.entitlements import Plan, plan_for
from serptank.modules.integrations.models import AiPerformanceDaily
from serptank.modules.jobs.service import JobContext, JobFailedError, register_handler
from serptank.modules.llm.gateway import (
    LlmError,
    LlmGateway,
    record_usage,
    requests_this_month,
)
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.search_data.collector import CollectorRouter, SerpUnavailableError
from serptank.modules.search_data.models import Competitor, RankObservation, TrackedKeyword
from serptank.modules.search_data.schema import SerpRequest
from serptank.modules.tenancy.models import Organization

logger = structlog.get_logger(__name__)

JOB_KIND = "ai_sampling"
SERP_ENGINE = "google_ai_overview"
USAGE_PREFIX = "ai_sampling"
MAX_PROMPTS = 200
DEFAULT_SAMPLES = 3


# ---------------------------------------------------------------------- configuration
def answer_engines(extras: dict[str, Any]) -> dict[str, AnswerEngine]:
    engines: dict[str, AnswerEngine] = extras.get("answer_engines") or {}
    return engines


def available_engines(extras: dict[str, Any]) -> set[str]:
    """Engines this server can sample right now."""
    available = set(answer_engines(extras))
    router: CollectorRouter | None = extras.get("serp")
    if router is not None and router.supports("google"):
        available.add(SERP_ENGINE)
    return available


def entitled_engines(plan: Plan, market: ProjectMarket) -> set[str]:
    return {e.value for e in market.ai_engines} & {e.value for e in plan.ai_engines}


async def get_profile(db: AsyncSession, project: Project) -> AiProfile:
    profile = await db.get(AiProfile, project.id)
    if profile is None:
        profile = AiProfile(
            project_id=project.id,
            organization_id=project.organization_id,
            brand_terms=[project.name] if project.name else [],
            samples_per_prompt=DEFAULT_SAMPLES,
        )
    return profile


async def entities(
    db: AsyncSession, project: Project, profile: AiProfile
) -> tuple[Entity, list[Entity]]:
    competitors = (
        await db.execute(select(Competitor).where(Competitor.project_id == project.id))
    ).scalars()
    return (
        entity_for(project.primary_domain, profile.brand_terms),
        [entity_for(c.domain, [c.label] if c.label else []) for c in competitors],
    )


# ------------------------------------------------------------------------------ job
@dataclass
class _Run:
    ctx: JobContext
    project: Project
    plan: Plan
    own: Entity
    rivals: list[Entity]
    samples: int
    today: date
    counts: Counter[str] = field(default_factory=Counter)
    budget_left: int = 0
    stopped: str | None = None
    rate_limited: set[str] = field(default_factory=set)

    def row(self, prompt: AiPrompt, engine: str, sample: int, **values: Any) -> dict[str, Any]:
        return {
            "id": uuid.uuid4(),
            "date": self.today,
            "organization_id": self.ctx.organization_id,
            "project_id": self.project.id,
            "prompt_id": prompt.id,
            "engine": engine,
            "sample": sample,
            **values,
        }

    def detected(self, text: str, citations: list[str]) -> dict[str, Any]:
        found = detect(text, citations, self.own, self.rivals)
        return {
            "mentioned": found.mentioned,
            "cited": found.cited,
            "mention_rank": found.mention_rank,
            "sentiment": found.sentiment,
            "competitors": found.competitors,
            "excerpt": found.excerpt,
            "citations": citations[:30],
        }

    async def google(
        self, db: AsyncSession, prompt: AiPrompt, market: ProjectMarket
    ) -> list[dict[str, Any]]:
        router: CollectorRouter = self.ctx.runtime.extras["serp"]
        request = SerpRequest(
            engine="google",
            query=prompt.prompt,
            country=market.country,
            language=market.language,
            device=market.device.value,
            location=market.location,
            depth=10,
        )
        try:
            serp = await router.get(
                db,
                request,
                organization_id=self.ctx.organization_id,
                org_daily_cap=self.plan.serp_requests_per_day,
                today=self.today,
            )
        except SerpUnavailableError as exc:
            self.counts["failed"] += 1
            if exc.code in {"serp_org_budget", "serp_global_budget"}:
                self.stopped = exc.message
            return []
        self.counts["samples"] += 1
        answer = serp.data.ai_answer
        if answer is None:
            return [
                self.row(
                    prompt,
                    SERP_ENGINE,
                    0,
                    answered=False,
                    mentioned=False,
                    cited=False,
                    competitors={},
                    citations=[],
                    excerpt="",
                    model="google",
                )
            ]
        citations = answer.cited_urls or [f"https://{d}/" for d in answer.cited_domains]
        return [
            self.row(
                prompt,
                SERP_ENGINE,
                0,
                answered=True,
                model="google",
                **self.detected(answer.text, citations),
            )
        ]

    async def llm(
        self, db: AsyncSession, prompt: AiPrompt, market: ProjectMarket, name: str
    ) -> list[dict[str, Any]]:
        engine = answer_engines(self.ctx.runtime.extras)[name]
        gateway: LlmGateway | None = self.ctx.runtime.extras.get("llm")
        rows = []
        for sample in range(self.samples):
            if name in self.rate_limited:
                break
            if self.budget_left <= 0:
                self.stopped = "Your plan's monthly AI prompt samples are used up."
                break
            if gateway is not None and (
                await gateway.tokens_used(db, self.ctx.organization_id)
                >= self.plan.llm_tokens_per_month
            ):
                self.stopped = "Your plan's monthly AI token budget is used up."
                break
            try:
                answer = await engine.answer(prompt.prompt, country=market.country)
            except LlmError as exc:
                self.counts["failed"] += 1
                if exc.code == "llm_rate_limited":
                    self.rate_limited.add(name)
                continue
            self.budget_left -= 1
            self.counts["samples"] += 1
            await record_usage(
                db,
                self.ctx.organization_id,
                f"{USAGE_PREFIX}:{name}",
                answer.input_tokens,
                answer.output_tokens,
            )
            rows.append(
                self.row(
                    prompt,
                    name,
                    sample,
                    answered=True,
                    model=answer.model[:80],
                    **self.detected(answer.text, answer.citations),
                )
            )
        return rows


@register_handler(JOB_KIND, queue="ai")
async def run_ai_sampling(ctx: JobContext) -> dict[str, Any]:
    async with await ctx.session() as db:
        project = await db.get(Project, ctx.project_id)
        org = await db.get(Organization, ctx.organization_id)
        if project is None or project.deleted_at is not None or org is None:
            raise JobFailedError("project_gone", "The project no longer exists.")
        plan = plan_for(org.plan_code)
        profile = await get_profile(db, project)
        own, rivals = await entities(db, project, profile)
        run = _Run(
            ctx=ctx,
            project=project,
            plan=plan,
            own=own,
            rivals=rivals,
            samples=max(1, min(profile.samples_per_prompt, 10)),
            today=datetime.now(UTC).date(),
        )
        run.budget_left = plan.ai_prompts_per_month - await requests_this_month(
            db, ctx.organization_id, USAGE_PREFIX
        )
        markets = {
            m.id: m
            for m in (
                await db.execute(
                    select(ProjectMarket).where(ProjectMarket.project_id == project.id)
                )
            ).scalars()
        }
        prompts = list(
            (
                await db.execute(
                    select(AiPrompt)
                    .where(AiPrompt.project_id == project.id, AiPrompt.active.is_(True))
                    .order_by(AiPrompt.created_at)
                    .limit(MAX_PROMPTS)
                )
            ).scalars()
        )
        if not prompts:
            return {"prompts": 0, "note": "Add prompts to track first."}
        available = available_engines(ctx.runtime.extras)
        await db.execute(
            delete(AiObservation).where(
                AiObservation.project_id == project.id, AiObservation.date == run.today
            )
        )
        await db.commit()
        for index, prompt in enumerate(prompts):
            market = markets.get(prompt.market_id)
            if market is None:
                continue
            wanted = set(prompt.engines) or entitled_engines(plan, market)
            engines = sorted(wanted & entitled_engines(plan, market) & available)
            run.counts["unavailable"] += len(wanted - available)
            run.counts["prompts"] += 1
            rows: list[dict[str, Any]] = []
            for engine in engines:
                if run.stopped and engine != SERP_ENGINE:
                    continue
                if engine == SERP_ENGINE:
                    rows += await run.google(db, prompt, market)
                else:
                    rows += await run.llm(db, prompt, market, engine)
            if rows:
                await db.execute(insert(AiObservation), rows)
                await db.commit()
            await ctx.report(
                progress=(index + 1) / len(prompts), stage="sampling", counters=dict(run.counts)
            )
    result: dict[str, Any] = dict(run.counts)
    if run.stopped:
        result["note"] = run.stopped
    return result


# ------------------------------------------------------------------------ aggregation
def _rate(k: int, n: int) -> dict[str, Any]:
    r = wilson(k, n)
    return {
        "successes": r.successes,
        "trials": r.trials,
        "rate": r.rate,
        "low": r.low,
        "high": r.high,
    }


async def visibility(db: AsyncSession, project: Project, days: int, own_key: str) -> dict[str, Any]:
    since = datetime.now(UTC).date() - timedelta(days=days)
    rows = list(
        (
            await db.execute(
                select(AiObservation).where(
                    AiObservation.project_id == project.id, AiObservation.date > since
                )
            )
        ).scalars()
    )
    prompts = {
        p.id: p
        for p in (
            await db.execute(select(AiPrompt).where(AiPrompt.project_id == project.id))
        ).scalars()
    }
    by_engine: dict[str, list[AiObservation]] = defaultdict(list)
    for row in rows:
        by_engine[row.engine].append(row)
    engines = []
    for engine, obs in sorted(by_engine.items(), key=lambda kv: kv[0] != SERP_ENGINE):
        answered = [o for o in obs if o.answered]
        sentiments = [o.sentiment for o in answered if o.sentiment is not None]
        ranks = [o.mention_rank for o in answered if o.mention_rank is not None]
        engines.append(
            {
                "engine": engine,
                "samples": len(obs),
                "answer_rate": _rate(len(answered), len(obs)),
                "mention_rate": _rate(sum(o.mentioned for o in answered), len(answered)),
                "citation_rate": _rate(sum(o.cited for o in answered), len(answered)),
                "avg_sentiment": round(sum(sentiments) / len(sentiments), 2)
                if sentiments
                else None,
                "avg_mention_rank": round(sum(ranks) / len(ranks), 1) if ranks else None,
            }
        )
    # Share of voice: brand mentions across all answers, own vs tracked competitors.
    mentions: Counter[str] = Counter()
    citations: Counter[str] = Counter()
    for row in rows:
        if not row.answered:
            continue
        mentions[own_key] += row.mentioned
        citations[own_key] += row.cited
        for domain, facts in (row.competitors or {}).items():
            mentions[domain] += bool(facts.get("mentioned"))
            citations[domain] += bool(facts.get("cited"))
    total = sum(mentions.values())
    share = [
        {
            "domain": domain,
            "is_own": domain == own_key,
            "mentions": mentions[domain],
            "citations": citations[domain],
            "share": round(mentions[domain] / total, 4) if total else None,
        }
        for domain in sorted(mentions, key=lambda d: -mentions[d])
    ]
    per_prompt: dict[uuid.UUID, dict[str, list[AiObservation]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        per_prompt[row.prompt_id][row.engine].append(row)
    organic = await _organic_positions(
        db, project.id, [p.keyword for p in prompts.values() if p.keyword]
    )
    prompt_rows = []
    for prompt_id, prompt in prompts.items():
        cells = {}
        for engine, obs in per_prompt.get(prompt_id, {}).items():
            answered = [o for o in obs if o.answered]
            cells[engine] = {
                "samples": len(obs),
                "answered": len(answered),
                "mentioned": sum(o.mentioned for o in answered),
                "cited": sum(o.cited for o in answered),
            }
        prompt_rows.append(
            {
                "prompt_id": str(prompt_id),
                "prompt": prompt.prompt,
                "keyword": prompt.keyword,
                "active": prompt.active,
                "organic_position": organic.get(prompt.keyword or ""),
                "engines": cells,
            }
        )
    first_party = await _first_party(db, project.id, since)
    return {
        "days": days,
        "engines": engines,
        "share_of_voice": share,
        "prompts": prompt_rows,
        "first_party": first_party,
    }


async def _organic_positions(
    db: AsyncSession, project_id: uuid.UUID, keywords: list[str]
) -> dict[str, float | None]:
    if not keywords:
        return {}
    latest = (
        select(
            TrackedKeyword.keyword,
            RankObservation.position,
            func.row_number()
            .over(
                partition_by=TrackedKeyword.keyword,
                order_by=(RankObservation.date.desc(), RankObservation.source),
            )
            .label("rn"),
        )
        .join(RankObservation, RankObservation.keyword_id == TrackedKeyword.id)
        .where(
            TrackedKeyword.project_id == project_id,
            TrackedKeyword.keyword.in_(keywords),
            RankObservation.is_own.is_(True),
            RankObservation.engine == "google",
        )
        .subquery()
    )
    rows = await db.execute(select(latest.c.keyword, latest.c.position).where(latest.c.rn == 1))
    return dict(rows.tuples().all())


async def _first_party(
    db: AsyncSession, project_id: uuid.UUID, since: date
) -> list[dict[str, Any]]:
    """Imported first-party AI data (GSC Gen-AI report, Bing AI Performance)."""
    rows = await db.execute(
        select(
            AiPerformanceDaily.source,
            AiPerformanceDaily.surface,
            func.sum(AiPerformanceDaily.impressions),
            func.sum(AiPerformanceDaily.clicks),
            func.sum(AiPerformanceDaily.citations),
        )
        .where(AiPerformanceDaily.project_id == project_id, AiPerformanceDaily.date > since)
        .group_by(AiPerformanceDaily.source, AiPerformanceDaily.surface)
    )
    return [
        {
            "source": source,
            "surface": surface,
            "impressions": int(imps or 0),
            "clicks": int(clicks or 0),
            "citations": int(cites or 0),
        }
        for source, surface, imps, clicks, cites in rows
    ]
