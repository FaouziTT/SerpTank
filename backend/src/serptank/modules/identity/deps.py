"""FastAPI dependencies for authentication.

* :func:`current_user` - a fully authenticated browser session (MFA complete).
* :func:`mfa_pending_user` - a session waiting for its second factor.
* :func:`recent_reauth` - additionally requires a re-authentication in the last
  ``reauth_window_s`` seconds (step-up for sensitive operations).
* :func:`optional_principal` - session *or* API key, used by organization routes.

Resolving a user binds its id to the database session so RLS applies to everything the
request does afterwards.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.config import Settings
from serptank.core.crypto import Keyring
from serptank.core.db import bind_identity, get_session
from serptank.core.email import EmailSender
from serptank.core.errors import AppError, AuthenticationRequiredError
from serptank.core.http import SafeHttpClient
from serptank.modules.identity.api_keys import ApiKeyPrincipal, authenticate_api_key, touch_api_key
from serptank.modules.identity.brute_force import CaptchaVerifier, LoginThrottle
from serptank.modules.identity.google import GoogleOidcClient
from serptank.modules.identity.models import User
from serptank.modules.identity.passkeys import PasskeyService
from serptank.modules.identity.passwords import BreachChecker, PasswordHasher
from serptank.modules.identity.sessions import SessionData, SessionStore, session_cookie_name


class ReauthRequiredError(AppError):
    status = 403
    code = "reauth_required"
    title = "Please confirm your identity"


@dataclass
class IdentityServices:
    """Long-lived identity collaborators, created once in the app lifespan."""

    settings: Settings
    redis: Redis
    store: SessionStore
    hasher: PasswordHasher
    breach_checker: BreachChecker
    throttle: LoginThrottle
    email: EmailSender
    keyring: Keyring
    passkeys: PasskeyService
    google: GoogleOidcClient
    http: SafeHttpClient
    captcha: CaptchaVerifier


def get_identity(request: Request) -> IdentityServices:
    services: IdentityServices = request.app.state.identity
    return services


DbSession = Annotated[AsyncSession, Depends(get_session)]
Identity = Annotated[IdentityServices, Depends(get_identity)]


@dataclass
class AuthenticatedUser:
    user: User
    session: SessionData
    session_token: str


async def _load_session(request: Request, identity: IdentityServices) -> tuple[str, SessionData]:
    token = request.cookies.get(session_cookie_name(identity.settings), "")
    data = await identity.store.get(token) if token else None
    if data is None:
        raise AuthenticationRequiredError("Please sign in.")
    return token, data


async def _load_user(db: AsyncSession, data: SessionData, identity: IdentityServices) -> User:
    user = await db.get(User, data.user_uuid)
    if user is None or not user.is_active or user.deleted_at is not None:
        await identity.store.revoke_key(data.key, data.user_id)
        raise AuthenticationRequiredError("Please sign in.")
    await bind_identity(db, user_id=user.id)
    return user


async def current_user(request: Request, db: DbSession, identity: Identity) -> AuthenticatedUser:
    token, data = await _load_session(request, identity)
    if data.mfa_pending:
        raise AuthenticationRequiredError("Complete two-factor authentication to continue.")
    user = await _load_user(db, data, identity)
    return AuthenticatedUser(user=user, session=data, session_token=token)


async def mfa_pending_user(
    request: Request, db: DbSession, identity: Identity
) -> AuthenticatedUser:
    token, data = await _load_session(request, identity)
    if not data.mfa_pending:
        raise AuthenticationRequiredError("No two-factor verification is pending.")
    user = await _load_user(db, data, identity)
    return AuthenticatedUser(user=user, session=data, session_token=token)


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]


async def recent_reauth(auth: CurrentUser, identity: Identity) -> AuthenticatedUser:
    if not auth.session.recently_reauthenticated(identity.settings.reauth_window_s, time.time()):
        raise ReauthRequiredError("Re-enter your password or authentication code to continue.")
    return auth


RecentlyReauthenticated = Annotated[AuthenticatedUser, Depends(recent_reauth)]


@dataclass
class Principal:
    """Either a signed-in human or an API key (exactly one is set)."""

    user: AuthenticatedUser | None = None
    api_key: ApiKeyPrincipal | None = None


async def principal(request: Request, db: DbSession, identity: Identity) -> Principal:
    authorization = request.headers.get("authorization", "")
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credentials:
            raise AuthenticationRequiredError("Unsupported authorization scheme.")
        key = await authenticate_api_key(
            db, credentials, identity.settings.api_key_pepper.get_secret_value()
        )
        if key is None:
            raise AuthenticationRequiredError("Invalid or expired API key.")
        return Principal(api_key=key)
    return Principal(user=await current_user(request, db, identity))


async def record_api_key_use(db: AsyncSession, key: ApiKeyPrincipal) -> None:
    await touch_api_key(db, key.key_id)
