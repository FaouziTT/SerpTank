"""Identity HTTP API (``/api/v1/auth``).

Browser flows are cookie-session based. Every state-changing request must carry the
CSRF token from ``GET /auth/csrf`` (enforced by ``CsrfMiddleware``); anonymous flows
(login, register, password reset, passkey sign-in) additionally require the
pre-session cookie, which binds the CSRF token and OAuth/WebAuthn challenges to this
browser.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlencode

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select, update

from serptank.core.audit import AuditEvent, record_audit_event
from serptank.core.crypto import generate_token
from serptank.core.db import bind_identity
from serptank.core.errors import AppError, CsrfError, NotFoundError
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.identity import mfa
from serptank.modules.identity.api_keys import create_api_key
from serptank.modules.identity.csrf import (
    csrf_token_for_presession,
    csrf_token_for_session,
    session_storage_key,
)
from serptank.modules.identity.deps import (
    AuthenticatedUser,
    CurrentUser,
    DbSession,
    Identity,
    RecentlyReauthenticated,
    mfa_pending_user,
)
from serptank.modules.identity.google import GoogleSignInError
from serptank.modules.identity.models import ApiKey, MfaTotp, User, WebAuthnCredential
from serptank.modules.identity.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyOut,
    AuditEventOut,
    ChangePasswordRequest,
    CodeRequest,
    CsrfResponse,
    EmailRequest,
    LoginRequest,
    LoginResponse,
    MembershipOut,
    MfaVerifyRequest,
    PasskeyLoginRequest,
    PasskeyOut,
    PasskeyRegisterRequest,
    ReauthRequest,
    RecoveryCodesResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SessionInfo,
    SessionResponse,
    TokenRequest,
    TotpSetupResponse,
    UserOut,
)
from serptank.modules.identity.service import AuthService, ClientInfo, LoginResult
from serptank.modules.identity.sessions import (
    SessionData,
    clear_session_cookie,
    presession_cookie_name,
    session_cookie_name,
    set_session_cookie,
)
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.models import Membership, Organization
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/auth", tags=["auth"])
org_router = APIRouter(prefix="/orgs/{org_id}", tags=["api-keys", "audit"])
logger = structlog.get_logger(__name__)

_AUTH_RATE = rate_limit("auth", Rate(10, 60), Rate(60, 3600))
_EMAIL_RATE = rate_limit("auth-email", Rate(3, 60), Rate(20, 3600))


def _client(request: Request) -> ClientInfo:
    return ClientInfo(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def _presession_token(request: Request, identity: Identity) -> str:
    token = request.cookies.get(presession_cookie_name(identity.settings), "")
    if not token:
        raise CsrfError("Missing pre-session. Fetch /api/v1/auth/csrf first.")
    return token


def require_presession(request: Request, identity: Identity) -> str:
    """Browser-only anonymous flows must carry the pre-session cookie (CSRF-bound)."""
    return _presession_token(request, identity)


Presession = Annotated[str, Depends(require_presession)]


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        email_verified=user.email_verified_at is not None,
        mfa_enabled=user.mfa_enabled,
        has_password=user.password_hash is not None,
        google_linked=user.google_subject is not None,
    )


def _start_session(response: Response, identity: Identity, token: str, data: SessionData) -> str:
    set_session_cookie(response, identity.settings, token, data)
    return csrf_token_for_session(identity.settings, token)


def _login_response(response: Response, identity: Identity, result: LoginResult) -> LoginResponse:
    csrf = _start_session(response, identity, result.token, result.session)
    if result.mfa_required:
        return LoginResponse(status="mfa_required", csrf_token=csrf, mfa_methods=result.mfa_methods)
    return LoginResponse(status="authenticated", csrf_token=csrf, user=_user_out(result.user))


# --------------------------------------------------------------------------- CSRF
@router.get("/csrf", response_model=CsrfResponse)
async def get_csrf_token(request: Request, response: Response, identity: Identity) -> CsrfResponse:
    """Return the CSRF token for this browser, creating a pre-session if needed."""
    settings = identity.settings
    session_token = request.cookies.get(session_cookie_name(settings))
    if session_token and await identity.store.get(session_token):
        return CsrfResponse(csrf_token=csrf_token_for_session(settings, session_token))
    pre = request.cookies.get(presession_cookie_name(settings)) or generate_token(32)
    response.set_cookie(
        presession_cookie_name(settings),
        pre,
        max_age=3600 * 12,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return CsrfResponse(csrf_token=csrf_token_for_presession(settings, pre))


# ------------------------------------------------------------------ registration
@router.post("/register", status_code=202, dependencies=[Depends(_EMAIL_RATE)])
async def register(
    body: RegisterRequest, request: Request, db: DbSession, identity: Identity, _: Presession
) -> dict[str, str]:
    await AuthService(db, identity).register(
        body.email, body.password, body.full_name, _client(request)
    )
    return {"status": "check_email"}


@router.post("/verify-email", status_code=204, dependencies=[Depends(_AUTH_RATE)])
async def verify_email(body: TokenRequest, db: DbSession, identity: Identity) -> None:
    await AuthService(db, identity).verify_email(body.token)


@router.post("/verify-email/resend", status_code=202, dependencies=[Depends(_EMAIL_RATE)])
async def resend_verification(
    body: EmailRequest, db: DbSession, identity: Identity, _: Presession
) -> dict[str, str]:
    await AuthService(db, identity).resend_verification(body.email)
    return {"status": "check_email"}


# ------------------------------------------------------------------------ login
@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    identity: Identity,
    _: Presession,
) -> LoginResponse:
    result = await AuthService(db, identity).login(
        body.email,
        body.password,
        remember=body.remember_me,
        captcha_token=body.captcha_token,
        client=_client(request),
    )
    return _login_response(response, identity, result)


@router.post("/mfa/verify", response_model=LoginResponse, dependencies=[Depends(_AUTH_RATE)])
async def verify_mfa(
    body: MfaVerifyRequest,
    request: Request,
    response: Response,
    db: DbSession,
    identity: Identity,
    auth: Annotated[AuthenticatedUser, Depends(mfa_pending_user)],
) -> LoginResponse:
    token, data = await AuthService(db, identity).complete_mfa(
        auth.user,
        auth.session,
        code=body.code,
        recovery_code=body.recovery_code,
        client=_client(request),
    )
    csrf = _start_session(response, identity, token, data)
    return LoginResponse(status="authenticated", csrf_token=csrf, user=_user_out(auth.user))


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: DbSession, identity: Identity) -> None:
    token = request.cookies.get(session_cookie_name(identity.settings), "")
    data = await identity.store.get(token) if token else None
    if data is not None:
        await identity.store.revoke_key(data.key, data.user_id)
        await bind_identity(db, user_id=data.user_uuid)
        record_audit_event(db, "auth.logout", actor_user_id=data.user_uuid)
        await db.commit()
    clear_session_cookie(response, identity.settings)


@router.post("/logout-all", status_code=204)
async def logout_all(
    response: Response, auth: CurrentUser, db: DbSession, identity: Identity
) -> None:
    await identity.store.revoke_all(auth.user.id)
    record_audit_event(db, "auth.logout_all", actor_user_id=auth.user.id)
    await db.commit()
    clear_session_cookie(response, identity.settings)


@router.post("/reauth", response_model=CsrfResponse, dependencies=[Depends(_AUTH_RATE)])
async def reauthenticate(
    body: ReauthRequest, response: Response, auth: CurrentUser, db: DbSession, identity: Identity
) -> CsrfResponse:
    token, data = await AuthService(db, identity).reauthenticate(
        auth.user, auth.session, password=body.password, code=body.code
    )
    return CsrfResponse(csrf_token=_start_session(response, identity, token, data))


# ---------------------------------------------------------------------- session
@router.get("/session", response_model=SessionResponse)
async def get_session_info(auth: CurrentUser, db: DbSession, identity: Identity) -> SessionResponse:
    rows = await db.execute(
        select(Membership.organization_id, Organization.name, Organization.slug, Membership.role)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == auth.user.id, Organization.deleted_at.is_(None))
        .order_by(Organization.name)
    )
    reauth_until = (
        datetime.fromtimestamp(auth.session.reauth_at + identity.settings.reauth_window_s, UTC)
        if auth.session.reauth_at
        else None
    )
    return SessionResponse(
        user=_user_out(auth.user),
        memberships=[
            MembershipOut(
                organization_id=org_id, organization_name=name, organization_slug=slug, role=role
            )
            for org_id, name, slug, role in rows
        ],
        reauth_valid_until=reauth_until,
    )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(auth: CurrentUser, identity: Identity) -> list[SessionInfo]:
    sessions = await identity.store.list_for_user(auth.user.id)
    return [
        SessionInfo(
            id=s.public_id,
            current=s.key == auth.session.key,
            created_at=datetime.fromtimestamp(s.created_at, UTC),
            last_seen_at=datetime.fromtimestamp(s.last_seen_at, UTC),
            ip=s.ip,
            user_agent=s.user_agent,
            auth_methods=s.auth_methods,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str, auth: CurrentUser, db: DbSession, identity: Identity
) -> None:
    for s in await identity.store.list_for_user(auth.user.id):
        if s.public_id == session_id:
            await identity.store.revoke_key(s.key, s.user_id)
            record_audit_event(db, "auth.session_revoked", actor_user_id=auth.user.id)
            await db.commit()
            return
    raise NotFoundError("Session not found.")


# -------------------------------------------------------------------- passwords
@router.post("/password/forgot", status_code=202, dependencies=[Depends(_EMAIL_RATE)])
async def forgot_password(
    body: EmailRequest, db: DbSession, identity: Identity, _: Presession
) -> dict[str, str]:
    await AuthService(db, identity).forgot_password(body.email)
    return {"status": "check_email"}


@router.post("/password/reset", status_code=204, dependencies=[Depends(_AUTH_RATE)])
async def reset_password(
    body: ResetPasswordRequest, db: DbSession, identity: Identity, _: Presession
) -> None:
    await AuthService(db, identity).reset_password(body.token, body.new_password)


@router.post("/password/change", response_model=CsrfResponse, dependencies=[Depends(_AUTH_RATE)])
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    auth: CurrentUser,
    db: DbSession,
    identity: Identity,
) -> CsrfResponse:
    token, data = await AuthService(db, identity).change_password(
        auth.user, auth.session, body.current_password, body.new_password
    )
    return CsrfResponse(csrf_token=_start_session(response, identity, token, data))


# -------------------------------------------------------------------------- TOTP
@router.post("/mfa/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(
    auth: RecentlyReauthenticated, db: DbSession, identity: Identity
) -> TotpSetupResponse:
    secret = mfa.new_totp_secret()
    await mfa.store_pending_totp(db, identity.keyring, auth.user.id, secret)
    await db.commit()
    return TotpSetupResponse(
        secret=secret, otpauth_uri=mfa.provisioning_uri(secret, auth.user.email)
    )


@router.post(
    "/mfa/totp/confirm", response_model=RecoveryCodesResponse, dependencies=[Depends(_AUTH_RATE)]
)
async def totp_confirm(
    body: CodeRequest, auth: CurrentUser, db: DbSession, identity: Identity
) -> RecoveryCodesResponse:
    ok = await mfa.verify_totp(
        db, identity.keyring, auth.user.id, body.code, require_confirmed=False
    )
    if not ok:
        raise AppError("The code is incorrect. Check your authenticator's clock and try again.")
    auth.user.mfa_enabled = True
    codes = await mfa.regenerate_recovery_codes(
        db, auth.user.id, identity.settings.api_key_pepper.get_secret_value()
    )
    record_audit_event(
        db, "auth.mfa_enabled", actor_user_id=auth.user.id, details={"method": "totp"}
    )
    await db.commit()
    return RecoveryCodesResponse(codes=codes)


@router.delete("/mfa/totp", status_code=204)
async def totp_disable(auth: RecentlyReauthenticated, db: DbSession, identity: Identity) -> None:
    record = await db.get(MfaTotp, auth.user.id)
    if record is not None:
        await db.delete(record)
    passkeys = await db.execute(
        select(func.count()).where(WebAuthnCredential.user_id == auth.user.id)
    )
    auth.user.mfa_enabled = bool(passkeys.scalar_one())
    record_audit_event(
        db, "auth.mfa_disabled", actor_user_id=auth.user.id, details={"method": "totp"}
    )
    await db.commit()


@router.post("/mfa/recovery-codes", response_model=RecoveryCodesResponse)
async def regenerate_recovery_codes(
    auth: RecentlyReauthenticated, db: DbSession, identity: Identity
) -> RecoveryCodesResponse:
    codes = await mfa.regenerate_recovery_codes(
        db, auth.user.id, identity.settings.api_key_pepper.get_secret_value()
    )
    record_audit_event(db, "auth.recovery_codes_regenerated", actor_user_id=auth.user.id)
    await db.commit()
    return RecoveryCodesResponse(codes=codes)


# ---------------------------------------------------------------------- passkeys
@router.post("/passkeys/register/options")
async def passkey_register_options(
    auth: RecentlyReauthenticated, db: DbSession, identity: Identity
) -> dict[str, Any]:
    return await identity.passkeys.registration_options(db, auth.user, auth.session.key)


@router.post("/passkeys/register", response_model=PasskeyOut)
async def passkey_register(
    body: PasskeyRegisterRequest, auth: RecentlyReauthenticated, db: DbSession, identity: Identity
) -> PasskeyOut:
    record = await identity.passkeys.register(
        db, auth.user, auth.session.key, body.credential, body.name
    )
    auth.user.mfa_enabled = True
    record_audit_event(db, "auth.passkey_added", actor_user_id=auth.user.id)
    await db.commit()
    return PasskeyOut.model_validate(record, from_attributes=True)


@router.get("/passkeys", response_model=list[PasskeyOut])
async def list_passkeys(auth: CurrentUser, db: DbSession) -> list[PasskeyOut]:
    rows = await db.execute(
        select(WebAuthnCredential)
        .where(WebAuthnCredential.user_id == auth.user.id)
        .order_by(WebAuthnCredential.created_at)
    )
    return [PasskeyOut.model_validate(r, from_attributes=True) for r in rows.scalars()]


@router.delete("/passkeys/{passkey_id}", status_code=204)
async def delete_passkey(
    passkey_id: uuid.UUID, auth: RecentlyReauthenticated, db: DbSession
) -> None:
    record = await db.get(WebAuthnCredential, passkey_id)
    if record is None or record.user_id != auth.user.id:
        raise NotFoundError("Passkey not found.")
    await db.delete(record)
    await db.flush()
    remaining = await db.execute(
        select(func.count()).where(WebAuthnCredential.user_id == auth.user.id)
    )
    totp = await db.get(MfaTotp, auth.user.id)
    auth.user.mfa_enabled = bool(remaining.scalar_one()) or bool(totp and totp.confirmed_at)
    record_audit_event(db, "auth.passkey_removed", actor_user_id=auth.user.id)
    await db.commit()


@router.post("/passkeys/login/options", dependencies=[Depends(_AUTH_RATE)])
async def passkey_login_options(
    request: Request, identity: Identity, pre: Presession
) -> dict[str, Any]:
    return await identity.passkeys.authentication_options(
        session_storage_key(identity.settings, pre)
    )


@router.post("/passkeys/login", response_model=LoginResponse, dependencies=[Depends(_AUTH_RATE)])
async def passkey_login(
    body: PasskeyLoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    identity: Identity,
    pre: Presession,
) -> LoginResponse:
    user_id = await identity.passkeys.authenticate(
        db, session_storage_key(identity.settings, pre), body.credential
    )
    result = await AuthService(db, identity).passkey_sign_in(
        user_id, body.remember_me, _client(request)
    )
    return _login_response(response, identity, result)


# ------------------------------------------------------------------------ Google
@router.get("/google/start")
async def google_start(
    request: Request,
    identity: Identity,
    mode: Annotated[str, Query(pattern="^(login|link)$")] = "login",
) -> RedirectResponse:
    if not identity.settings.google_sign_in_enabled:
        raise NotFoundError("Google sign-in is not enabled.")
    pre = _presession_token(request, identity)
    user_id: str | None = None
    if mode == "link":
        data = await identity.store.get(
            request.cookies.get(session_cookie_name(identity.settings), "")
        )
        if data is None or data.mfa_pending:
            raise NotFoundError("Sign in before linking Google.")
        user_id = data.user_id
    url = await identity.google.start(
        presession_key=session_storage_key(identity.settings, pre), mode=mode, user_id=user_id
    )
    return RedirectResponse(url, status_code=303)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: DbSession,
    identity: Identity,
    state: Annotated[str, Query(max_length=128)] = "",
    code: Annotated[str, Query(max_length=2048)] = "",
    error: Annotated[str | None, Query(max_length=128)] = None,
) -> RedirectResponse:
    origin = identity.settings.public_origin.rstrip("/")

    def fail(reason: str) -> RedirectResponse:
        return RedirectResponse(f"{origin}/login?{urlencode({'error': reason})}", status_code=303)

    pre = request.cookies.get(presession_cookie_name(identity.settings), "")
    if error or not code:
        return fail("google_cancelled")
    try:
        google_identity, record = await identity.google.complete(
            state=state, code=code, presession_key=session_storage_key(identity.settings, pre)
        )
        service = AuthService(db, identity)
        if record["mode"] == "link":
            user = await db.get(User, uuid.UUID(record["user_id"]))
            if user is None:
                return fail("google_failed")
            await bind_identity(db, user_id=user.id)
            await service.link_google(user, google_identity)
            return RedirectResponse(f"{origin}/settings/security?linked=google", status_code=303)
        result = await service.google_sign_in(google_identity, _client(request))
    except GoogleSignInError as exc:
        logger.info("google_sign_in_failed", reason=exc.detail)
        return fail(
            "google_account_exists" if "already exists" in (exc.detail or "") else "google_failed"
        )
    target = "/login/mfa" if result.mfa_required else "/dashboard"
    response = RedirectResponse(f"{origin}{target}", status_code=303)
    set_session_cookie(response, identity.settings, result.token, result.session)
    return response


@router.post("/google/unlink", status_code=204)
async def google_unlink(auth: RecentlyReauthenticated, db: DbSession, identity: Identity) -> None:
    await AuthService(db, identity).unlink_google(auth.user)


# ----------------------------------------------------------------- my security log
@router.get("/security-events", response_model=list[AuditEventOut])
async def my_security_events(auth: CurrentUser, db: DbSession) -> list[AuditEventOut]:
    rows = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.actor_user_id == auth.user.id, AuditEvent.organization_id.is_(None))
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
    )
    return [AuditEventOut.model_validate(r, from_attributes=True) for r in rows.scalars()]


# ---------------------------------------------------------- org API keys and audit
@org_router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    ctx: Annotated[OrgContext, Depends(org_access(Permission.API_KEYS_MANAGE))], db: DbSession
) -> list[ApiKeyOut]:
    rows = await db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == ctx.organization_id)
        .order_by(ApiKey.created_at.desc())
    )
    return [ApiKeyOut.model_validate(r, from_attributes=True) for r in rows.scalars()]


@org_router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_org_api_key(
    body: ApiKeyCreateRequest,
    ctx: Annotated[OrgContext, Depends(org_access(Permission.API_KEYS_MANAGE))],
    auth: RecentlyReauthenticated,
    db: DbSession,
    identity: Identity,
) -> ApiKeyCreatedResponse:
    created = create_api_key(
        db,
        organization_id=ctx.organization_id,
        created_by=auth.user.id,
        name=body.name,
        scopes=body.scopes,
        expires_in_days=body.expires_in_days,
        pepper=identity.settings.api_key_pepper.get_secret_value(),
    )
    await db.flush()
    record_audit_event(
        db,
        "api_key.created",
        actor_user_id=auth.user.id,
        organization_id=ctx.organization_id,
        target_type="api_key",
        target_id=created.record.id,
        details={"scopes": created.record.scopes},
    )
    await db.commit()
    out = ApiKeyOut.model_validate(created.record, from_attributes=True)
    return ApiKeyCreatedResponse(**out.model_dump(), key=created.plaintext)


@org_router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_org_api_key(
    key_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(org_access(Permission.API_KEYS_MANAGE))],
    db: DbSession,
) -> None:
    result = await db.execute(
        update(ApiKey)
        .where(
            ApiKey.id == key_id,
            ApiKey.organization_id == ctx.organization_id,
            ApiKey.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
        .returning(ApiKey.id)
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundError("API key not found.")
    record_audit_event(
        db,
        "api_key.revoked",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        target_type="api_key",
        target_id=key_id,
    )
    await db.commit()


@org_router.get("/audit-events", response_model=list[AuditEventOut])
async def org_audit_events(
    ctx: Annotated[OrgContext, Depends(org_access(Permission.AUDIT_READ))],
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: datetime | None = None,
) -> list[AuditEventOut]:
    stmt = select(AuditEvent).where(AuditEvent.organization_id == ctx.organization_id)
    if before is not None:
        stmt = stmt.where(AuditEvent.created_at < before)
    rows = await db.execute(stmt.order_by(AuditEvent.created_at.desc()).limit(limit))
    return [AuditEventOut.model_validate(r, from_attributes=True) for r in rows.scalars()]


__all__ = ["org_router", "router"]
