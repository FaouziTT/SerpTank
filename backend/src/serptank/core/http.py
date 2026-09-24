"""SSRF-safe outbound HTTP client (OWASP A01:2025 - SSRF).

**Every** outbound request to a URL that a user can influence (crawls, webhooks, sitemap
fetches, provider callbacks) must go through :class:`SafeHttpClient`. It enforces:

1. **URL policy** - ``http``/``https`` only, no userinfo, allowed ports only (80/443 by
   default), IDNA-normalised host.
2. **Address policy** - the host is resolved and *every* returned address must be
   globally routable. Loopback, RFC1918, link-local (incl. cloud metadata
   ``169.254.169.254``), CGNAT, multicast, reserved, unspecified, ULA, site-local and
   IPv4 addresses embedded in IPv6 (mapped, NAT64, 6to4, Teredo) are rejected.
3. **IP pinning** - the connection is made to the *validated* IP (the original host is
   kept in ``Host`` and TLS SNI/certificate verification), so a DNS-rebinding attacker
   cannot swap the address between the check and the connect.
4. **Redirects** - followed manually (max 5); every hop is re-validated from scratch.
   Credentials are dropped when a redirect changes origin.
5. **Resource caps** - total deadline, per-phase timeouts, maximum response size
   (streamed, never buffered beyond the cap), optional content-type allow-list.
6. ``trust_env=False`` - ambient proxy variables are ignored. An explicit egress proxy
   (e.g. Smokescreen for the renderer) can be configured; in that mode the proxy
   performs connections and must enforce the same policy, while we still pre-validate.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Final

import httpx

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Resolver = Callable[[str, int], Awaitable[list[str]]]

DEFAULT_USER_AGENT: Final = "SerpTankBot/1.0 (+https://serptank.com/bot)"
_REDIRECT_STATUSES: Final = frozenset({301, 302, 303, 307, 308})
_SENSITIVE_HEADERS: Final = frozenset({"authorization", "cookie", "proxy-authorization"})
_NAT64_PREFIX: Final = ipaddress.ip_network("64:ff9b::/96")
_EXTRA_BLOCKED: Final = tuple(
    ipaddress.ip_network(n)
    for n in (
        "0.0.0.0/8",
        "100.64.0.0/10",  # CGNAT
        "192.0.0.0/24",  # IETF protocol assignments
        "192.0.2.0/24",
        "198.18.0.0/15",  # benchmarking
        "198.51.100.0/24",
        "203.0.113.0/24",
        "240.0.0.0/4",
        "255.255.255.255/32",
        "fc00::/7",  # ULA
        "fec0::/10",  # site-local (deprecated)
        "2001:db8::/32",
        "100::/64",  # discard-only
    )
)


class EgressError(Exception):
    """Base class for refused or failed outbound requests. Messages are safe to log."""


class EgressPolicyError(EgressError):
    """The URL or its resolved address violates the egress policy."""


class ResponseTooLargeError(EgressError):
    """The response body exceeded the configured maximum."""


class DisallowedContentTypeError(EgressError):
    """The response content type is not in the allow-list."""


class TooManyRedirectsError(EgressError):
    """The redirect chain exceeded the configured maximum."""


class UpstreamError(EgressError):
    """Network-level failure (DNS, connect, TLS, timeout)."""


@dataclass(frozen=True)
class EgressPolicy:
    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    allowed_ports: frozenset[int] = frozenset({80, 443})
    max_redirects: int = 5
    max_response_bytes: int = 10 * 1024 * 1024
    total_timeout_s: float = 30.0
    connect_timeout_s: float = 5.0
    read_timeout_s: float = 15.0
    allowed_content_types: frozenset[str] | None = None  # e.g. {"text/html"}; None = any
    # False returns 3xx responses as-is (the crawler records every hop itself).
    follow_redirects: bool = True


@dataclass
class SafeResponse:
    status_code: int
    headers: httpx.Headers
    url: str
    content: bytes
    redirect_chain: list[str] = field(default_factory=list)
    truncated: bool = False

    @property
    def content_type(self) -> str:
        return str(self.headers.get("content-type", "")).split(";", 1)[0].strip().lower()

    def text(self) -> str:
        charset = "utf-8"
        for part in self.headers.get("content-type", "").split(";")[1:]:
            name, _, value = part.strip().partition("=")
            if name.lower() == "charset" and value:
                charset = value.strip("\"' ")
        try:
            return self.content.decode(charset, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


def _embedded_ipv4(ip: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    if ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    if ip in _NAT64_PREFIX:
        return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    if ip.sixtofour is not None:
        return ip.sixtofour
    if ip.teredo is not None:
        return ip.teredo[1]
    return None


def is_public_address(ip: IPAddress) -> bool:
    """True only for globally routable unicast addresses."""
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = _embedded_ipv4(ip)
        if embedded is not None:
            return is_public_address(embedded)
        if ip.scope_id:
            return False
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    ):
        return False
    return not any(ip in net for net in _EXTRA_BLOCKED if net.version == ip.version)


async def system_resolver(host: str, port: int) -> list[str]:
    """Resolve ``host`` with the OS resolver (non-blocking)."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        msg = f"DNS resolution failed for {host}"
        raise UpstreamError(msg) from exc
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


