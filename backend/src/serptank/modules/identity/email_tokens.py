"""Single-use, expiring tokens delivered by email (verification, password reset).

Tokens are 256-bit random values; only their keyed hash is stored. Redemption uses the
``app_consume_email_token`` SECURITY DEFINER function, which atomically checks purpose,
expiry and single use and returns the owning user.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from serptank.core.crypto import generate_token, hash_token
from serptank.modules.identity.models import EmailToken, EmailTokenPurpose

TTL = {
    EmailTokenPurpose.VERIFY_EMAIL: timedelta(hours=48),
    EmailTokenPurpose.RESET_PASSWORD: timedelta(minutes=30),
}


async def issue_email_token(
    db: AsyncSession, user_id: uuid.UUID, purpose: EmailTokenPurpose, pepper: str
) -> str:
    """Create a token (invalidating earlier unused ones for the same purpose)."""
    now = datetime.now(UTC)
    await db.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == purpose.value,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = generate_token(32)
    db.add(
        EmailToken(
            user_id=user_id,
            purpose=purpose.value,
            token_hash=hash_token(token, pepper=pepper),
            expires_at=now + TTL[purpose],
        )
    )
    return token


async def consume_email_token(
    db: AsyncSession, token: str, purpose: EmailTokenPurpose, pepper: str
) -> uuid.UUID | None:
    if not token or len(token) > 128:  # noqa: PLR2004
        return None
    result = await db.execute(
        text("SELECT app_consume_email_token(:hash, :purpose)"),
        {"hash": hash_token(token, pepper=pepper), "purpose": purpose.value},
    )
    value = result.scalar_one_or_none()
    if value is None:
        return None
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
