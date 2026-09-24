"""Keywords, rankings, competitors, research: ``/orgs/{org}/projects/{project}/keywords``."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.errors import AppError, ConflictError, NotFoundError
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.billing.entitlements import PlanLimitError, plan_for
from serptank.modules.crawler.urls import site_hosts
from serptank.modules.identity.deps import DbSession, Identity
from serptank.modules.integrations.credentials import (
    bing_api_key,
    get_connection,
    google_access_token,
)
from serptank.modules.integrations.models import GscDaily, Provider
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.bing import BingWebmasterClient
from serptank.modules.integrations.providers.google_ads import KeywordPlannerClient
from serptank.modules.integrations.providers.google_oauth import SCOPES
from serptank.modules.integrations.router_org import provider_problem
from serptank.modules.jobs.schemas import JobOut
from serptank.modules.jobs.service import JobDispatcher, create_job
from serptank.modules.keywords import ctr as ctr_curve
from serptank.modules.keywords import difficulty as kd
from serptank.modules.keywords.intent import classify
from serptank.modules.keywords.ranks import JOB_KIND
from serptank.modules.keywords.schemas import (
    AnalyzeOut,
    AnalyzeRequest,
    CompetitorIn,
    CompetitorOut,
    DifficultyOut,
    KeywordIdeaOut,
    KeywordsAdd,
    KeywordsAdded,
    OpportunitiesOut,
    OpportunityOut,
    PositionOut,
    ResearchOut,
    ResearchRequest,
    SerpResultOut,
    ShareOfVoiceOut,
    ShareOfVoiceRow,
    TrackedKeywordOut,
)
from serptank.modules.keywords.serp_stats import domain_frequency
from serptank.modules.projects.domains import InvalidDomainError, normalize_domain
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.projects.router import ProjectRepository
from serptank.modules.search_data.collector import CollectorRouter, SerpUnavailableError
from serptank.modules.search_data.models import (
    Competitor,
    KeywordMetrics,
    RankObservation,
    TrackedKeyword,
)
from serptank.modules.search_data.schema import SerpRequest, normalize_query
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/projects/{project_id}", tags=["keywords"])
ProjectRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
ProjectWrite = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_WRITE))]
_RESEARCH_RATE = rate_limit("keyword-research", Rate(60, 3600))
_ANALYZE_RATE = rate_limit("serp-analyze", Rate(60, 3600))
HISTORY_DAYS = 60


class DataUnavailableError(AppError):
    status = 503
    code = "data_unavailable"
    title = "Data is unavailable right now"


async def _project(db: AsyncSession, ctx: OrgContext, project_id: uuid.UUID) -> Project:
    return await ProjectRepository(db, ctx.organization_id).get(project_id)


async def _market(db: AsyncSession, project: Project, market_id: uuid.UUID) -> ProjectMarket:
    market = await db.get(ProjectMarket, market_id)
    if market is None or market.project_id != project.id:
        raise NotFoundError("Market not found.")
    return market


def _serp_router(request: Request) -> CollectorRouter:
    router_: CollectorRouter = request.app.state.job_runtime.extras["serp"]
    return router_


# ------------------------------------------------------------------ tracked keywords
@router.post("/keywords", response_model=KeywordsAdded, status_code=201)
async def add_keywords(
    project_id: uuid.UUID, body: KeywordsAdd, ctx: ProjectWrite, db: DbSession
) -> KeywordsAdded:
    project = await _project(db, ctx, project_id)
    market = await _market(db, project, body.market_id)
    plan = plan_for(ctx.organization.plan_code)
    used = int(
        (
            await db.execute(
                select(func.count())
                .select_from(TrackedKeyword)
                .where(TrackedKeyword.organization_id == ctx.organization_id)
            )
        ).scalar_one()
    )
    wanted = [k for k in dict.fromkeys(normalize_query(k) for k in body.keywords) if k]
    existing = set(
        (
            await db.execute(
                select(TrackedKeyword.keyword).where(TrackedKeyword.market_id == market.id)
            )
        ).scalars()
    )
    new = [k for k in wanted if k not in existing]
    if used + len(new) > plan.max_tracked_keywords:
        raise PlanLimitError(
            f"Your {plan.name} plan tracks up to {plan.max_tracked_keywords:,} keywords "
            f"({used:,} in use).",
            extra={"limit": plan.max_tracked_keywords, "resource": "tracked keywords"},
        )
    tags = [t.strip()[:50] for t in body.tags if t.strip()]
    if new:
        await db.execute(
            pg_insert(TrackedKeyword)
            .values(
                [
                    {
                        "id": uuid.uuid4(),
                        "organization_id": ctx.organization_id,
                        "project_id": project.id,
                        "market_id": market.id,
                        "keyword": k,
                        "tags": tags,
                    }
                    for k in new
                ]
            )
            .on_conflict_do_nothing()
        )
    await db.commit()
    return KeywordsAdded(
        added=len(new),
        skipped_existing=len(wanted) - len(new),
        limit=plan.max_tracked_keywords,
        used=used + len(new),
    )


async def _volumes(
    db: AsyncSession, keywords: list[str], market: ProjectMarket | None
) -> dict[str, tuple[int | None, str]]:
    if not keywords:
        return {}
    stmt = select(KeywordMetrics).where(KeywordMetrics.keyword.in_(keywords))
    if market is not None:
        stmt = stmt.where(KeywordMetrics.country == market.country)
    out: dict[str, tuple[int | None, str]] = {}
    for metric in (await db.execute(stmt)).scalars():
        # Official Google Ads data wins over Bing impressions.
        if metric.keyword not in out or metric.source == "google_ads":
            out[metric.keyword] = (metric.avg_monthly_searches, metric.source)
    return out


@router.get("/keywords", response_model=list[TrackedKeywordOut])
async def list_keywords(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    market_id: uuid.UUID | None = None,
    tag: Annotated[str | None, Query(max_length=50)] = None,
) -> list[TrackedKeywordOut]:
    project = await _project(db, ctx, project_id)
    stmt = select(TrackedKeyword).where(TrackedKeyword.project_id == project.id)
    if market_id:
        stmt = stmt.where(TrackedKeyword.market_id == market_id)
    if tag:
        stmt = stmt.where(TrackedKeyword.tags.contains([tag]))
    keywords = list((await db.execute(stmt.order_by(TrackedKeyword.keyword).limit(2000))).scalars())
    since = datetime.now(UTC).date() - timedelta(days=HISTORY_DAYS)
    history: dict[tuple[uuid.UUID, str, str], list[RankObservation]] = defaultdict(list)
    if keywords:
        rows = await db.execute(
            select(RankObservation)
            .where(
                RankObservation.project_id == project.id,
                RankObservation.is_own.is_(True),
                RankObservation.date >= since,
                RankObservation.keyword_id.in_([k.id for k in keywords]),
            )
            .order_by(RankObservation.date.desc())
        )
        for obs in rows.scalars():
            history[(obs.keyword_id, obs.engine, obs.source)].append(obs)
    volumes = await _volumes(db, [k.keyword for k in keywords], None)
    out: list[TrackedKeywordOut] = []
    for keyword in keywords:
        positions: list[PositionOut] = []
        features: list[str] = []
        for (keyword_id, engine, source), series in sorted(
            history.items(), key=lambda kv: (kv[0][1] != "google", kv[0][1], kv[0][2])
        ):
            if keyword_id != keyword.id:
                continue
            latest = series[0]
            previous = next((o for o in series[1:] if o.date < latest.date), None)
            features = features or list(latest.features)
            positions.append(
                PositionOut(
                    engine=engine,
                    source=source,
                    position=latest.position,
                    previous=previous.position if previous else None,
                    date=latest.date,
                    url=latest.url,
                    features=list(latest.features),
                    ai_cited=latest.ai_cited,
                )
            )
        volume, volume_source = volumes.get(keyword.keyword, (None, None))
        out.append(
            TrackedKeywordOut(
                id=keyword.id,
                keyword=keyword.keyword,
                market_id=keyword.market_id,
                tags=list(keyword.tags),
                intent=classify(keyword.keyword, features).primary,
                volume=volume,
                volume_source=volume_source,
                positions=positions,
            )
        )
    return out


@router.delete("/keywords/{keyword_id}", status_code=204)
async def delete_keyword(
    project_id: uuid.UUID, keyword_id: uuid.UUID, ctx: ProjectWrite, db: DbSession
) -> None:
    await _project(db, ctx, project_id)
    result = await db.execute(
        delete(TrackedKeyword)
        .where(TrackedKeyword.id == keyword_id, TrackedKeyword.project_id == project_id)
        .returning(TrackedKeyword.id)
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("Keyword not found.")
    await db.commit()


@router.post("/keywords/check", response_model=JobOut, status_code=202)
async def check_rankings(
    project_id: uuid.UUID, ctx: ProjectWrite, db: DbSession, request: Request
) -> JobOut:
    project = await _project(db, ctx, project_id)
    job = await create_job(
        db,
        organization_id=ctx.organization_id,
        kind=JOB_KIND,
        project_id=project.id,
        user_id=ctx.actor_user_id,
    )
    dispatcher: JobDispatcher = request.app.state.job_dispatcher
    await dispatcher.dispatch(job)
    return JobOut.model_validate(job)


# ----------------------------------------------------------------------- competitors
@router.get("/competitors", response_model=list[CompetitorOut])
async def list_competitors(
    project_id: uuid.UUID, ctx: ProjectRead, db: DbSession
) -> list[Competitor]:
    await _project(db, ctx, project_id)
    return list(
        (
            await db.execute(
                select(Competitor)
                .where(Competitor.project_id == project_id)
                .order_by(Competitor.domain)
            )
        ).scalars()
    )


@router.post("/competitors", response_model=CompetitorOut, status_code=201)
async def add_competitor(
    project_id: uuid.UUID, body: CompetitorIn, ctx: ProjectWrite, db: DbSession
) -> Competitor:
    project = await _project(db, ctx, project_id)
    try:
        domain = normalize_domain(body.domain)
    except InvalidDomainError as exc:
        raise ConflictError(str(exc)) from exc
    if domain in site_hosts(project.primary_domain):
        raise ConflictError("That's this project's own domain.")
    count = int(
        (
            await db.execute(select(func.count()).where(Competitor.project_id == project.id))
        ).scalar_one()
    )
    if count >= 10:  # noqa: PLR2004
        raise ConflictError("A project can compare against up to 10 competitors.")
    competitor = Competitor(
        organization_id=ctx.organization_id, project_id=project.id, domain=domain, label=body.label
    )
    db.add(competitor)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise ConflictError("That competitor is already added.") from exc
    return competitor


@router.delete("/competitors/{competitor_id}", status_code=204)
async def delete_competitor(
    project_id: uuid.UUID, competitor_id: uuid.UUID, ctx: ProjectWrite, db: DbSession
) -> None:
    await _project(db, ctx, project_id)
    await db.execute(
        delete(Competitor).where(
            Competitor.id == competitor_id, Competitor.project_id == project_id
        )
    )
    await db.commit()


@router.get("/keywords/share-of-voice", response_model=ShareOfVoiceOut)
async def share_of_voice(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    market_id: uuid.UUID,
    engine: Annotated[str, Query(max_length=20)] = "google",
) -> ShareOfVoiceOut:
    project = await _project(db, ctx, project_id)
    market = await _market(db, project, market_id)
    keywords = {
        k.id: k.keyword
        for k in (
            await db.execute(select(TrackedKeyword).where(TrackedKeyword.market_id == market.id))
        ).scalars()
    }
    latest: date | None = (
        await db.execute(
            select(func.max(RankObservation.date)).where(
                RankObservation.project_id == project.id,
                RankObservation.source == "serp",
                RankObservation.engine == engine,
                RankObservation.keyword_id.in_(list(keywords) or [uuid.uuid4()]),
            )
        )
    ).scalar_one()
    if latest is None:
        return ShareOfVoiceOut(
            engine=engine, date=None, keywords=len(keywords), volumes_known=False, rows=[]
        )
    rows = list(
        (
            await db.execute(
                select(RankObservation).where(
                    RankObservation.project_id == project.id,
                    RankObservation.source == "serp",
                    RankObservation.engine == engine,
                    RankObservation.date == latest,
                    RankObservation.keyword_id.in_(list(keywords)),
                )
            )
        ).scalars()
    )
    volumes = await _volumes(db, list(keywords.values()), market)
    by_domain: dict[str, list[RankObservation]] = defaultdict(list)
    for obs in rows:
        by_domain[obs.domain].append(obs)
    out_rows: list[ShareOfVoiceRow] = []
    for domain, observations in by_domain.items():
        pairs = [
            (o.position, volumes.get(keywords.get(o.keyword_id, ""), (None, ""))[0])
            for o in observations
        ]
        ranked = [o.position for o in observations if o.position is not None]
        out_rows.append(
            ShareOfVoiceRow(
                domain=domain,
                is_own=observations[0].is_own,
                share=ctr_curve.share_of_voice(pairs),
                keywords_ranking=len(ranked),
                average_position=round(sum(ranked) / len(ranked), 1) if ranked else None,
            )
        )
    out_rows.sort(key=lambda r: -r.share)
    return ShareOfVoiceOut(
        engine=engine,
        date=latest,
        keywords=len(keywords),
        volumes_known=bool(volumes),
        rows=out_rows,
    )


# -------------------------------------------------------------------------- research
@router.post(
    "/keywords/research", response_model=ResearchOut, dependencies=[Depends(_RESEARCH_RATE)]
)
async def research(
    project_id: uuid.UUID,
    body: ResearchRequest,
    ctx: ProjectRead,
    db: DbSession,
    identity: Identity,
) -> ResearchOut:
    """Keyword ideas from official sources: Google Ads Keyword Planner, else Bing."""
    project = await _project(db, ctx, project_id)
    market = await _market(db, project, body.market_id)
    settings = identity.settings
    tracked = set(
        (
            await db.execute(
                select(TrackedKeyword.keyword).where(TrackedKeyword.market_id == market.id)
            )
        ).scalars()
    )
    today = datetime.now(UTC).date()
    google = await get_connection(db, ctx.organization_id, Provider.GOOGLE)
    customer = (google.settings or {}).get("ads_customer_id") if google else None
    ideas: list[KeywordIdeaOut] = []
    try:
        if (
            google
            and customer
            and SCOPES["ads"] in google.scopes
            and settings.google_ads_developer_token.get_secret_value()
        ):
            token = await google_access_token(
                db,
                ctx.organization_id,
                keyring=identity.keyring,
                settings=settings,
                http=identity.http,
            )
            planner = KeywordPlannerClient(
                identity.http,
                access_token=token,
                developer_token=settings.google_ads_developer_token.get_secret_value(),
                api_version=settings.google_ads_api_version,
                login_customer_id=settings.google_ads_login_customer_id,
            )
            results = await planner.ideas(
                str(customer), [body.seed], market.country, market.language
            )
            for idea in results[:200]:
                keyword = normalize_query(idea.keyword)
                await _store_metric(
                    db,
                    keyword,
                    market,
                    "google_ads",
                    idea.avg_monthly_searches,
                    idea.competition,
                    idea.low_bid_micros,
                    idea.high_bid_micros,
                    idea.monthly,
                    today,
                )
                intent = classify(keyword)
                ideas.append(
                    KeywordIdeaOut(
                        keyword=keyword,
                        volume=idea.avg_monthly_searches,
                        volume_source="google_ads",
                        competition=idea.competition,
                        cpc_low=idea.low_bid_micros / 1e6 if idea.low_bid_micros else None,
                        cpc_high=idea.high_bid_micros / 1e6 if idea.high_bid_micros else None,
                        intent=intent.primary,
                        intent_reasons=intent.reasons,
                        difficulty=None,
                        tracked=keyword in tracked,
                    )
                )
            await db.commit()
            return ResearchOut(source="google_ads", ideas=ideas)
        if await get_connection(db, ctx.organization_id, Provider.BING):
            key = await bing_api_key(db, ctx.organization_id, identity.keyring)
            rows = await BingWebmasterClient(identity.http, key).related_keywords(
                body.seed, market.country, market.language, today - timedelta(days=30), today
            )
            for row in rows[:200]:
                keyword = normalize_query(str(row.get("Query", "")))
                if not keyword:
                    continue
                impressions = int(row.get("Impressions") or 0)
                await _store_metric(
                    db, keyword, market, "bing", impressions, None, None, None, [], today
                )
                intent = classify(keyword)
                ideas.append(
                    KeywordIdeaOut(
                        keyword=keyword,
                        volume=impressions,
                        volume_source="bing",
                        competition=None,
                        cpc_low=None,
                        cpc_high=None,
                        intent=intent.primary,
                        intent_reasons=intent.reasons,
                        difficulty=None,
                        tracked=keyword in tracked,
                    )
                )
            await db.commit()
            return ResearchOut(source="bing", ideas=ideas)
    except ProviderError as exc:
        raise provider_problem(exc) from exc
    raise ConflictError(
        "Connect Google Ads (Keyword Planner) or Bing Webmaster Tools to research keywords."
    )


async def _store_metric(
    db: AsyncSession,
    keyword: str,
    market: ProjectMarket,
    source: str,
    volume: int | None,
    competition: str | None,
    low: int | None,
    high: int | None,
    monthly: list[dict[str, Any]],
    today: date,
) -> None:
    values = {
        "id": uuid.uuid4(),
        "keyword": keyword,
        "country": market.country,
        "language": market.language,
        "source": source,
        "avg_monthly_searches": volume,
        "competition": competition,
        "cpc_low_micros": low,
        "cpc_high_micros": high,
        "monthly": monthly,
        "fetched_on": today,
    }
    stmt = pg_insert(KeywordMetrics).values(**values)
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=["keyword", "country", "language", "source"],
            set_={k: stmt.excluded[k] for k in values if k != "id"},
        )
    )


@router.post("/keywords/analyze", response_model=AnalyzeOut, dependencies=[Depends(_ANALYZE_RATE)])
async def analyze(
    project_id: uuid.UUID, body: AnalyzeRequest, ctx: ProjectWrite, db: DbSession, request: Request
) -> AnalyzeOut:
    """Fetch (or reuse the cached) SERP for a keyword and explain it: KD, intent, features."""
    project = await _project(db, ctx, project_id)
    market = await _market(db, project, body.market_id)
    plan = plan_for(ctx.organization.plan_code)
    if body.engine not in {e.value for e in plan.search_engines}:
        raise PlanLimitError(
            f"Your {plan.name} plan doesn't include {body.engine}.",
            extra={"missing": [body.engine]},
        )
    serp_request = SerpRequest(
        engine=body.engine,
        query=body.keyword,
        country=market.country,
        language=market.language,
        device=market.device.value,
        location=market.location,
    )
    try:
        serp = await _serp_router(request).get(
            db,
            serp_request,
            organization_id=ctx.organization_id,
            org_daily_cap=plan.serp_requests_per_day,
        )
    except SerpUnavailableError as exc:
        raise DataUnavailableError(exc.message, extra={"reason": exc.code}) from exc
    data = serp.data
    frequency, size = await domain_frequency(db, body.engine, [r.domain for r in data.organic[:10]])
    difficulty = kd.compute(data, frequency, size)
    intent = classify(data.query, data.features)
    own = site_hosts(project.primary_domain)
    rivals = {
        c.domain
        for c in (
            await db.execute(select(Competitor).where(Competitor.project_id == project.id))
        ).scalars()
    }
    rival_hosts = set().union(*(site_hosts(d) for d in rivals)) if rivals else set()
    return AnalyzeOut(
        keyword=data.query,
        engine=body.engine,
        fetched_on=serp.fetched_on,
        from_cache=serp.from_cache,
        intent=intent.primary,
        intent_reasons=intent.reasons,
        difficulty=DifficultyOut(**difficulty.__dict__),
        features=data.features,
        ai_answer_cites=data.ai_answer.cited_urls[:20] if data.ai_answer else [],
        people_also_ask=data.people_also_ask,
        results=[
            SerpResultOut(
                position=r.position,
                url=r.url,
                domain=r.domain,
                title=r.title,
                is_own=r.domain in own,
                is_competitor=r.domain in rival_hosts,
            )
            for r in data.organic[:20]
        ],
    )


# --------------------------------------------------------------------- opportunities
STRIKING_MIN_IMPRESSIONS = 50
LOW_CTR_MIN_IMPRESSIONS = 100


@router.get("/keywords/opportunities", response_model=OpportunitiesOut)
async def opportunities(
    project_id: uuid.UUID,
    ctx: ProjectRead,
    db: DbSession,
    days: Annotated[int, Query(ge=7, le=90)] = 28,
) -> OpportunitiesOut:
    """Search Console queries worth working on: 'striking distance' (8-20) and low CTR."""
    project = await _project(db, ctx, project_id)
    latest: date | None = (
        await db.execute(select(func.max(GscDaily.date)).where(GscDaily.project_id == project.id))
    ).scalar_one()
    if latest is None:
        return OpportunitiesOut(
            has_data=False, curve_source="default", date_from=None, date_to=None, items=[]
        )
    start = latest - timedelta(days=days - 1)
    rows = (
        await db.execute(
            select(
                GscDaily.query,
                func.sum(GscDaily.clicks),
                func.sum(GscDaily.impressions),
                func.sum(GscDaily.position * GscDaily.impressions)
                / func.nullif(func.sum(GscDaily.impressions), 0),
            )
            .where(GscDaily.project_id == project.id, GscDaily.date.between(start, latest))
            .group_by(GscDaily.query)
        )
    ).all()
    aggregates = [(str(q), int(c), int(i), float(p)) for q, c, i, p in rows if p is not None and i]
    curve, own_curve = ctr_curve.fit_curve((p, c, i) for _, c, i, p in aggregates)
    tracked = set(
        (
            await db.execute(
                select(TrackedKeyword.keyword).where(TrackedKeyword.project_id == project.id)
            )
        ).scalars()
    )
    items: list[OpportunityOut] = []
    for query, clicks, impressions, position in aggregates:
        actual = clicks / impressions
        if 8 <= position <= 20 and impressions >= STRIKING_MIN_IMPRESSIONS:  # noqa: PLR2004
            target = ctr_curve.expected_ctr(3, curve)
            potential = max(0, round(impressions * target) - clicks)
            items.append(
                OpportunityOut(
                    query=query,
                    kind="striking_distance",
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(actual, 4),
                    position=round(position, 1),
                    expected_ctr=round(target, 4),
                    potential_clicks=potential,
                    tracked=normalize_query(query) in tracked,
                )
            )
        elif position < 8 and impressions >= LOW_CTR_MIN_IMPRESSIONS:  # noqa: PLR2004
            expected = ctr_curve.expected_ctr(position, curve)
            if actual < expected * 0.5:
                items.append(
                    OpportunityOut(
                        query=query,
                        kind="low_ctr",
                        clicks=clicks,
                        impressions=impressions,
                        ctr=round(actual, 4),
                        position=round(position, 1),
                        expected_ctr=round(expected, 4),
                        potential_clicks=max(0, round(impressions * expected) - clicks),
                        tracked=normalize_query(query) in tracked,
                    )
                )
    items.sort(key=lambda o: -o.potential_clicks)
    return OpportunitiesOut(
        has_data=True,
        curve_source="own" if own_curve else "default",
        date_from=start,
        date_to=latest,
        items=items[:200],
    )