def _parse_ip_literal(host: str) -> IPAddress | None:
    """Parse ``host`` as an IP, including legacy IPv4 forms browsers/libc accept.

    ``inet_aton`` understands decimal (``2130706433``), hex (``0x7f000001``), octal
    (``0177.0.0.1``) and shorthand (``127.1``) spellings of IPv4 addresses. Treating
    them as literals ensures they are policy-checked instead of being handed to a
    resolver that might interpret them differently.
    """
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    try:
        return ipaddress.IPv4Address(socket.inet_aton(host))
    except OSError:
        return None


@dataclass(frozen=True)
class _Target:
    url: httpx.URL
    host: str
    port: int
    pinned_ip: str


class SafeHttpClient:
    """Async HTTP client that enforces :class:`EgressPolicy` on every hop."""

    def __init__(
        self,
        policy: EgressPolicy | None = None,
        *,
        resolver: Resolver = system_resolver,
        transport: httpx.AsyncBaseTransport | None = None,
        proxy: str | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.policy = policy or EgressPolicy()
        self._resolver = resolver
        self._proxy = proxy
        self._user_agent = user_agent
        self._client = httpx.AsyncClient(
            transport=transport,
            proxy=proxy,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(
                self.policy.read_timeout_s, connect=self.policy.connect_timeout_s
            ),
        )

    async def __aenter__(self) -> SafeHttpClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def validate_url(self, url: str, policy: EgressPolicy | None = None) -> _Target:
        """Validate ``url`` and resolve it to a pinned public IP, or raise."""
        policy = policy or self.policy
        try:
            parsed = httpx.URL(url)
        except (httpx.InvalidURL, TypeError, ValueError) as exc:
            raise EgressPolicyError("invalid URL") from exc
        if parsed.scheme not in policy.allowed_schemes:
            raise EgressPolicyError(f"scheme {parsed.scheme!r} is not allowed")
        if parsed.userinfo:
            raise EgressPolicyError("credentials in URLs are not allowed")
        host = parsed.host
        if not host:
            raise EgressPolicyError("URL has no host")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in policy.allowed_ports:
            raise EgressPolicyError(f"port {port} is not allowed")

        literal = _parse_ip_literal(host)
        addresses = [str(literal)] if literal else await self._resolver(host, port)
        if not addresses:
            raise UpstreamError(f"no addresses for {host}")
        for address in addresses:
            ip = _parse_ip_literal(address)
            if ip is None or not is_public_address(ip):
                # Reject if ANY record is internal: mixed answers are a rebinding trick.
                raise EgressPolicyError(f"{host} resolves to a non-public address")
        return _Target(url=parsed, host=host, port=port, pinned_ip=addresses[0])

    def _build_request(
        self, target: _Target, method: str, headers: httpx.Headers, content: bytes | None
    ) -> httpx.Request:
        headers = headers.copy()
        headers.setdefault("user-agent", self._user_agent)
        default_port = 443 if target.url.scheme == "https" else 80
        headers["host"] = (
            target.host if target.port == default_port else f"{target.host}:{target.port}"
        )
        if self._proxy:
            # The egress proxy connects; it enforces the same policy on its side.
            return self._client.build_request(method, target.url, headers=headers, content=content)
        ip = ipaddress.ip_address(target.pinned_ip)
        ip_host = f"[{ip}]" if ip.version == 6 else str(ip)  # noqa: PLR2004
        pinned_url = target.url.copy_with(host=ip_host.strip("[]"))
        extensions = {"sni_hostname": target.host} if target.url.scheme == "https" else {}
        return self._client.build_request(
            method, pinned_url, headers=headers, content=content, extensions=extensions
        )

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        policy: EgressPolicy | None = None,
    ) -> SafeResponse:
        """Perform a request under the policy. Raises :class:`EgressError` on refusal.

        ``policy`` tightens limits for one call (e.g. a tiny verification file).
        """
        policy = policy or self.policy
        try:
            async with asyncio.timeout(policy.total_timeout_s):
                return await self._request(
                    method, url, httpx.Headers(headers or {}), content, policy
                )
        except TimeoutError as exc:
            raise UpstreamError("request exceeded the total time limit") from exc

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        policy: EgressPolicy | None = None,
    ) -> SafeResponse:
        return await self.request("GET", url, headers=headers, policy=policy)

    async def _request(
        self,
        method: str,
        url: str,
        headers: httpx.Headers,
        content: bytes | None,
        policy: EgressPolicy,
    ) -> SafeResponse:
        chain: list[str] = []
        current_url, current_method, current_content = url, method.upper(), content
        for _ in range(policy.max_redirects + 1):
            target = await self.validate_url(current_url, policy)
            request = self._build_request(target, current_method, headers, current_content)
            try:
                response = await self._client.send(request, stream=True)
            except httpx.HTTPError as exc:
                msg = f"request to {target.host} failed: {type(exc).__name__}"
                raise UpstreamError(msg) from exc
            try:
                if (
                    policy.follow_redirects
                    and response.status_code in _REDIRECT_STATUSES
                    and "location" in response.headers
                ):
                    next_url = str(target.url.join(response.headers["location"]))
                    chain.append(str(target.url))
                    if httpx.URL(next_url).netloc != target.url.netloc:
                        headers = httpx.Headers(
                            {
                                k: v
                                for k, v in headers.items()
                                if k.lower() not in _SENSITIVE_HEADERS
                            }
                        )
                    if response.status_code == 303 or (  # noqa: PLR2004
                        response.status_code in {301, 302} and current_method == "POST"
                    ):
                        current_method, current_content = "GET", None
                    current_url = next_url
                    continue
                self._check_content_type(response.headers, policy)
                body = await self._read_capped(response, policy)
                return SafeResponse(
                    status_code=response.status_code,
                    headers=response.headers,
                    url=str(target.url),
                    content=body,
                    redirect_chain=chain,
                )
            finally:
                await response.aclose()
        raise TooManyRedirectsError(f"more than {policy.max_redirects} redirects")

    @staticmethod
    def _check_content_type(headers: httpx.Headers, policy: EgressPolicy) -> None:
        allowed = policy.allowed_content_types
        if allowed is None:
            return
        content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in allowed:
            raise DisallowedContentTypeError(f"content type {content_type!r} is not allowed")

    @staticmethod
    async def _read_capped(response: httpx.Response, policy: EgressPolicy) -> bytes:
        limit = policy.max_response_bytes
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise ResponseTooLargeError(f"response declares {declared} bytes (limit {limit})")
        chunks: list[bytes] = []
        size = 0
        try:
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > limit:
                    raise ResponseTooLargeError(f"response exceeded {limit} bytes")
                chunks.append(chunk)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"error while reading response: {type(exc).__name__}") from exc
        return b"".join(chunks)


def _strip_sensitive(headers: httpx.Headers) -> httpx.Headers:
    return httpx.Headers({k: v for k, v in headers.items() if k.lower() not in _SENSITIVE_HEADERS})


def normalize_public_url(url: str, *, schemes: Iterable[str] = ("http", "https")) -> str:
    """Syntactic URL validation for user input (no network). Returns the normalised URL."""
    try:
        parsed = httpx.URL(url.strip())
    except (httpx.InvalidURL, TypeError, ValueError) as exc:
        raise EgressPolicyError("invalid URL") from exc
    if parsed.scheme not in set(schemes) or not parsed.host or parsed.userinfo:
        raise EgressPolicyError("URL must be http(s), have a host and no credentials")
    return str(parsed)
