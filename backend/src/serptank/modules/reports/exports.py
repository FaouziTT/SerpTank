"""CSV exports: built by a job, kept 24 h, downloaded through short-lived signed links.

A download link is ``/api/v1/exports/{org}/{export}?exp=<unix>&sig=<hmac>``. The HMAC
covers org, export id and expiry, with a key derived from the session secret for this
purpose only (``HMAC(session_secret, "serptank/export-link/v1")``), so a link can be
shared with a colleague's browser or a script for 15 minutes without a session - and
can't be forged, extended, or pointed at another export or tenant.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.modules.ai_visibility.models import AiObservation, AiPrompt
from serptank.modules.audit.models import AuditIssue
from serptank.modules.crawler.models import Crawl, CrawlStatus
from serptank.modules.integrations.models import GscDaily
from serptank.modules.jobs.service import JobContext, JobFailedError, register_handler
from serptank.modules.reports.csvsafe import to_csv
from serptank.modules.reports.models import Export
from serptank.modules.search_data.models import RankObservation, TrackedKeyword

JOB_KIND = "export"
LINK_TTL = timedelta(minutes=15)
KEEP_FOR = timedelta(hours=24)
MAX_ROWS = 100_000
MAX_BYTES = 20 * 1024 * 1024

Rows = AsyncIterator[list[Any]]


# --------------------------------------------------------------------------- signing
def _key(session_secret: str) -> bytes:
    return hmac.new(session_secret.encode(), b"serptank/export-link/v1", hashlib.sha256).digest()


def sign(session_secret: str, org_id: uuid.UUID, export_id: uuid.UUID, expires: int) -> str:
    message = f"{org_id}:{export_id}:{expires}".encode()
    return hmac.new(_key(session_secret), message, hashlib.sha256).hexdigest()


def verify(
    session_secret: str, org_id: uuid.UUID, export_id: uuid.UUID, expires: int, signature: str
) -> bool:
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(sign(session_secret, org_id, export_id, expires), signature)


def signed_path(
    session_secret: str, org_id: uuid.UUID, export_id: uuid.UUID
) -> tuple[str, datetime]:
    expires = int(time.time() + LINK_TTL.total_seconds())
    sig = sign(session_secret, org_id, export_id, expires)
    return (
        f"/api/v1/exports/{org_id}/{export_id}?exp={expires}&sig={sig}",
        datetime.fromtimestamp(expires, UTC),
    )


# ---------------------------------------------------------------------- export kinds
async def _rankings(db: AsyncSession, project_id: uuid.UUID) -> Rows:
    rows = await db.stream(
        select(
            RankObservation.date,
            TrackedKeyword.keyword,
            RankObservation.engine,
            RankObservation.source,
            RankObservation.domain,
            RankObservation.is_own,
            RankObservation.position,
            RankObservation.url,
            RankObservation.ai_cited,
        )
        .join(TrackedKeyword, TrackedKeyword.id == RankObservation.keyword_id)
        .where(RankObservation.project_id == project_id)
        .order_by(desc(RankObservation.date), TrackedKeyword.keyword)
        .limit(MAX_ROWS)
    )
    async for row in rows:
        yield list(row)


async def _audit_issues(db: AsyncSession, project_id: uuid.UUID) -> Rows:
    crawl_id = (
        await db.execute(
            select(Crawl.id)
            .where(Crawl.project_id == project_id, Crawl.status == CrawlStatus.COMPLETED)
            .order_by(desc(Crawl.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if crawl_id is None:
        return
    rows = await db.stream(
        select(AuditIssue.rule_id, AuditIssue.severity, AuditIssue.scope, AuditIssue.url)
        .where(AuditIssue.crawl_id == crawl_id)
        .order_by(AuditIssue.severity, AuditIssue.rule_id)
        .limit(MAX_ROWS)
    )
    async for rule, severity, scope, url in rows:
        yield [rule, severity.value, scope, url]


async def _gsc_queries(db: AsyncSession, project_id: uuid.UUID) -> Rows:
    latest: date | None = (
        await db.execute(select(func.max(GscDaily.date)).where(GscDaily.project_id == project_id))
    ).scalar_one()
    if latest is None:
        return
    imps = func.sum(GscDaily.impressions)
    rows = await db.stream(
        select(
            GscDaily.query,
            GscDaily.page,
            func.sum(GscDaily.clicks),
            imps,
            func.sum(GscDaily.position * GscDaily.impressions) / func.nullif(imps, 0),
        )
        .where(GscDaily.project_id == project_id, GscDaily.date > latest - timedelta(days=28))
        .group_by(GscDaily.query, GscDaily.page)
        .order_by(desc(imps))
        .limit(MAX_ROWS)
    )
    async for query, page, clicks, impressions, position in rows:
        ctr = round(clicks / impressions, 4) if impressions else None
        yield [query, page, clicks, impressions, ctr, round(position or 0, 1)]


async def _ai_answers(db: AsyncSession, project_id: uuid.UUID) -> Rows:
    rows = await db.stream(
        select(
            AiObservation.date,
            AiObservation.engine,
            AiPrompt.prompt,
            AiObservation.sample,
            AiObservation.answered,
            AiObservation.mentioned,
            AiObservation.cited,
            AiObservation.citations,
            AiObservation.excerpt,
        )
        .join(AiPrompt, AiPrompt.id == AiObservation.prompt_id)
        .where(AiObservation.project_id == project_id)
        .order_by(desc(AiObservation.date))
        .limit(MAX_ROWS)
    )
    async for row in rows:
        values = list(row)
        values[7] = " ".join(values[7] or [])
        yield values


KINDS: dict[str, tuple[list[str], Callable[[AsyncSession, uuid.UUID], Rows]]] = {
    "rankings": (
        ["date", "keyword", "engine", "source", "domain", "is_own", "position", "url", "ai_cited"],
        _rankings,
    ),
    "audit_issues": (["rule", "severity", "scope", "url"], _audit_issues),
    "gsc_queries": (["query", "page", "clicks", "impressions", "ctr", "position"], _gsc_queries),
    "ai_answers": (
        [
            "date",
            "engine",
            "prompt",
            "sample",
            "answered",
            "mentioned",
            "cited",
            "citations",
            "excerpt",
        ],
        _ai_answers,
    ),
}


async def _collect(rows: Rows) -> list[list[Any]]:
    return [row async for row in rows]


@register_handler(JOB_KIND, queue="reports")
async def run_export(ctx: JobContext) -> dict[str, Any]:
    async with await ctx.session() as db:
        export = await db.get(Export, uuid.UUID(str(ctx.params.get("id"))))
        if export is None:
            raise JobFailedError("export_gone", "The export no longer exists.")
        header, build = KINDS[export.kind]
        try:
            content, count = to_csv(header, await _collect(build(db, export.project_id)))
            if len(content) > MAX_BYTES:
                raise JobFailedError("export_too_large", "The export is larger than 20 MB.")
        except JobFailedError as exc:
            export.status, export.error = "failed", exc.message
            await db.commit()
            raise
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
        export.content = content
        export.rows = count
        export.filename = f"serptank-{export.kind}-{stamp}.csv"
        export.status = "completed"
        export.expires_at = datetime.now(UTC) + KEEP_FOR
        await db.commit()
        return {"rows": count, "bytes": len(content)}


async def purge_expired(system: AsyncSession) -> int:
    """Drop expired export contents (scheduler session; keeps the row for history)."""
    result = await system.execute(
        update(Export)
        .where(Export.expires_at < datetime.now(UTC), Export.content.is_not(None))
        .values(content=None, status="expired")
    )
    await system.commit()
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
