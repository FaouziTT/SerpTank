"""Collector router: cache sharing, failover, circuit breaker, budgets, validation."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date

import pytest
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.config import Settings
from serptank.core.db import bind_identity
from serptank.core.http import SafeHttpClient
from serptank.core.models import uuid7
from serptank.modules.search_data.adapters.base import CollectorError
from serptank.modules.search_data.collector import (
    CollectorRouter,
    SerpUnavailableError,
    parse_order,
    top10_overlap,
)
from serptank.modules.search_data.factory import build_router
from serptank.modules.search_data.models import SerpValidation
from serptank.modules.search_data.schema import SerpRequest
from serptank.modules.tenancy.models import Organization
from tests.search_data.fakes import FakeVendor

DAY = date(2026, 9, 24)


@pytest.fixture
async def org_session(
    owner_engine: AsyncEngine, app_engine: AsyncEngine
) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(owner_engine, expire_on_commit=False) as owner:
        org = Organization(id=uuid7(), name="SERP", slug=f"serp-{uuid.uuid4().hex[:8]}")
        owner.add(org)
        await owner.commit()
    async with async_sessionmaker(app_engine, expire_on_commit=False)() as session:
        await bind_identity(session, organization_id=org.id)
        yield session


def router(*vendors: FakeVendor, cap: int = 1000, validation: float = 0.0) -> CollectorRouter:
    return CollectorRouter(
        adapters={v.name: v for v in vendors},
        order={"*": [v.name for v in vendors]},
        global_daily_requests=cap,
        validation_rate=validation,
    )


def req(query: str) -> SerpRequest:
    return SerpRequest(engine="google", query=query, country="US", language="en")


def _org(session: AsyncSession) -> uuid.UUID:
    value = session.info["serptank.org_id"]
    assert isinstance(value, uuid.UUID)
    return value


async def test_cache_is_shared_and_counted_once(org_session: AsyncSession) -> None:
    vendor = FakeVendor()
    r = router(vendor)
    q = f"shoes {uuid.uuid4().hex[:6]}"
    first = await r.get(
        org_session, req(q), organization_id=_org(org_session), org_daily_cap=10, today=DAY
    )
    second = await r.get(
        org_session,
        req(q.upper() + "  "),
        organization_id=uuid.uuid4(),
        org_daily_cap=10,
        today=DAY,
    )
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.snapshot_id == first.snapshot_id
    assert len(vendor.calls) == 1
    used = (
        await org_session.execute(
            text("SELECT requests FROM serp_usage WHERE day = :d"), {"d": DAY}
        )
    ).scalar_one()
    assert used == 1
    # A new day means a fresh fetch.
    await r.get(
        org_session,
        req(q),
        organization_id=_org(org_session),
        org_daily_cap=10,
        today=date(2026, 9, 25),
    )
    assert len(vendor.calls) == 2


async def test_failover_and_circuit_breaker(org_session: AsyncSession) -> None:
    broken = FakeVendor(name="broken", fail_with=CollectorError("broken", "HTTP 503"))
    backup = FakeVendor(name="backup")
    r = router(broken, backup)
    for i in range(6):
        result = await r.get(
            org_session,
            req(f"failover {uuid.uuid4().hex[:6]} {i}"),
            organization_id=_org(org_session),
            org_daily_cap=100,
            today=DAY,
        )
        assert result.vendor == "backup"
    assert len(broken.calls) == 5  # circuit opened after 5 consecutive failures
    assert len(backup.calls) == 6
    only_broken = router(FakeVendor(name="broken2", fail_with=CollectorError("broken2", "down")))
    with pytest.raises(SerpUnavailableError) as exc:
        await only_broken.get(
            org_session,
            req(f"x {uuid.uuid4().hex}"),
            organization_id=_org(org_session),
            org_daily_cap=100,
            today=DAY,
        )
    assert exc.value.code == "serp_unavailable"


async def test_budgets_stop_fetching_honestly(org_session: AsyncSession) -> None:
    vendor = FakeVendor(name="budget")
    r = router(vendor)
    org = _org(org_session)
    day = date(2026, 1, 1)
    await r.get(
        org_session, req(f"b1 {uuid.uuid4().hex}"), organization_id=org, org_daily_cap=1, today=day
    )
    with pytest.raises(SerpUnavailableError) as exc:
        await r.get(
            org_session,
            req(f"b2 {uuid.uuid4().hex}"),
            organization_id=org,
            org_daily_cap=1,
            today=day,
        )
    assert exc.value.code == "serp_org_budget"
    global_cap = router(FakeVendor(name="g"), cap=0)
    with pytest.raises(SerpUnavailableError) as exc:
        await global_cap.get(
            org_session,
            req(f"b3 {uuid.uuid4().hex}"),
            organization_id=org,
            org_daily_cap=100,
            today=day,
        )
    assert exc.value.code == "serp_global_budget"
    with pytest.raises(SerpUnavailableError) as exc:
        await router(FakeVendor(engines=frozenset({"bing"}))).get(
            org_session, req("x"), organization_id=org, org_daily_cap=10, today=day
        )
    assert exc.value.code == "serp_engine_unsupported"


async def test_cross_validation_records_disagreement(org_session: AsyncSession) -> None:
    primary = FakeVendor(name="p")
    secondary = FakeVendor(name="s", ranking=["other1.com", "other2.com", "www.example-shop.com"])
    r = router(primary, secondary, validation=1.0)
    q = f"validate {uuid.uuid4().hex[:8]}"
    await r.get(org_session, req(q), organization_id=_org(org_session), org_daily_cap=10, today=DAY)
    row = (
        await org_session.execute(select(SerpValidation).where(SerpValidation.query == q))
    ).scalar_one()
    assert row.agreed is False
    assert row.top10_overlap == pytest.approx(1 / 6, abs=0.01)


def test_order_parsing_and_factory() -> None:
    assert parse_order("google=a,b; *=c") == {"google": ["a", "b"], "*": ["c"]}
    r = build_router(Settings(), SafeHttpClient())
    assert r.adapters == {}  # no credentials: no vendors, honestly unsupported
    assert not r.supports("google")
    r = build_router(
        Settings(
            dataforseo_login="l",
            dataforseo_password=SecretStr("p"),
            rawhtml_endpoint="https://x/?u={url}",
            rawhtml_api_key=SecretStr("k"),
        ),
        SafeHttpClient(),
    )
    assert set(r.adapters) == {"dataforseo", "rawhtml"}
    assert r.supports("duckduckgo")  # raw HTML + our parser
    assert r.supports("yandex")  # DataForSEO


def test_overlap() -> None:
    a = FakeVendor(ranking=["a", "b"])
    import asyncio

    one = asyncio.run(a.fetch(req("q")))
    assert top10_overlap(one, one) == 1.0
