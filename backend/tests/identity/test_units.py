"""Unit tests: password policy/hashing, HIBP k-anonymity, sessions, TOTP windows."""

from __future__ import annotations

import hashlib
import time

import httpx
import pyotp
import pytest
from pwdlib.hashers.bcrypt import BcryptHasher
from redis.asyncio import Redis

from serptank.core.config import Settings
from serptank.core.http import SafeHttpClient
from serptank.modules.identity.mfa import matching_step
from serptank.modules.identity.passwords import (
    HibpBreachChecker,
    NoBreachChecker,
    PasswordHasher,
    WeakPasswordError,
    validate_password,
)
from serptank.modules.identity.sessions import SessionStore
from tests.conftest import _service_url


async def _resolver(_h: str, _p: int) -> list[str]:
    return ["93.184.215.34"]


def _hibp(handler) -> HibpBreachChecker:  # type: ignore[no-untyped-def]
    return HibpBreachChecker(
        SafeHttpClient(resolver=_resolver, transport=httpx.MockTransport(handler))
    )


async def test_hibp_sends_only_prefix_and_detects_breach() -> None:
    password = "correct horse battery staple"
    digest = hashlib.sha1(password.encode()).hexdigest().upper()  # noqa: S324
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text=f"0000000000000000000000000000000000A:0\n{digest[5:]}:42\n")

    assert await _hibp(handler).is_breached(password)
    assert seen[0].endswith("/range/" + digest[:5])
    assert password not in seen[0]
    assert digest[5:] not in seen[0]


async def test_hibp_padding_entries_and_misses() -> None:
    def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ABCDEF:0\n")

    assert not await _hibp(handler).is_breached("some other password")


async def test_hibp_fails_open_when_unavailable() -> None:
    assert not await _hibp(lambda _r: httpx.Response(503)).is_breached("x" * 20)


async def test_password_policy() -> None:
    checker = NoBreachChecker()
    await validate_password("a sufficiently long one", min_length=12, breach_checker=checker)
    cases = ["short", "x" * 129, "aaaaaaaaaaaaaaaa", "password1234"]
    for bad in cases:
        with pytest.raises(WeakPasswordError):
            await validate_password(bad, min_length=12, breach_checker=checker)
    with pytest.raises(WeakPasswordError, match="name or email"):
        await validate_password(
            "janedoe12345", min_length=12, breach_checker=checker, context=("JaneDoe12345",)
        )


def test_argon2_and_bcrypt_upgrade() -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("my long passphrase")
    assert hashed.startswith("$argon2id$")
    assert hasher.verify("my long passphrase", hashed) == (True, None)
    assert hasher.verify("wrong", hashed)[0] is False
    legacy = BcryptHasher().hash("legacy password here")
    valid, upgraded = hasher.verify("legacy password here", legacy)
    assert valid
    assert upgraded
    assert upgraded.startswith("$argon2id$")
    assert hasher.verify("x", "not-a-hash") == (False, None)


def test_totp_window() -> None:
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    now = time.time()
    assert matching_step(secret, totp.at(int(now)), now) == int(now // 30)
    assert matching_step(secret, totp.at(int(now) - 30), now) is not None
    assert matching_step(secret, totp.at(int(now) - 90), now) is None
    assert matching_step(secret, "12ab56", now) is None


@pytest.fixture
async def store() -> SessionStore:
    url = _service_url("SERPTANK_TEST_REDIS_URL")
    if not url:
        pytest.skip("Redis not configured")
    redis = Redis.from_url(url, decode_responses=True)
    settings = Settings(session_idle_timeout_s=60, session_absolute_timeout_s=120)
    return SessionStore(redis, settings)


async def test_session_storage_never_contains_token(store: SessionStore) -> None:
    import uuid

    token, data = await store.create(uuid.uuid4())
    assert token not in data.key
    assert await store._redis.get(f"sess:{token}") is None
    assert (await store.get(token)) is not None


async def test_absolute_expiry_enforced(store: SessionStore) -> None:
    import uuid

    token, data = await store.create(uuid.uuid4())
    data.absolute_expires_at = time.time() - 1
    await store.update(data)
    assert await store.get(token) is None


async def test_rotation_invalidates_old_token(store: SessionStore) -> None:
    import uuid

    token, data = await store.create(uuid.uuid4())
    new_token, new_data = await store.rotate(data, mfa_pending=False)
    assert await store.get(token) is None
    assert (await store.get(new_token)) is not None
    assert new_data.key != data.key


async def test_garbage_tokens(store: SessionStore) -> None:
    assert await store.get("") is None
    assert await store.get("x" * 500) is None
    assert await store.get("does-not-exist") is None
