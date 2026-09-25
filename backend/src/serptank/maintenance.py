"""Operational maintenance tasks (run by beat, or by hand on the server).

    python -m serptank.maintenance rotate-keys

**Key rotation** (runbook: docs/runbooks/key-rotation.md). Add a new key to
``SERPTANK_ENCRYPTION_KEYS``, make it ``SERPTANK_ENCRYPTION_ACTIVE_KEY_ID``, deploy,
then this task re-encrypts every stored secret still sealed with an older key:
integration credentials and TOTP seeds. When it reports ``remaining: 0`` the old key can
be removed from the keyring. Runs with the scheduler (BYPASSRLS) role because it spans
tenants; it only ever decrypts and re-encrypts in place, never exposing plaintext.

Lives outside ``serptank.core`` because it touches feature-module tables.
"""

from __future__ import annotations

import asyncio
import sys

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from serptank.core.config import get_settings
from serptank.core.crypto import DecryptionError, Keyring, keyring_from_settings
from serptank.modules.identity.mfa import totp_associated_data
from serptank.modules.identity.models import MfaTotp
from serptank.modules.integrations.credentials import _ad as connection_associated_data
from serptank.modules.integrations.models import Connection

logger = structlog.get_logger(__name__)
BATCH = 500


async def rotate_keys(system: AsyncSession, keyring: Keyring) -> dict[str, int]:
    """Re-encrypt secrets sealed with non-active keys. Returns counts per kind."""
    counts = {"connections": 0, "mfa": 0, "failed": 0, "remaining": 0}
    if len(keyring.keys) < 2:  # noqa: PLR2004 - a single key: no rotation in progress
        return counts
    connections = (await system.execute(select(Connection).limit(100_000))).scalars()
    for connection in connections:
        if not keyring.needs_rotation(connection.credentials):
            continue
        ad = connection_associated_data(connection.organization_id, connection.provider)
        try:
            plaintext = keyring.decrypt(connection.credentials, associated_data=ad)
        except DecryptionError:
            counts["failed"] += 1  # key already removed or data corrupted: needs reconnect
            continue
        connection.credentials = keyring.encrypt(plaintext, associated_data=ad)
        counts["connections"] += 1
        if counts["connections"] % BATCH == 0:
            await system.commit()
    seeds = (await system.execute(select(MfaTotp).limit(100_000))).scalars()
    for seed in seeds:
        if not keyring.needs_rotation(seed.secret_encrypted):
            continue
        ad = totp_associated_data(seed.user_id)
        try:
            plaintext = keyring.decrypt(seed.secret_encrypted, associated_data=ad)
        except DecryptionError:
            counts["failed"] += 1
            continue
        seed.secret_encrypted = keyring.encrypt(plaintext, associated_data=ad)
        counts["mfa"] += 1
    await system.commit()
    counts["remaining"] = counts["failed"]
    logger.info("key_rotation", **counts)
    return counts


async def _main(command: str) -> int:
    settings = get_settings()
    url = settings.scheduler_database_url.get_secret_value()
    if command != "rotate-keys" or not url:
        sys.stderr.write("usage: python -m serptank.maintenance rotate-keys (needs scheduler DB)\n")
        return 2
    engine = create_async_engine(url, pool_size=1, max_overflow=0)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as system:
            counts = await rotate_keys(system, keyring_from_settings(settings))
    finally:
        await engine.dispose()
    sys.stdout.write(f"{counts}\n")
    return 0 if counts["remaining"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else "")))
