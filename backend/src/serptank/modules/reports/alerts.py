"""Alert rules, their evaluation, and notification fan-out (in-app + optional email).

Each evaluator compares the two most recent observations of one signal and returns
events. An event's ``dedupe_key`` is stable for the same change, so evaluating twice
never notifies twice (unique ``(user_id, dedupe_key)``). Events fan out to every member
who can read the project; email goes only to owners/admins/editors when the rule has
``email`` on, and only for notifications that were newly created.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import structlog
from sqlalchemy import desc, distinct, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import EmailSender, OutgoingEmail
from serptank.core.models import MemberRole
from serptank.modules.ai_visibility.models import AiObservation, AiPrompt
from serptank.modules.audit.models import AuditIssue, Severity
from serptank.modules.crawler.models import Crawl, CrawlStatus
from serptank.modules.identity.models import User
from serptank.modules.integrations.models import UrlInspection
from serptank.modules.integrations.providers.crux import assess
from serptank.modules.integrations.sync import latest_vitals
from serptank.modules.jobs.service import JobContext, JobFailedError, register_handler
from serptank.modules.projects.models import Project, ProjectMarket
from serptank.modules.reports.models import AlertRule, Notification
from serptank.modules.reports.presence import presence
from serptank.modules.search_data.models import RankObservation, TrackedKeyword
from serptank.modules.tenancy.models import Membership

logger = structlog.get_logger(__name__)

JOB_KIND = "evaluate_alerts"
MAX_EVENTS = 50  # per rule per evaluation; the rest are summarised
READERS = (MemberRole.OWNER, MemberRole.ADMIN, MemberRole.EDITOR, MemberRole.VIEWER)
EMAIL_ROLES = (MemberRole.OWNER, MemberRole.ADMIN, MemberRole.EDITOR)

# kind -> (label, default threshold, threshold meaning)
KINDS: dict[str, tuple[str, float | None, str | None]] = {
    "rank_drop": ("Ranking drops on Google", 3.0, "positions lost"),
    "ai_citation_lost": ("Lost AI citations", None, None),
    "audit_regression": ("Site audit regressions", 5.0, "score points lost"),
    "cwv_poor": ("Core Web Vitals failing", None, None),
    "indexing_lost": ("Pages dropped from Google's index", None, None),
    "weekly_digest": ("Weekly summary", None, None),
}


@dataclass
class Event:
    title: str
    body: str
    dedupe_key: str
    link: str | None = None


Evaluator = Callable[[AsyncSession, Project, AlertRule, str], Awaitable[list[Event]]]


async def _two_dates(db: AsyncSession, column: Any, *where: Any) -> list[date]:
    rows = await db.execute(select(distinct(column)).where(*where).order_by(desc(column)).limit(2))
    return list(rows.scalars())


async def rank_drop(db: AsyncSession, project: Project, rule: AlertRule, base: str) -> list[Event]:
    threshold = rule.threshold or 3.0
    scope = (
        RankObservation.project_id == project.id,
        RankObservation.is_own.is_(True),
        RankObservation.engine == "google",
        RankObservation.source == "serp",
    )
    dates = await _two_dates(db, RankObservation.date, *scope)
    if len(dates) < 2:  # noqa: PLR2004
        return []
    latest, previous = dates
    rows = await db.execute(
        select(RankObservation.keyword_id, RankObservation.date, RankObservation.position).where(
            *scope, RankObservation.date.in_(dates)
        )
    )
    by_kw: dict[uuid.UUID, dict[date, float | None]] = {}
    for kid, day, position in rows:
        by_kw.setdefault(kid, {})[day] = position
    names = dict(
        (
            await db.execute(
                select(TrackedKeyword.id, TrackedKeyword.keyword).where(
                    TrackedKeyword.id.in_(list(by_kw))
                )
            )
        )
        .tuples()
        .all()
    )
    events = []
    for kid, seen in by_kw.items():
        if previous not in seen or latest not in seen:
            continue
        before, now = seen[previous], seen[latest]
        if before is None:
            continue
        dropped_out = now is None or (before <= 10 and now > 10)  # noqa: PLR2004
        if dropped_out or (now is not None and now - before >= threshold):
            now_text = "out of the top 100" if now is None else f"#{now:g}"
            events.append(
                Event(
                    f"“{names.get(kid, '?')}” fell from #{before:g} to {now_text}",
                    f"Google position changed between {previous} and {latest}.",
                    f"rank_drop:{kid}:{latest}",
                    f"{base}/keywords",
                )
            )
    return events


async def ai_citation_lost(
    db: AsyncSession, project: Project, _rule: AlertRule, base: str
) -> list[Event]:
    scope = (AiObservation.project_id == project.id, AiObservation.answered.is_(True))
    dates = await _two_dates(db, AiObservation.date, *scope)
    if len(dates) < 2:  # noqa: PLR2004
        return []
    latest, previous = dates
    rows = await db.execute(
        select(
            AiObservation.prompt_id,
            AiObservation.engine,
            AiObservation.date,
            func.bool_or(AiObservation.cited),
        )
        .where(*scope, AiObservation.date.in_(dates))
        .group_by(AiObservation.prompt_id, AiObservation.engine, AiObservation.date)
    )
    cited: dict[tuple[uuid.UUID, str], dict[date, bool]] = {}
    for pid, engine, day, was_cited in rows:
        cited.setdefault((pid, engine), {})[day] = bool(was_cited)
    prompts = dict(
        (
            await db.execute(
                select(AiPrompt.id, AiPrompt.prompt).where(AiPrompt.project_id == project.id)
            )
        )
        .tuples()
        .all()
    )
    return [
        Event(
            f"No longer cited by {engine.replace('_', ' ')}",
            f"“{prompts.get(pid, '?')}” cited you on {previous} but not on {latest}.",
            f"ai_citation_lost:{pid}:{engine}:{latest}",
            f"{base}/ai",
        )
        for (pid, engine), seen in cited.items()
        if seen.get(previous) and seen.get(latest) is False
    ]


async def audit_regression(
    db: AsyncSession, project: Project, rule: AlertRule, base: str
) -> list[Event]:
    crawls = list(
        (
            await db.execute(
                select(Crawl)
                .where(Crawl.project_id == project.id, Crawl.status == CrawlStatus.COMPLETED)
                .order_by(desc(Crawl.created_at))
                .limit(2)
            )
        ).scalars()
    )
    if len(crawls) < 2:  # noqa: PLR2004
        return []
    latest, previous = crawls

    async def criticals(crawl_id: uuid.UUID) -> int:
        return int(
            (
                await db.execute(
                    select(func.count()).where(
                        AuditIssue.crawl_id == crawl_id, AuditIssue.severity == Severity.CRITICAL
                    )
                )
            ).scalar_one()
        )

    events = []
    drop = (previous.score or 0) - (latest.score or 0)
    if latest.score is not None and previous.score is not None and drop >= (rule.threshold or 5.0):
        events.append(
            Event(
                f"Audit score fell {drop:.0f} points to {latest.score:.0f}",
                "Compare the latest audit with the previous one to see what changed.",
                f"audit_score:{latest.id}",
                f"{base}/audit",
            )
        )
    new_critical = await criticals(latest.id) - await criticals(previous.id)
    if new_critical > 0:
        events.append(
            Event(
                f"{new_critical} new critical audit issue(s)",
                "Critical issues can stop Google from crawling or indexing the site.",
                f"audit_critical:{latest.id}",
                f"{base}/audit",
            )
        )
    return events


async def cwv_poor(db: AsyncSession, project: Project, _rule: AlertRule, base: str) -> list[Event]:
    events = []
    for v in await latest_vitals(db, project.id):
        if assess({"lcp_ms": v.lcp_ms, "inp_ms": v.inp_ms, "cls": v.cls}) == "poor":
            events.append(
                Event(
                    f"Core Web Vitals are poor ({v.form_factor})",
                    f"Field data for {v.target} fails the Core Web Vitals assessment.",
                    f"cwv_poor:{v.target}:{v.form_factor}:{v.date}",
                    f"{base}/audit",
                )
            )
    return events


async def indexing_lost(
    db: AsyncSession, project: Project, _rule: AlertRule, base: str
) -> list[Event]:
    ranked = (
        select(
            UrlInspection.url,
            UrlInspection.verdict,
            UrlInspection.inspected_at,
            func.row_number()
            .over(partition_by=UrlInspection.url, order_by=UrlInspection.inspected_at.desc())
            .label("rn"),
        )
        .where(UrlInspection.project_id == project.id)
        .subquery()
    )
    rows = await db.execute(
        select(ranked.c.url, ranked.c.verdict, ranked.c.inspected_at, ranked.c.rn).where(
            ranked.c.rn <= 2  # noqa: PLR2004
        )
    )
    history: dict[str, dict[int, tuple[str | None, datetime]]] = {}
    for url, verdict, at, rn in rows:
        history.setdefault(url, {})[rn] = (verdict, at)
    return [
        Event(
            "A page is no longer indexed by Google",
            f"{url} was indexed, but the latest URL Inspection says “{seen[1][0] or 'unknown'}”.",
            f"indexing_lost:{url}:{seen[1][1].isoformat()}",
            f"{base}/search",
        )
        for url, seen in history.items()
        if 2 in seen and seen[2][0] == "PASS" and seen[1][0] != "PASS"  # noqa: PLR2004
    ]


async def weekly_digest(
    db: AsyncSession, project: Project, _rule: AlertRule, base: str
) -> list[Event]:
    today = datetime.now(UTC).date()
    if today.weekday() != 0:  # Mondays
        return []
    market = (
        await db.execute(
            select(ProjectMarket).where(ProjectMarket.project_id == project.id).limit(1)
        )
    ).scalar_one_or_none()
    if market is None:
        return []
    data = await presence(db, project, market)
    parts = [
        f"Search Presence Score: {data['score'] if data['score'] is not None else 'no data yet'}"
    ]
    if data["gsc"]:
        cur, prev = data["gsc"]["current"], data["gsc"]["previous"]
        parts.append(f"Google clicks (28 days): {cur['clicks']:,} (previous {prev['clicks']:,})")
    if data["audit"]:
        parts.append(f"Audit score: {data['audit']['score']}")
    year, week, _ = today.isocalendar()
    return [
        Event(
            f"Weekly summary for {project.name}",
            "\n".join(parts),
            f"weekly_digest:{year}-W{week}",
            f"{base}/presence",
        )
    ]


EVALUATORS: dict[str, Evaluator] = {
    "rank_drop": rank_drop,
    "ai_citation_lost": ai_citation_lost,
    "audit_regression": audit_regression,
    "cwv_poor": cwv_poor,
    "indexing_lost": indexing_lost,
    "weekly_digest": weekly_digest,
}


async def fan_out(
    db: AsyncSession,
    project: Project,
    rule: AlertRule,
    events: list[Event],
    email: EmailSender | None,
    public_origin: str,
) -> int:
    """Create notifications for readers; email new ones if the rule asks. Returns count."""
    if not events:
        return 0
    if len(events) > MAX_EVENTS:
        extra = len(events) - MAX_EVENTS + 1
        events = [
            *events[: MAX_EVENTS - 1],
            Event(
                f"…and {extra} more",
                "Open SerpTank for the full list.",
                f"{rule.kind}:overflow:{events[-1].dedupe_key}",
                events[0].link,
            ),
        ]
    members = (
        await db.execute(
            select(Membership.user_id, Membership.role, User.email)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.organization_id == project.organization_id,
                Membership.role.in_(READERS),
                User.deleted_at.is_(None),
            )
        )
    ).all()
    created = 0
    for event in events:
        for user_id, role, address in members:
            inserted = await db.execute(
                pg_insert(Notification)
                .values(
                    id=uuid.uuid4(),
                    organization_id=project.organization_id,
                    user_id=user_id,
                    project_id=project.id,
                    kind=rule.kind,
                    title=event.title[:200],
                    body=event.body,
                    link=event.link,
                    dedupe_key=event.dedupe_key[:200],
                )
                .on_conflict_do_nothing(index_elements=["user_id", "dedupe_key"])
                .returning(Notification.id)
            )
            if inserted.scalar_one_or_none() is None:
                continue
            created += 1
            if rule.email and email is not None and role in EMAIL_ROLES:
                link = f"{public_origin}{event.link}" if event.link else public_origin
                await email.send(
                    OutgoingEmail(
                        to=address,
                        subject=f"[SerpTank] {event.title}"[:200],
                        text=f"{event.body}\n\nOpen in SerpTank: {link}\n\n"
                        "You receive this because email alerts are on for this project.",
                    )
                )
    await db.commit()
    return created


async def evaluate_project(
    db: AsyncSession, project: Project, email: EmailSender | None, public_origin: str
) -> dict[str, int]:
    base = f"/orgs/{project.organization_id}/projects/{project.id}"
    rules = (
        await db.execute(
            select(AlertRule).where(AlertRule.project_id == project.id, AlertRule.active.is_(True))
        )
    ).scalars()
    counts: dict[str, int] = {}
    for rule in list(rules):
        evaluator = EVALUATORS.get(rule.kind)
        if evaluator is None:
            continue
        events = await evaluator(db, project, rule, base)
        counts[rule.kind] = await fan_out(db, project, rule, events, email, public_origin)
        rule.last_evaluated_at = datetime.now(UTC)
        await db.commit()
    return counts


@register_handler(JOB_KIND, queue="reports")
async def run_evaluate_alerts(ctx: JobContext) -> dict[str, Any]:
    async with await ctx.session() as db:
        project = await db.get(Project, ctx.project_id)
        if project is None or project.deleted_at is not None:
            raise JobFailedError("project_gone", "The project no longer exists.")
        counts = await evaluate_project(
            db, project, ctx.runtime.extras.get("email"), ctx.runtime.settings.public_origin
        )
    return {"notifications": sum(counts.values()), **counts}
