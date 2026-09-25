"""Encryption key rotation re-seals integration credentials and TOTP seeds."""

from __future__ import annotations

import base64
import uuid

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from serptank.core.crypto import Keyring
from serptank.core.models import uuid7
from serptank.maintenance import rotate_keys
from serptank.modules.identity.mfa import totp_associated_data
from serptank.modules.identity.models import MfaTotp, User
from serptank.modules.integrations.credentials import seal, unseal
from serptank.modules.integrations.models import Connection, Provider
from serptank.modules.tenancy.models import Organization


async def test_rotate_keys(owner_session: AsyncSession, owner_engine: AsyncEngine) -> None:
    k1, k2 = Keyring.generate_key(), Keyring.generate_key()
    old = Keyring({"k1": _raw(k1)}, "k1")
    new = Keyring({"k1": _raw(k1), "k2": _raw(k2)}, "k2")
    org = Organization(id=uuid7(), name="Rot", slug=f"rot-{uuid.uuid4().hex[:8]}")
    user = User(id=uuid7(), email=f"rot-{uuid.uuid4().hex[:8]}@example.com")
    owner_session.add_all([org, user])
    await owner_session.flush()
    connection = Connection(
        organization_id=org.id,
        provider=Provider.BING,
        credentials=seal(old, org.id, Provider.BING, {"api_key": "secret"}),
    )
    seed = MfaTotp(
        user_id=user.id,
        secret_encrypted=old.encrypt(
            "JBSWY3DPEHPK3PXP", associated_data=totp_associated_data(user.id)
        ),
    )
    owner_session.add_all([connection, seed])
    await owner_session.commit()

    async with async_sessionmaker(owner_engine, expire_on_commit=False)() as system:
        assert (await rotate_keys(system, old))["connections"] == 0  # single key: no-op
        counts = await rotate_keys(system, new)
    # The shared test database may hold other tests' ciphertexts (other keys), so
    # assert on this test's own rows rather than global counts.
    assert counts["connections"] >= 1
    assert counts["mfa"] >= 1
    await owner_session.refresh(connection)
    await owner_session.refresh(seed)
    assert connection.credentials.split(".")[1] == "k2"
    assert unseal(new, connection) == {"api_key": "secret"}
    assert not new.needs_rotation(seed.secret_encrypted)
    # Once everything is on k2, k1 can be dropped from the keyring.
    only_new = Keyring({"k2": _raw(k2)}, "k2")
    assert unseal(only_new, connection) == {"api_key": "secret"}


def _raw(encoded: str) -> bytes:
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
