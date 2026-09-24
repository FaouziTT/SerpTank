"""CSV import parsing (unit) and the import endpoint."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.email import MemoryEmailSender
from serptank.modules.integrations.csv_import import MAX_ROWS, CsvImportError, parse_ai_csv
from serptank.modules.tenancy.models import Organization
from tests.support.api import signed_in_browser

GSC = """Date,Top pages,Country,Device,Search appearance,Impressions,Clicks
2026-09-01,https://shop.com/a,United States,Mobile,AI Overview,"1,200",14
2026-09-01,https://shop.com/b,Germany,Desktop,AI Mode,300,2
2026-09-02,https://shop.com/a,United States,Mobile,,50,0
"""


def test_parses_gsc_genai_export() -> None:
    result = parse_ai_csv(GSC.encode(), source="gsc_genai")
    assert len(result.rows) == 3
    first = result.rows[0]
    assert (
        first.date,
        first.page,
        first.country,
        first.device,
        first.surface,
        first.impressions,
        first.clicks,
    ) == (
        date(2026, 9, 1),
        "https://shop.com/a",
        "United States",
        "mobile",
        "ai_overview",
        1200,
        14,
    )
    assert result.rows[1].surface == "ai_mode"
    assert result.rows[2].surface == "ai_overview"  # default when the cell is empty
    assert result.missing_metrics == ["citations"]
    assert result.date_range == (date(2026, 9, 1), date(2026, 9, 2))
    assert result.columns["page"] == "Top pages"


def test_parses_bing_ai_export_with_semicolons_and_utf16() -> None:
    csv = (
        "Date;Cited URL;Grounding queries;Citations\n09/03/2026;https://shop.com/c;best widgets;7\n"
    )
    result = parse_ai_csv(csv.encode("utf-16"), source="bing_ai")
    row = result.rows[0]
    assert (row.date, row.page, row.query, row.citations, row.surface) == (
        date(2026, 9, 3),
        "https://shop.com/c",
        "best widgets",
        7,
        "copilot",
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"", "empty"),
        (b"Page,Impressions\nx,1\n", "No date column"),
        (b"Date,Page\n2026-01-01,x\n", "No metric column"),
        (b"Date,Impressions\n", "no data rows"),
        (b"\xff\xfe\x00\xd8", "UTF"),
        (b"Date,Impressions\nnot-a-date,1\n2026-01-01,2\n", "invalid"),
        (b"Date,Impressions\n2026-01-01,-5\n", "invalid"),
    ],
)
def test_rejects_bad_files(payload: bytes, message: str) -> None:
    with pytest.raises(CsvImportError, match=message):
        parse_ai_csv(payload, source="gsc_genai")


def test_rejects_unknown_source_and_surface() -> None:
    with pytest.raises(CsvImportError):
        parse_ai_csv(GSC.encode(), source="other")
    with pytest.raises(CsvImportError, match="Surface"):
        parse_ai_csv(GSC.encode(), source="bing_ai", default_surface="ai_mode")


def test_tolerates_a_few_bad_rows() -> None:
    good = "".join(f"2026-09-{(i % 28) + 1:02d},{i}\n" for i in range(40))
    result = parse_ai_csv(f"Date,Impressions\n{good}garbage,1\n".encode(), source="gsc_genai")
    assert result.bad_rows == 1
    assert result.errors[0].startswith("Line 42")


def test_row_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("serptank.modules.integrations.csv_import.MAX_ROWS", 3)
    with pytest.raises(CsvImportError, match="more than"):
        parse_ai_csv(b"Date,Impressions\n" + b"2026-01-01,1\n" * 5, source="gsc_genai")
    assert MAX_ROWS > 3


async def test_import_endpoint_replaces_range(
    api_app: FastAPI, outbox: MemoryEmailSender, owner_session: AsyncSession
) -> None:
    b, _ = await signed_in_browser(api_app, outbox)
    org = (await b.post("/api/v1/orgs", {"name": "Imp"})).json()["id"]
    await owner_session.execute(
        update(Organization).where(Organization.id == uuid.UUID(org)).values(plan_code="pro")
    )
    await owner_session.commit()
    project = (
        await b.post(f"/api/v1/orgs/{org}/projects", {"name": "S", "domain": "shop-import.com"})
    ).json()["id"]
    url = f"/api/v1/orgs/{org}/projects/{project}/imports/gsc_genai"
    headers = {
        "Origin": "http://localhost:3000",
        "X-CSRF-Token": b.csrf,
        "content-type": "text/csv",
    }
    first = await b.client.post(url, content=GSC.encode(), headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["rows"] == 3
    again = await b.client.post(url, content=GSC.encode(), headers=headers)
    assert again.status_code == 200
    totals = (
        await b.get(f"/api/v1/orgs/{org}/projects/{project}/ai-performance", params={"days": 480})
    ).json()
    by_surface = {t["surface"]: t for t in totals}
    assert by_surface["ai_overview"]["impressions"] == 1250
    assert by_surface["ai_mode"]["clicks"] == 2
    bad = await b.client.post(url, content=b"Page,Impressions\nx,1\n", headers=headers)
    assert bad.status_code == 422
    assert bad.json()["code"] == "import_rejected"
    huge = await b.client.post(url, content=b"x" * (21 * 1024 * 1024), headers=headers)
    assert huge.status_code == 413
    small_elsewhere = await b.client.post(
        f"/api/v1/orgs/{org}/projects", content=b"x" * (2 * 1024 * 1024), headers=headers
    )
    assert small_elsewhere.status_code == 413  # the big limit applies only to imports


def test_crux_assessment_thresholds() -> None:
    from serptank.modules.integrations.providers.crux import assess

    assert assess({"lcp_ms": 2500, "inp_ms": 200, "cls": 0.1}) == "good"
    assert assess({"lcp_ms": 2600, "inp_ms": 100, "cls": 0.0}) == "needs_improvement"
    assert assess({"lcp_ms": 1000, "inp_ms": 600, "cls": 0.0}) == "poor"
    assert assess({"lcp_ms": 1000, "inp_ms": None, "cls": 0.0}) == "unknown"


def test_bing_dates_and_log_redaction() -> None:
    from serptank.core.logging import redact
    from serptank.modules.integrations.providers.bing import parse_ms_date

    assert parse_ms_date("/Date(1758326400000)/") == date(2025, 9, 20)
    assert parse_ms_date("/Date(1758326400000-0700)/") == date(2025, 9, 20)
    assert parse_ms_date("garbage") is None
    assert "SECRET" not in redact("https://ssl.bing.com/x?siteUrl=a&apikey=SECRET&z=1")
