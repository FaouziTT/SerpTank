"""Organization-level connections: ``/api/v1/orgs/{org_id}/integrations`` and the OAuth callback."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete

from serptank.core.audit import record_audit_event
from serptank.core.errors import AppError, ConflictError, NotFoundError
from serptank.core.ratelimit import Rate, rate_limit
from serptank.modules.identity.deps import CurrentUser, DbSession, Identity, Principal
from serptank.modules.integrations.credentials import (
    get_connection,
    google_access_token,
    seal,
    unseal,
)
from serptank.modules.integrations.models import (
    Connection,
    ConnectionStatus,
    ProjectSource,
    Provider,
    SourceKind,
)
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.bing import BingWebmasterClient
from serptank.modules.integrations.providers.ga4 import Ga4Client
from serptank.modules.integrations.providers.google_oauth import SCOPES, GoogleDataOAuth
from serptank.modules.integrations.providers.gsc import GscClient
from serptank.modules.integrations.schemas import (
    AdsAccount,
    AuthorizationUrl,
    BingConnect,
    ConnectionOut,
    GoogleProperties,
    GoogleStart,
    IntegrationsOverview,
    PropertyOption,
)
from serptank.modules.tenancy.deps import OrgContext, org_access
from serptank.modules.tenancy.policies import Permission

router = APIRouter(prefix="/orgs/{org_id}/integrations", tags=["integrations"])
callback_router = APIRouter(prefix="/integrations", tags=["integrations"])

IntegrationsManage = Annotated[OrgContext, Depends(org_access(Permission.INTEGRATIONS_MANAGE))]
OrgRead = Annotated[OrgContext, Depends(org_access(Permission.PROJECT_READ))]
_CONNECT_RATE = rate_limit("integration-connect", Rate(20, 3600))
FEATURE_BY_SCOPE = {scope: feature for feature, scope in SCOPES.items()}


class IntegrationUnavailableError(AppError):
    status = 503
    code = "integration_unavailable"
    title = "This integration isn't configured on this server"


class ProviderFailureError(AppError):
    status = 502
    code = "provider_error"
    title = "The provider refused the request"


def provider_problem(exc: ProviderError) -> AppError:
    return ProviderFailureError(
        exc.message, extra={"provider_code": exc.code, "reauth": exc.reauth}
    )


def _out(connection: Connection) -> ConnectionOut:
    return ConnectionOut(
        provider=connection.provider,
        status=connection.status,
        account_label=connection.account_label,
        scopes=list(connection.scopes),
        features=sorted({FEATURE_BY_SCOPE[s] for s in connection.scopes if s in FEATURE_BY_SCOPE}),
        last_error_code=connection.last_error_code,
        created_at=connection.created_at,
        settings=dict(connection.settings),
    )


@router.get("", response_model=IntegrationsOverview)
async def overview(ctx: OrgRead, db: DbSession, request: Request) -> IntegrationsOverview:
    settings = request.app.state.settings
    connections = [
        _out(c)
        for provider in Provider
        if (c := await get_connection(db, ctx.organization_id, provider)) is not None
    ]
    return IntegrationsOverview(
        connections=connections,
        google_available=settings.google_data_enabled,
        vitals_available=bool(settings.google_api_key.get_secret_value()),
        keyword_planner_available=settings.google_data_enabled
        and bool(settings.google_ads_developer_token.get_secret_value()),
    )


@router.post(
    "/google/start", response_model=AuthorizationUrl, dependencies=[Depends(_CONNECT_RATE)]
)
async def google_start(
    body: GoogleStart, ctx: IntegrationsManage, identity: Identity
) -> AuthorizationUrl:
    if not identity.settings.google_data_enabled:
        raise IntegrationUnavailableError
    oauth = GoogleDataOAuth(identity.settings, identity.redis, identity.http)
    url = await oauth.start(
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.actor_user_id),
        features=list(dict.fromkeys(body.features)),
    )
    return AuthorizationUrl(authorization_url=url)


def _back(org: str | None, **params: str) -> RedirectResponse:
    path = f"/orgs/{org}/integrations" if org else "/dashboard"
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


@callback_router.get("/google/callback", include_in_schema=False)
async def google_callback(  # noqa: PLR0911 - each early return is a distinct failure page
    auth: CurrentUser,
    db: DbSession,
    identity: Identity,
    state: Annotated[str, Query(max_length=200)] = "",
    code: Annotated[str, Query(max_length=2000)] = "",
    error: Annotated[str, Query(max_length=200)] = "",
) -> RedirectResponse:
    oauth = GoogleDataOAuth(identity.settings, identity.redis, identity.http)
    try:
        record = await oauth.consume_state(state)
    except ProviderError:
        return _back(None, error="google_state_invalid")
    org_id = record["org"]
    if record["user"] != str(auth.user.id):
        return _back(org_id, error="google_state_invalid")  # started by someone else
    if error or not code:
        return _back(org_id, error="google_denied")
    # The user must still be allowed to manage integrations in that org (re-checked now).
    try:
        ctx = await org_access(Permission.INTEGRATIONS_MANAGE)(
            org_id=uuid.UUID(org_id), who=Principal(user=auth), db=db
        )
    except AppError:
        return _back(None, error="google_forbidden")
    try:
        tokens = await oauth.exchange(code, record["verifier"])
        email = await oauth.account_email(tokens.access_token)
    except ProviderError as exc:
        return _back(org_id, error=exc.code)
    connection = await get_connection(db, ctx.organization_id, Provider.GOOGLE)
    previous = unseal(identity.keyring, connection) if connection is not None else {}
    refresh = tokens.refresh_token or previous.get("refresh_token")
    if not refresh:
        return _back(org_id, error="google_no_refresh_token")
    creds = {
        "refresh_token": refresh,
        "access_token": tokens.access_token,
        "expires_at": time.time() + tokens.expires_in,
    }
    sealed = seal(identity.keyring, ctx.organization_id, Provider.GOOGLE, creds)
    if connection is None:
        connection = Connection(
            organization_id=ctx.organization_id,
            provider=Provider.GOOGLE,
            credentials=sealed,
            connected_by_user_id=auth.user.id,
        )
        db.add(connection)
    connection.credentials = sealed
    connection.scopes = sorted(set(tokens.scopes))
    connection.account_label = email
    connection.status = ConnectionStatus.ACTIVE
    connection.last_error_code = None
    record_audit_event(
        db,
        "integration.connected",
        actor_user_id=auth.user.id,
        organization_id=ctx.organization_id,
        details={"provider": "google", "features": sorted(record["features"])},
    )
    await db.commit()
    return _back(org_id, connected="google")


@router.put("/bing", response_model=ConnectionOut, dependencies=[Depends(_CONNECT_RATE)])
async def connect_bing(
    body: BingConnect, ctx: IntegrationsManage, db: DbSession, identity: Identity
) -> ConnectionOut:
    try:
        sites = await BingWebmasterClient(identity.http, body.api_key).sites()
    except ProviderError as exc:
        raise provider_problem(exc) from exc
    sealed = seal(identity.keyring, ctx.organization_id, Provider.BING, {"api_key": body.api_key})
    connection = await get_connection(db, ctx.organization_id, Provider.BING)
    if connection is None:
        connection = Connection(
            organization_id=ctx.organization_id,
            provider=Provider.BING,
            credentials=sealed,
            connected_by_user_id=ctx.actor_user_id,
        )
        db.add(connection)
    connection.credentials = sealed
    connection.status = ConnectionStatus.ACTIVE
    connection.last_error_code = None
    connection.account_label = f"{len(sites)} site(s)"
    record_audit_event(
        db,
        "integration.connected",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        details={"provider": "bing"},
    )
    await db.commit()
    await db.refresh(connection)
    return _out(connection)


@router.delete("/{provider}", status_code=204)
async def disconnect(
    provider: Provider, ctx: IntegrationsManage, db: DbSession, identity: Identity
) -> None:
    connection = await get_connection(db, ctx.organization_id, provider)
    if connection is None:
        raise NotFoundError("Not connected.")
    if provider is Provider.GOOGLE:
        try:
            token = unseal(identity.keyring, connection).get("refresh_token")
        except Exception:  # noqa: BLE001 - undecryptable (rotated key): still delete
            token = None
        if token:
            await GoogleDataOAuth(identity.settings, None, identity.http).revoke(str(token))
        kinds = [SourceKind.GSC, SourceKind.GA4]
    else:
        kinds = [SourceKind.BING]
    await db.execute(
        delete(ProjectSource).where(
            ProjectSource.organization_id == ctx.organization_id, ProjectSource.kind.in_(kinds)
        )
    )
    await db.delete(connection)
    record_audit_event(
        db,
        "integration.disconnected",
        actor_user_id=ctx.actor_user_id,
        organization_id=ctx.organization_id,
        details={"provider": provider.value},
    )
    await db.commit()


@router.get("/google/properties", response_model=GoogleProperties)
async def google_properties(ctx: OrgRead, db: DbSession, identity: Identity) -> GoogleProperties:
    connection = await get_connection(db, ctx.organization_id, Provider.GOOGLE)
    if connection is None:
        raise NotFoundError("Google isn't connected.")
    try:
        token = await google_access_token(
            db,
            ctx.organization_id,
            keyring=identity.keyring,
            settings=identity.settings,
            http=identity.http,
        )
        sites = (
            await GscClient(identity.http, token).sites()
            if SCOPES["gsc"] in connection.scopes or SCOPES["gsc_write"] in connection.scopes
            else []
        )
        props = (
            await Ga4Client(identity.http, token).properties()
            if SCOPES["ga4"] in connection.scopes
            else []
        )
    except ProviderError as exc:
        raise provider_problem(exc) from exc
    return GoogleProperties(
        gsc_sites=[
            PropertyOption(id=s["site_url"], label=f"{s['site_url']} ({s['permission']})")
            for s in sites
        ],
        ga4_properties=[PropertyOption(id=p["property_id"], label=p["name"]) for p in props],
    )


@router.get("/bing/sites", response_model=list[PropertyOption])
async def bing_sites(ctx: OrgRead, db: DbSession, identity: Identity) -> list[PropertyOption]:
    connection = await get_connection(db, ctx.organization_id, Provider.BING)
    if connection is None:
        raise NotFoundError("Bing Webmaster Tools isn't connected.")
    try:
        sites = await BingWebmasterClient(
            identity.http, str(unseal(identity.keyring, connection)["api_key"])
        ).sites()
    except ProviderError as exc:
        raise provider_problem(exc) from exc
    return [
        PropertyOption(id=str(s["site_url"]), label=str(s["site_url"]))
        for s in sites
        if s["verified"]
    ]


@router.put("/google/ads", response_model=ConnectionOut)
async def set_ads_account(
    body: AdsAccount, ctx: IntegrationsManage, db: DbSession
) -> ConnectionOut:
    connection = await get_connection(db, ctx.organization_id, Provider.GOOGLE)
    if connection is None or SCOPES["ads"] not in connection.scopes:
        raise ConflictError("Connect Google with the Google Ads permission first.")
    connection.settings = {
        **connection.settings,
        "ads_customer_id": body.customer_id.replace("-", ""),
        "ads_set_at": datetime.now(UTC).isoformat(),
    }
    await db.commit()
    await db.refresh(connection)
    return _out(connection)
