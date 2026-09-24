"""The baseline migration can be applied, reverted and re-applied without drift."""

from __future__ import annotations

import asyncio

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from serptank.db_models import Base
from tests.conftest import DatabaseUrls, run_migrations


def test_downgrade_and_reupgrade(test_database: DatabaseUrls) -> None:
    run_migrations(test_database.owner_url, "base", downgrade=True)
    run_migrations(test_database.owner_url, "head")


def test_models_match_migrations(test_database: DatabaseUrls) -> None:
    async def diff() -> list[object]:
        engine = create_async_engine(test_database.owner_url)
        async with engine.connect() as conn:
            result = await conn.run_sync(
                lambda sync: compare_metadata(MigrationContext.configure(sync), Base.metadata)
            )
        await engine.dispose()
        return list(result)

    assert asyncio.run(diff()) == []
