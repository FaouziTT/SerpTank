"""Encrypted credential storage and authenticated provider clients.

Credentials are JSON encrypted with the keyring. The associated data binds each
ciphertext to (organization, provider): a value copied into another org's row fails
to decrypt. Access tokens are cached inside the ciphertext with their expiry and
refreshed with the stored refresh token when needed.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.config import Settings
from serptank.core.crypto import Keyring
from serptank.core.http import SafeHttpClient
from serptank.modules.integrations.models import Connection, ConnectionStatus, Provider
from serptank.modules.integrations.providers.base import ProviderError
from serptank.modules.integrations.providers.google_oauth import GoogleDataOAuth

EXPIRY_MARGIN_S = 120


def _ad(organization_id: uuid.UUID, provider: Provider) -> bytes:
    return f"connection:{organization_id}:{provider.value}".encode()


def seal(
    keyring: Keyring, organization_id: uuid.UUID, provider: Provider, data: dict[str, Any]
) -> str:
    return keyring.encrypt(json.dumps(data), associated_data=_ad(organization_id, provider))


def unseal(keyring: Keyring, connection: Connection) -> dict[str, Any]:
    raw = keyring.decrypt(
        connection.credentials, associated_data=_ad(connection.organization_id, connection.provider)
    )
    data: dict[str, Any] = json.loads(raw)
    return data


async def get_connection(
    db: AsyncSession, organization_id: uuid.UUID, provider: Provider
) -> Connection | None:
    result = await db.execute(
        select(Connection).where(
            Connection.organization_id == organization_id, Connection.provider == provider
        )
    )
    return result.scalar_one_or_none()


class NotConnectedError(ProviderError):
    def __init__(self, label: str) -> None:
        super().__init__("not_connected", f"Connect {label} first.")


async def google_access_token(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    keyring: Keyring,
    settings: Settings,
    http: SafeHttpClient,
    scope: str | None = None,
) -> str:
    """A valid Google access token for the org, refreshing (and persisting) if needed.

    Marks the connection ``reauth_required`` (and commits) when Google revoked the grant.
    """
    connection = await get_connection(db, organization_id, Provider.GOOGLE)
    if connection is None or connection.status is ConnectionStatus.REAUTH_REQUIRED:
        raise NotConnectedError("your Google account")
    if scope and scope not in connection.scopes:
        raise ProviderError(
            "google_scope_missing",
            "Grant SerpTank the extra Google permission for this feature first.",
        )
    creds = unseal(keyring, connection)
    if (
        creds.get("access_token")
        and float(creds.get("expires_at", 0)) - EXPIRY_MARGIN_S > time.time()
    ):
        return str(creds["access_token"])
    oauth = GoogleDataOAuth(settings, None, http)
    try:
        tokens = await oauth.refresh(str(creds.get("refresh_token", "")))
    except ProviderError as exc:
        if exc.reauth:
            connection.status = ConnectionStatus.REAUTH_REQUIRED
            connection.last_error_code = exc.code
            await db.commit()
        raise
    creds.update(access_token=tokens.access_token, expires_at=time.time() + tokens.expires_in)
    if tokens.refresh_token:
        creds["refresh_token"] = tokens.refresh_token
    connection.credentials = seal(keyring, organization_id, Provider.GOOGLE, creds)
    connection.status = ConnectionStatus.ACTIVE
    connection.last_used_at = datetime.now(UTC)
    await db.commit()
    return tokens.access_token


async def bing_api_key(db: AsyncSession, organization_id: uuid.UUID, keyring: Keyring) -> str:
    connection = await get_connection(db, organization_id, Provider.BING)
    if connection is None or connection.status is ConnectionStatus.REAUTH_REQUIRED:
        raise NotConnectedError("Bing Webmaster Tools")
    return str(unseal(keyring, connection)["api_key"])


async def record_provider_failure(
    db: AsyncSession, organization_id: uuid.UUID, provider: Provider, exc: ProviderError
) -> None:
    connection = await get_connection(db, organization_id, provider)
    if connection is None:
        return
    connection.last_error_code = exc.code
    connection.status = ConnectionStatus.REAUTH_REQUIRED if exc.reauth else ConnectionStatus.ERROR
    await db.commit()
