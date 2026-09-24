"""CSV writing that is safe to open in spreadsheet apps (OWASP CSV injection).

Cells starting with ``=``, ``+``, ``-``, ``@``, tab or carriage return are prefixed with
an apostrophe so Excel/Sheets/LibreOffice treat them as text, never as formulas. Plain
negative numbers stay numeric (we only neutralise strings, not ints/floats).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from typing import Any

DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def neutralise(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return value
    text = str(value)
    return f"'{text}" if text.startswith(DANGEROUS) else text


def to_csv(header: Sequence[str], rows: Iterable[Sequence[Any]]) -> tuple[bytes, int]:
    """UTF-8 (with BOM, so Excel detects the encoding) CSV bytes and the row count."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    count = 0
    for row in rows:
        writer.writerow([neutralise(v) for v in row])
        count += 1
    return ("﻿" + buffer.getvalue()).encode("utf-8"), count
