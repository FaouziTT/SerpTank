"""Pure report helpers: CSV neutralisation, signed links, presence buckets."""

from __future__ import annotations

import time
import uuid

from serptank.modules.reports.csvsafe import neutralise, to_csv
from serptank.modules.reports.exports import sign, signed_path, verify
from serptank.modules.reports.presence import bucket, engine_weight

SECRET = "s" * 40


def test_csv_formula_neutralisation() -> None:
    assert neutralise('=HYPERLINK("http://evil")') == '\'=HYPERLINK("http://evil")'
    for danger in ("+1+1", "-2+3", "@SUM(A1)", "\tx", "\rx"):
        assert neutralise(danger).startswith("'")
    assert neutralise(-3) == -3  # numbers stay numbers
    assert neutralise(None) == ""
    assert neutralise(True) == "true"
    content, count = to_csv(["a", "b"], [["=1", 2], ["ok", None]])
    assert count == 2
    text = content.decode("utf-8")
    assert text.startswith("﻿a,b\r\n")
    assert "'=1,2" in text


def test_signed_links() -> None:
    org, export = uuid.uuid4(), uuid.uuid4()
    future = int(time.time()) + 60
    sig = sign(SECRET, org, export, future)
    assert verify(SECRET, org, export, future, sig)
    assert not verify(SECRET, org, export, future + 1, sig)  # extended expiry
    assert not verify(SECRET, uuid.uuid4(), export, future, sig)  # other tenant
    assert not verify(SECRET, org, uuid.uuid4(), future, sig)  # other export
    assert not verify("x" * 40, org, export, future, sig)  # other key
    past = int(time.time()) - 1
    assert not verify(SECRET, org, export, past, sign(SECRET, org, export, past))
    path, expires = signed_path(SECRET, org, export)
    assert path.startswith(f"/api/v1/exports/{org}/{export}?exp=")
    assert expires.timestamp() > time.time()


def test_presence_helpers() -> None:
    assert [bucket(p) for p in (1, 3.4, 7, 15, 60, None, 150)] == [
        "top3", "top10", "top10", "top20", "top100", "not_ranking", "not_ranking",
    ]  # fmt: skip
    assert engine_weight("US", "google") > engine_weight("US", "bing")
    assert engine_weight("RU", "yandex") > engine_weight("RU", "google")
    assert engine_weight("DE", "google") == 0.90
