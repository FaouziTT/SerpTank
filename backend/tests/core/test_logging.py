from __future__ import annotations

import json
import logging

import pytest
import structlog

from serptank.core.logging import REDACTED, configure_logging, redact


def test_redacts_sensitive_keys_recursively() -> None:
    data = {
        "password": "hunter2",
        "nested": {"api_key": "abc", "ok": 1, "Session_ID": "s"},
        "items": [{"refresh_token": "r"}],
        "authorization": "Bearer x",
    }
    out = redact(data)
    assert out["password"] == REDACTED
    assert out["nested"] == {"api_key": REDACTED, "ok": 1, "Session_ID": REDACTED}
    assert out["items"] == [{"refresh_token": REDACTED}]
    assert out["authorization"] == REDACTED


def test_emails_are_hashed() -> None:
    out = redact("login failed for Alice@Example.com")
    assert "alice" not in out.lower()
    assert "email#" in out
    assert redact("x Alice@example.com") == redact("x alice@EXAMPLE.com")


def test_log_output_is_json_and_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json=True)
    structlog.get_logger("t").info("user_login", email="bob@example.com", password="pw")
    logging.getLogger().handlers[0].flush()
    line = capsys.readouterr().out.strip().splitlines()[-1]
    record = json.loads(line)
    assert record["event"] == "user_login"
    assert record["password"] == REDACTED
    assert "bob@example.com" not in line
