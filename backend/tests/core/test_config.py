from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from serptank.core.config import Environment, Settings
from serptank.core.crypto import Keyring

STRONG = "x" * 40


def _prod(**overrides: object) -> Settings:
    key = Keyring.generate_key()
    values: dict[str, object] = {
        "environment": Environment.PRODUCTION,
        "public_origin": "https://app.serptank.com",
        "allowed_hosts": ["app.serptank.com"],
        "session_secret": SecretStr("s" * 40),
        "csrf_secret": SecretStr("c" * 40),
        "api_key_pepper": SecretStr("p" * 40),
        "encryption_keys": SecretStr(f"k1:{key}"),
        "encryption_active_key_id": "k1",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_valid_production_config() -> None:
    settings = _prod()
    assert settings.is_production_like
    assert not settings.show_docs
    assert settings.cookie_secure
    assert "k1" in settings.parsed_encryption_keys()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"session_secret": SecretStr("dev-insecure-change-me")}, "session_secret"),
        ({"csrf_secret": SecretStr("short")}, "csrf_secret"),
        ({"api_key_pepper": SecretStr("s" * 40)}, "must all differ"),
        ({"encryption_keys": SecretStr(""), "encryption_active_key_id": ""}, "encryption_keys"),
        ({"public_origin": "http://app.serptank.com"}, "https"),
        ({"allowed_hosts": ["*"]}, "allowed_hosts"),
    ],
)
def test_production_fails_closed(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _prod(**overrides)


def test_invalid_keyring_rejected() -> None:
    with pytest.raises(ValidationError, match="32 bytes"):
        Settings(encryption_keys=SecretStr("k1:c2hvcnQ"), encryption_active_key_id="k1")
    with pytest.raises(ValidationError, match="ACTIVE_KEY_ID"):
        Settings(
            encryption_keys=SecretStr(f"k1:{Keyring.generate_key()}"),
            encryption_active_key_id="k9",
        )


def test_development_allows_placeholders_and_docs() -> None:
    settings = Settings(environment=Environment.DEVELOPMENT)
    assert settings.show_docs
    assert not settings.cookie_secure


def test_csv_env_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERPTANK_ALLOWED_HOSTS", "a.com, b.com")
    assert Settings().allowed_hosts == ["a.com", "b.com"]


def test_secrets_not_in_repr() -> None:
    settings = _prod()
    assert STRONG not in repr(settings)
    assert "s" * 40 not in repr(settings)
