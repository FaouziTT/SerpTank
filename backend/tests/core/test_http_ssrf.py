"""SSRF protection tests for SafeHttpClient (docs/execution-plan.md §5.5)."""

from __future__ import annotations

import ipaddress

import httpx
import pytest

from serptank.core.http import (
    DisallowedContentTypeError,
    EgressPolicy,
    EgressPolicyError,
    ResponseTooLargeError,
    SafeHttpClient,
    TooManyRedirectsError,
    is_public_address,
    normalize_public_url,
)

PUBLIC_IP = "93.184.215.34"

BLOCKED_ADDRESSES = [
    "127.0.0.1",
    "127.1.2.3",
    "10.0.0.1",
    "172.16.5.4",
    "192.168.1.1",
    "169.254.169.254",  # cloud metadata
    "100.64.0.1",  # CGNAT
    "0.0.0.0",
    "224.0.0.1",
    "240.0.0.1",
    "255.255.255.255",
    "198.18.0.1",
    "::1",
    "::",
    "fe80::1",
    "fc00::1",
    "fd12:3456::1",
    "::ffff:127.0.0.1",  # IPv4-mapped loopback
    "::ffff:169.254.169.254",
    "64:ff9b::a9fe:a9fe",  # NAT64 -> 169.254.169.254
    "2002:7f00:0001::1",  # 6to4 -> 127.0.0.1
    "ff02::1",
]
PUBLIC_ADDRESSES = ["93.184.215.34", "8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"]


@pytest.mark.parametrize("address", BLOCKED_ADDRESSES)
def test_blocks_non_public_addresses(address: str) -> None:
    assert not is_public_address(ipaddress.ip_address(address))


@pytest.mark.parametrize("address", PUBLIC_ADDRESSES)
def test_allows_public_addresses(address: str) -> None:
    assert is_public_address(ipaddress.ip_address(address))


def _resolver(mapping: dict[str, list[str]]):  # type: ignore[no-untyped-def]
    async def resolve(host: str, _port: int) -> list[str]:
        return mapping.get(host, [PUBLIC_IP])

    return resolve


def _client(handler, mapping=None, policy=None) -> SafeHttpClient:  # type: ignore[no-untyped-def]
    return SafeHttpClient(
        policy,
        resolver=_resolver(mapping or {}),
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "http://user:pass@example.com/",
        "http://example.com:6379/",
        "http://example.com:22/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://2130706433/",  # decimal-encoded 127.0.0.1
        "http://0x7f000001/",  # hex-encoded 127.0.0.1
        "http://0177.0.0.1/",  # octal-encoded 127.0.0.1
        "http://127.1/",  # shorthand 127.0.0.1
        "http://0xa9fea9fe/",  # hex 169.254.169.254
        "not a url",
        "http:///nohost",
    ],
)
async def test_rejects_disallowed_urls(url: str) -> None:
    async with _client(lambda _r: httpx.Response(200)) as client:
        with pytest.raises(EgressPolicyError):
            await client.get(url)


async def test_rejects_hostname_resolving_to_private_address() -> None:
    async with _client(lambda _r: httpx.Response(200), {"evil.test": ["10.0.0.5"]}) as client:
        with pytest.raises(EgressPolicyError):
            await client.get("http://evil.test/")


async def test_rejects_mixed_public_and_private_records() -> None:
    mapping = {"rebind.test": [PUBLIC_IP, "127.0.0.1"]}
    async with _client(lambda _r: httpx.Response(200), mapping) as client:
        with pytest.raises(EgressPolicyError):
            await client.get("http://rebind.test/")


async def test_pins_connection_to_validated_ip_and_keeps_host() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/plain"})

    async with _client(handler) as client:
        response = await client.get("https://example.com/path?q=1")
    assert response.status_code == 200
    assert response.text() == "ok"
    request = seen[0]
    assert request.url.host == PUBLIC_IP  # connection goes to the pinned IP
    assert request.headers["host"] == "example.com"
    assert request.extensions["sni_hostname"] == "example.com"  # TLS verifies real host
    assert request.url.path == "/path"
    assert "SerpTankBot" in request.headers["user-agent"]


async def test_redirect_to_internal_address_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://internal.test/admin"})

    mapping = {"internal.test": ["192.168.0.10"]}
    async with _client(handler, mapping) as client:
        with pytest.raises(EgressPolicyError):
            await client.get("http://example.com/")


async def test_redirect_to_metadata_ip_literal_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(301, headers={"location": "http://169.254.169.254/"})

    async with _client(handler) as client:
        with pytest.raises(EgressPolicyError):
            await client.get("http://example.com/")


async def test_follows_safe_redirects_and_records_chain() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["host"] == "a.test":
            return httpx.Response(301, headers={"location": "https://b.test/final"})
        return httpx.Response(200, text="done")

    async with _client(handler) as client:
        response = await client.get("http://a.test/start")
    assert response.url == "https://b.test/final"
    assert response.redirect_chain == ["http://a.test/start"]


async def test_cross_origin_redirect_strips_credentials() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.headers["host"] == "a.test":
            return httpx.Response(302, headers={"location": "https://b.test/"})
        return httpx.Response(200)

    async with _client(handler) as client:
        await client.get("https://a.test/", headers={"Authorization": "Bearer secret"})
    assert seen[0].headers.get("authorization") == "Bearer secret"
    assert "authorization" not in seen[1].headers


async def test_too_many_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "/again"})

    async with _client(handler, policy=EgressPolicy(max_redirects=3)) as client:
        with pytest.raises(TooManyRedirectsError):
            await client.get("http://loop.test/")


async def test_response_size_cap_declared() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 2000)

    async with _client(handler, policy=EgressPolicy(max_response_bytes=1000)) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get("http://big.test/")


async def test_content_type_allow_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})

    policy = EgressPolicy(allowed_content_types=frozenset({"text/html"}))
    async with _client(handler, policy=policy) as client:
        with pytest.raises(DisallowedContentTypeError):
            await client.get("http://json.test/")


def test_normalize_public_url() -> None:
    assert normalize_public_url(" https://Example.com/a ") == "https://example.com/a"
    for bad in ("javascript:alert(1)", "https://u:p@x.com", "ftp://x.com"):
        with pytest.raises(EgressPolicyError):
            normalize_public_url(bad)
