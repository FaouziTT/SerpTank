"""Collector router: cache first, then vendors in configured order with failover.

* **Global public-SERP cache.** A (engine, query, locale, device) SERP fetched today
  is served to every organization from ``serp_snapshots``; the cache stores nothing
  about who asked (plan §5.2). Cache hits cost nothing and aren't counted.
* **Budgets (cost circuit breakers, plan §5.6).** A global daily request cap across all
  orgs, and a per-org daily cap from the plan. Exceeding either returns an honest
  "unavailable" - never a guessed position.
* **Failover.** Vendors are tried in order per engine; retryable errors and parse
  failures move on to the next. After ``OPEN_AFTER`` consecutive failures a vendor is
  skipped for ``COOLDOWN_S`` (per process).
* **Cross-validation.** A configurable sample is fetched from a second vendor too, and
  top-10 domain agreement (Jaccard) is stored, catching bad or tampered data early.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.models import uuid7
from serptank.modules.search_data.adapters.base import CollectorError, SerpAdapter
from serptank.modules.search_data.models import SerpSnapshot, SerpUsage, SerpValidation, VendorUsage
from serptank.modules.search_data.schema import SerpRequest, SerpSnapshotData, normalize_query

logger = structlog.get_logger(__name__)

OPEN_AFTER = 5
COOLDOWN_S = 300.0
AGREEMENT_THRESHOLD = 0.5


class SerpUnavailableError(Exception):
    """No SERP could be obtained now (budget, no vendor, all failed). User-safe."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class CachedSerp:
    snapshot_id: uuid.UUID
    data: SerpSnapshotData
    fetched_on: date
    from_cache: bool
    vendor: str


@dataclass
class _Breaker:
    failures: int = 0
    open_until: float = 0.0


def parse_order(spec: str) -> dict[str, list[str]]:
    """ "google=dataforseo,rawhtml;*=dataforseo" -> {"google": [...], "*": [...]}."""
    order: dict[str, list[str]] = {}
    for part in filter(None, (p.strip() for p in spec.split(";"))):
        engine, _, vendors = part.partition("=")
        order[engine.strip()] = [v.strip() for v in vendors.split(",") if v.strip()]
    return order


def top10_overlap(a: SerpSnapshotData, b: SerpSnapshotData) -> float:
    left = {r.domain for r in a.organic[:10]}
    right = {r.domain for r in b.organic[:10]}
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


