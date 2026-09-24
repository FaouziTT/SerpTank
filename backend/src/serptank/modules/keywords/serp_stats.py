"""Statistics over the global SERP cache (used by keyword difficulty)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.modules.search_data.models import SerpSnapshot

WINDOW_DAYS = 30


async def domain_frequency(
    db: AsyncSession, engine: str, domains: list[str]
) -> tuple[dict[str, int], int]:
    """How many cached SERPs (last 30 days) each domain appears in, and the cache size."""
    since = datetime.now(UTC).date() - timedelta(days=WINDOW_DAYS)
    base = (SerpSnapshot.engine == engine, SerpSnapshot.fetched_on >= since)
    size = int((await db.execute(select(func.count()).where(*base))).scalar_one())
    counts: dict[str, int] = {}
    for domain in dict.fromkeys(domains):
        probe = literal([{"domain": domain}], type_=JSONB)
        counts[domain] = int(
            (
                await db.execute(
                    select(func.count()).where(*base, SerpSnapshot.data["organic"].contains(probe))
                )
            ).scalar_one()
        )
    return counts, size
