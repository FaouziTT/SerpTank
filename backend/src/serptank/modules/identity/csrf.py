"""Session-bound CSRF tokens (synchronizer-token pattern, stateless).

The token is ``HMAC(csrf_secret, "s:" + session_storage_key)`` for authenticated
browsers, and ``HMAC(csrf_secret, "p:" + presession_storage_key)`` before login. The
pre-session variant is what protects *login and registration* against login CSRF.

Unlike the legacy double-submit design, the token cannot be forged from the cookie:
it requires the server-side secret, and it changes whenever the session rotates.
The browser reads it from ``GET /api/v1/auth/csrf`` and sends it as ``X-CSRF-Token``.
"""

from __future__ import annotations

import hashlib
import hmac

from starlette.datastructures import Headers
from starlette.requests import cookie_parser
from starlette.types import Scope

from serptank.core.config import Settings
from serptank.core.crypto import constant_time_equals, hash_token
from serptank.core.middleware import CsrfTokenVerifier, SessionDetector
from serptank.modules.identity.sessions import presession_cookie_name, session_cookie_name

CSRF_HEADER = "x-csrf-token"


def _sign(settings: Settings, message: str) -> str:
    key = settings.csrf_secret.get_secret_value().encode()
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()


def session_storage_key(settings: Settings, token: str) -> str:
    return hash_token(token, pepper=settings.session_secret.get_secret_value())


def csrf_token_for_session(settings: Settings, session_token: str) -> str:
    return _sign(settings, "s:" + session_storage_key(settings, session_token))


def csrf_token_for_presession(settings: Settings, presession_token: str) -> str:
    return _sign(settings, "p:" + session_storage_key(settings, presession_token))


def expected_csrf_token(settings: Settings, cookies: dict[str, str]) -> str | None:
    session = cookies.get(session_cookie_name(settings))
    if session:
        return csrf_token_for_session(settings, session)
    presession = cookies.get(presession_cookie_name(settings))
    if presession:
        return csrf_token_for_presession(settings, presession)
    return None


def build_csrf_hooks(settings: Settings) -> tuple[SessionDetector, CsrfTokenVerifier]:
    """Detector + verifier plugged into :class:`serptank.core.middleware.CsrfMiddleware`."""
    names = (session_cookie_name(settings), presession_cookie_name(settings))

    def has_browser_cookie(headers: Headers) -> bool:
        cookies = cookie_parser(headers.get("cookie", ""))
        return any(cookies.get(name) for name in names)

    async def verify(_scope: Scope, headers: Headers) -> bool:
        expected = expected_csrf_token(settings, cookie_parser(headers.get("cookie", "")))
        provided = headers.get(CSRF_HEADER, "")
        if not expected or not provided:
            return False
        return constant_time_equals(expected, provided)

    return has_browser_cookie, verify
