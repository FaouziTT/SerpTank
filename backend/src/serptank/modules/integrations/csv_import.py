"""Strict, bounded import of AI-search CSV exports.

Sources (no public API yet - plan §3):

* ``gsc_genai`` - Search Console's Generative AI performance report (AI Overviews and
  AI Mode impressions by page/query/country/device/date).
* ``bing_ai`` - Bing Webmaster Tools' AI Performance report (Copilot citations and
  grounding queries).

Exports vary by language and report version, so columns are matched through alias
sets, but the schema is strict: a date column and at least one metric are required,
unknown columns are ignored, every value is validated, and the import is rejected if
more than 5 % of rows are invalid. Nothing is guessed: a missing metric is stored as 0
only when its column is absent from the file entirely (and reported back).
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime

MAX_ROWS = 500_000
MAX_CELL = 2048
MAX_BAD_SHARE = 0.05
NBSP = "\u00a0"

ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "day", "datum", "fecha"),
    "page": (
        "page",
        "pages",
        "top pages",
        "url",
        "landing page",
        "cited url",
        "cited page",
        "cited pages",
    ),
    "query": ("query", "queries", "top queries", "grounding query", "grounding queries", "prompt"),
    "country": ("country", "countries"),
    "device": ("device", "devices"),
    "surface": ("surface", "search appearance", "ai feature", "feature", "experience"),
    "impressions": (
        "impressions",
        "ai impressions",
        "ai overview impressions",
        "ai mode impressions",
    ),
    "clicks": ("clicks", "ai clicks"),
    "citations": ("citations", "cited", "times cited", "citation count", "citation share"),
}
METRICS = ("impressions", "clicks", "citations")
SOURCES = {"gsc_genai": ("ai_overview", "ai_mode"), "bing_ai": ("copilot",)}
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y", "%b %d, %Y", "%d %b %Y", "%Y/%m/%d")


class CsvImportError(Exception):
    """The file can't be imported. The message is user-safe and actionable."""


@dataclass
class ImportRow:
    date: date
    surface: str
    page: str = ""
    query: str = ""
    country: str = ""
    device: str = ""
    impressions: int = 0
    clicks: int = 0
    citations: int = 0


@dataclass
class ImportResult:
    rows: list[ImportRow] = field(default_factory=list)
    bad_rows: int = 0
    errors: list[str] = field(default_factory=list)
    columns: dict[str, str] = field(default_factory=dict)  # our field -> file header
    missing_metrics: list[str] = field(default_factory=list)

    @property
    def date_range(self) -> tuple[date, date] | None:
        if not self.rows:
            return None
        days = [r.date for r in self.rows]
        return min(days), max(days)


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("﻿").strip('"').lower())


def _parse_date(value: str) -> date:
    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()  # noqa: DTZ007 - calendar dates
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {text[:30]!r}")


def _parse_int(value: str) -> int:
    text = value.strip().replace(",", "").replace(NBSP, "").replace(" ", "")
    if not text or text in {"-", "—"}:
        return 0
    number = float(text.rstrip("%"))
    if number < 0 or number > 10**12:
        raise ValueError("number out of range")
    return round(number)


def _surface(value: str, source: str, default: str) -> str:
    text = value.lower()
    if "mode" in text:
        return "ai_mode"
    if "overview" in text:
        return "ai_overview"
    if "copilot" in text or source == "bing_ai":
        return "copilot"
    return default


def _row(
    cells: list[str], width: int, index: dict[str, int], source: str, default: str
) -> ImportRow:
    if len(cells) < width:
        raise ValueError("missing columns")

    def cell(name: str) -> str:
        return cells[index[name]][:MAX_CELL] if name in index else ""

    def metric(name: str) -> int:
        return _parse_int(cell(name)) if name in index else 0

    return ImportRow(
        date=_parse_date(cell("date")),
        surface=_surface(cell("surface"), source, default),
        page=cell("page").strip(),
        query=cell("query").strip(),
        country=cell("country").strip()[:64],
        device=cell("device").strip().lower()[:20],
        impressions=metric("impressions"),
        clicks=metric("clicks"),
        citations=metric("citations"),
    )


def _map_columns(header: list[str], normalized: list[str], result: ImportResult) -> dict[str, int]:
    """Our field -> column position, via the alias table (first match wins)."""
    index: dict[str, int] = {}
    for field_name, aliases in ALIASES.items():
        position = next((i for i, name in enumerate(normalized) if name in aliases), None)
        if position is not None:
            index[field_name] = position
            result.columns[field_name] = header[position].strip()
    return index


def _reader(text: str) -> Iterator[list[str]]:
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
            text[:4096], delimiters=",;\t"
        )
    except csv.Error:
        dialect = csv.excel
    return csv.reader(io.StringIO(text), dialect)


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError as exc:
            raise CsvImportError("The file isn't UTF-8 or UTF-16 text. Export it as CSV.") from exc


def parse_ai_csv(data: bytes, *, source: str, default_surface: str | None = None) -> ImportResult:
    if source not in SOURCES:
        raise CsvImportError("Unknown import type.")
    default = default_surface or SOURCES[source][0]
    if default not in SOURCES[source]:
        raise CsvImportError(f"Surface must be one of: {', '.join(SOURCES[source])}.")
    reader = _reader(_decode(data))
    header = next(reader, None)
    if not header:
        raise CsvImportError("The file is empty.")
    headers = [_normalize_header(h) for h in header]
    result = ImportResult()
    index = _map_columns(header, headers, result)
    if "date" not in index:
        raise CsvImportError(
            "No date column found. Export the report with a Date dimension (expected a "
            "column named 'Date')."
        )
    present = [m for m in METRICS if m in index]
    if not present:
        raise CsvImportError("No metric column found (expected Impressions, Clicks or Citations).")
    result.missing_metrics = [m for m in METRICS if m not in index]

    total = 0
    for line_number, cells in enumerate(reader, start=2):
        if not any(c.strip() for c in cells):
            continue
        total += 1
        if total > MAX_ROWS:
            raise CsvImportError(f"The file has more than {MAX_ROWS:,} rows. Split it by date.")
        try:
            result.rows.append(_row(cells, len(headers), index, source, default))
        except (ValueError, IndexError) as exc:
            result.bad_rows += 1
            if len(result.errors) < 10:  # noqa: PLR2004
                result.errors.append(f"Line {line_number}: {exc}")
    if total == 0:
        raise CsvImportError("The file has a header but no data rows.")
    if result.bad_rows / total > MAX_BAD_SHARE:
        raise CsvImportError(
            f"{result.bad_rows} of {total} rows are invalid, so nothing was imported. "
            f"First problems: {'; '.join(result.errors[:3])}"
        )
    return result
