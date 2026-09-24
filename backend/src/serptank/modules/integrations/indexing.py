"""URL submission to search engines (IndexNow; Bing Webmaster Tools URL submission).

Submitting URLs for sites you don't own is an abuse vector (plan §5.5), so every
submission requires a project whose domain ownership is verified, and every URL must be
on the project's own host (or its www twin).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.config import Settings
from serptank.core.errors import AppError, ConflictError
from serptank.core.http import SafeHttpClient
from serptank.modules.crawler.models import Crawl, CrawlPage, CrawlStatus
from serptank.modules.crawler.urls import normalize_url, site_hosts
from serptank.modules.integrations.models import IndexNowSubmission, ProjectSource, SourceKind
from serptank.modules.integrations.providers import indexnow
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.bing import BingWebmasterClient
from serptank.modules.projects.models import Project

MAX_MANUAL_URLS = 1000


class SubmissionError(AppError):
    status = 422
    code = "submission_rejected"
    title = "URLs can't be submitted"


def require_verified(project: Project) -> None:
    if project.domain_verified_at is None:
        raise ConflictError("Verify domain ownership before submitting URLs to search engines.")


def clean_urls(project: Project, urls: list[str]) -> list[str]:
    """Normalize, de-duplicate and keep only URLs on the project's hosts."""
    hosts = site_hosts(project.primary_domain)
    cleaned: list[str] = []
    rejected: list[str] = []
    for raw in urls[:MAX_MANUAL_URLS]:
        url = normalize_url(raw)
        if url and (urlsplit(url).hostname or "") in hosts:
            if url not in cleaned:
                cleaned.append(url)
        else:
            rejected.append(raw[:200])
    if rejected:
        raise SubmissionError(
            "Only URLs on this project's domain can be submitted.",
            extra={"rejected": rejected[:10]},
        )
    return cleaned


async def indexnow_source(db: AsyncSession, project_id: uuid.UUID) -> ProjectSource | None:
    return (
        await db.execute(
            select(ProjectSource).where(
                ProjectSource.project_id == project_id, ProjectSource.kind == SourceKind.INDEXNOW
            )
        )
    ).scalar_one_or_none()


async def submit_indexnow(
    db: AsyncSession,
    *,
    project: Project,
    source: ProjectSource,
    urls: list[str],
    http: SafeHttpClient,
    settings: Settings,
    trigger: str,
) -> list[IndexNowSubmission]:
    """Submit (per host), log each request, and commit. Raises ProviderError on refusal."""
    require_verified(project)
    if not source.settings.get("verified"):
        raise ConflictError("Publish and verify the IndexNow key file first.")
    by_host: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        by_host[(urlsplit(url).hostname or "").lower()].append(url)
    logged: list[IndexNowSubmission] = []
    for host, batch in by_host.items():
        for start in range(0, len(batch), indexnow.MAX_URLS):
            chunk = batch[start : start + indexnow.MAX_URLS]
            status: int | None
            try:
                status = await indexnow.submit(
                    http, settings.indexnow_endpoint, host, source.property_id, chunk
                )
            except ProviderError:
                status = None
                raise
            finally:
                entry = IndexNowSubmission(
                    organization_id=project.organization_id,
                    project_id=project.id,
                    channel="indexnow",
                    submitted_at=datetime.now(UTC),
                    url_count=len(chunk),
                    status_code=status,
                    trigger=trigger,
                    urls=chunk[:100],
                )
                db.add(entry)
                logged.append(entry)
                await db.commit()
    return logged


async def submit_bing(
    db: AsyncSession,
    *,
    project: Project,
    site_url: str,
    api_key: str,
    urls: list[str],
    http: SafeHttpClient,
) -> IndexNowSubmission:
    require_verified(project)
    await BingWebmasterClient(http, api_key).submit_urls(site_url, urls)
    entry = IndexNowSubmission(
        organization_id=project.organization_id,
        project_id=project.id,
        channel="bing",
        submitted_at=datetime.now(UTC),
        url_count=len(urls),
        status_code=200,
        trigger="manual",
        urls=urls[:100],
    )
    db.add(entry)
    await db.commit()
    return entry


async def changed_urls_since_previous_crawl(db: AsyncSession, crawl: Crawl) -> list[str]:
    """Indexable URLs that are new or whose content changed since the previous audit."""
    previous = (
        await db.execute(
            select(Crawl.id)
            .where(
                Crawl.project_id == crawl.project_id,
                Crawl.status == CrawlStatus.COMPLETED,
                Crawl.id != crawl.id,
                Crawl.created_at < crawl.created_at,
            )
            .order_by(desc(Crawl.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if previous is None:
        return []  # first audit: nothing to compare with (avoid a blanket submission)
    previous_rows = await db.execute(
        select(CrawlPage.url, CrawlPage.content_hash).where(CrawlPage.crawl_id == previous)
    )
    before: dict[str, str | None] = dict(previous_rows.tuples().all())
    now = await db.execute(
        select(CrawlPage.url, CrawlPage.content_hash).where(
            CrawlPage.crawl_id == crawl.id, CrawlPage.indexable_google.is_(True)
        )
    )
    return [url for url, content_hash in now if url not in before or before[url] != content_hash]


def submission_summary(entries: list[IndexNowSubmission]) -> dict[str, Any]:
    return {"requests": len(entries), "urls": sum(e.url_count for e in entries)}