@dataclass
class CollectorRouter:
    adapters: dict[str, SerpAdapter]
    order: dict[str, list[str]]
    global_daily_requests: int
    cache_days: int = 1
    validation_rate: float = 0.0
    _breakers: dict[str, _Breaker] = field(default_factory=dict)

    def vendors_for(self, engine: str) -> list[SerpAdapter]:
        names = self.order.get(engine) or self.order.get("*") or []
        return [
            self.adapters[n]
            for n in names
            if n in self.adapters and engine in self.adapters[n].engines
        ]

    def supports(self, engine: str) -> bool:
        return bool(self.vendors_for(engine))

    async def cached(
        self, db: AsyncSession, request: SerpRequest, today: date
    ) -> CachedSerp | None:
        stmt = (
            select(SerpSnapshot)
            .where(
                SerpSnapshot.engine == request.engine,
                SerpSnapshot.query == normalize_query(request.query),
                SerpSnapshot.country == request.country.upper(),
                SerpSnapshot.language == request.language,
                func.coalesce(SerpSnapshot.location, "") == (request.location or ""),
                SerpSnapshot.device == request.device,
                SerpSnapshot.fetched_on > today - timedelta(days=self.cache_days),
            )
            .order_by(SerpSnapshot.fetched_on.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return CachedSerp(
            row.id, SerpSnapshotData.from_json(row.data), row.fetched_on, True, row.vendor
        )

    async def _check_budgets(
        self, db: AsyncSession, organization_id: uuid.UUID, org_daily_cap: int, today: date
    ) -> None:
        global_used = (
            await db.execute(
                select(func.coalesce(func.sum(VendorUsage.requests), 0)).where(
                    VendorUsage.day == today
                )
            )
        ).scalar_one()
        if int(global_used) >= self.global_daily_requests:
            raise SerpUnavailableError(
                "serp_global_budget",
                "Live SERP checks are paused for today (platform budget reached).",
            )
        org_used = (
            await db.execute(
                select(SerpUsage.requests).where(
                    SerpUsage.day == today, SerpUsage.organization_id == organization_id
                )
            )
        ).scalar_one_or_none()
        if (org_used or 0) >= org_daily_cap:
            raise SerpUnavailableError(
                "serp_org_budget",
                "Your plan's daily live SERP checks are used up; they resume tomorrow.",
            )

    async def _account(
        self,
        db: AsyncSession,
        vendor: SerpAdapter,
        engine: str,
        today: date,
        *,
        failed: bool,
        organization_id: uuid.UUID | None,
    ) -> None:
        stmt = pg_insert(VendorUsage).values(
            day=today,
            vendor=vendor.name,
            engine=engine,
            requests=1,
            failures=int(failed),
            cost_micros=vendor.cost_micros,
        )
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=["day", "vendor", "engine"],
                set_={
                    "requests": VendorUsage.requests + 1,
                    "failures": VendorUsage.failures + int(failed),
                    "cost_micros": VendorUsage.cost_micros + vendor.cost_micros,
                },
            )
        )
        if organization_id is not None and not failed:
            usage = pg_insert(SerpUsage).values(
                day=today, organization_id=organization_id, requests=1
            )
            await db.execute(
                usage.on_conflict_do_update(
                    index_elements=["day", "organization_id"],
                    set_={"requests": SerpUsage.requests + 1},
                )
            )

    def _available(self, vendor: SerpAdapter) -> bool:
        breaker = self._breakers.get(vendor.name)
        return breaker is None or breaker.open_until <= time.monotonic()

    def _record(self, vendor: SerpAdapter, ok: bool) -> None:
        breaker = self._breakers.setdefault(vendor.name, _Breaker())
        if ok:
            breaker.failures = 0
            return
        breaker.failures += 1
        if breaker.failures >= OPEN_AFTER:
            breaker.open_until = time.monotonic() + COOLDOWN_S
            logger.warning("serp_vendor_circuit_open", vendor=vendor.name)

    async def get(
        self,
        db: AsyncSession,
        request: SerpRequest,
        *,
        organization_id: uuid.UUID,
        org_daily_cap: int,
        today: date | None = None,
    ) -> CachedSerp:
        """A SERP for ``request``: cached if fresh, else fetched (and charged). Commits."""
        today = today or datetime.now(UTC).date()
        hit = await self.cached(db, request, today)
        if hit is not None:
            return hit
        vendors = self.vendors_for(request.engine)
        if not vendors:
            raise SerpUnavailableError(
                "serp_engine_unsupported", "No data source is configured for this search engine."
            )
        await self._check_budgets(db, organization_id, org_daily_cap, today)
        errors: list[str] = []
        for index, vendor in enumerate(vendors):
            if not self._available(vendor):
                errors.append(f"{vendor.name}: circuit open")
                continue
            try:
                data = await vendor.fetch(request)
            except CollectorError as exc:
                self._record(vendor, ok=False)
                await self._account(
                    db, vendor, request.engine, today, failed=True, organization_id=None
                )
                await db.commit()
                errors.append(exc.message)
                logger.info(
                    "serp_fetch_failed",
                    vendor=vendor.name,
                    engine=request.engine,
                    error=exc.message,
                )
                continue  # fail over (non-retryable ones too: the next vendor may work)
            self._record(vendor, ok=True)
            await self._account(
                db, vendor, request.engine, today, failed=False, organization_id=organization_id
            )
            snapshot = await self._store(db, request, data, vendor.name, today)
            await self._maybe_validate(db, request, data, vendor, vendors[index + 1 :], today)
            await db.commit()
            return snapshot
        logger.warning("serp_all_vendors_failed", engine=request.engine, errors=errors[:5])
        raise SerpUnavailableError(
            "serp_unavailable", "Live SERP data is temporarily unavailable; we'll retry."
        )

    async def _store(
        self,
        db: AsyncSession,
        request: SerpRequest,
        data: SerpSnapshotData,
        vendor: str,
        today: date,
    ) -> CachedSerp:
        data.query = normalize_query(request.query)
        values = {
            "id": uuid7(),
            "engine": request.engine,
            "query": data.query,
            "country": request.country.upper(),
            "language": request.language,
            "location": request.location,
            "device": request.device,
            "fetched_on": today,
            "vendor": vendor,
            "data": data.to_json(),
        }
        inserted = (
            await db.execute(
                pg_insert(SerpSnapshot)
                .values(**values)
                .on_conflict_do_nothing()
                .returning(SerpSnapshot.id)
            )
        ).scalar_one_or_none()
        if inserted is None:  # a concurrent fetch stored it first: use that one
            existing = await self.cached(db, request, today)
            if existing is None:
                raise SerpUnavailableError(
                    "serp_unavailable", "Live SERP data is temporarily unavailable; we'll retry."
                )
            return CachedSerp(existing.snapshot_id, existing.data, today, False, existing.vendor)
        return CachedSerp(inserted, data, today, False, vendor)

    async def _maybe_validate(
        self,
        db: AsyncSession,
        request: SerpRequest,
        data: SerpSnapshotData,
        primary: SerpAdapter,
        others: list[SerpAdapter],
        today: date,
    ) -> None:
        # Random sampling for data-quality checks, not security.
        if not others or self.validation_rate <= 0 or random.random() >= self.validation_rate:  # noqa: S311  # nosec B311
            return
        secondary = others[0]
        try:
            second = await secondary.fetch(request)
        except CollectorError:
            return
        await self._account(
            db, secondary, request.engine, today, failed=False, organization_id=None
        )
        overlap = top10_overlap(data, second)
        db.add(
            SerpValidation(
                engine=request.engine,
                query=normalize_query(request.query),
                primary_vendor=primary.name,
                secondary_vendor=secondary.name,
                top10_overlap=round(overlap, 3),
                agreed=overlap >= AGREEMENT_THRESHOLD,
            )
        )
        if overlap < AGREEMENT_THRESHOLD:
            logger.warning(
                "serp_vendors_disagree", engine=request.engine, overlap=round(overlap, 2)
            )
