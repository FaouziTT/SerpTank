"""CI helper: create the SerpTank roles and extensions on a bare PostgreSQL service.

Usage: python scripts_ci/bootstrap_db.py <owner-dsn> <app-password>

Mirrors infra/postgres/init/*.{sql,sh}, which only run for the docker-compose volume.
"""

from __future__ import annotations

import asyncio
import sys

import asyncpg


async def main(dsn: str, app_password: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        for ext in ("timescaledb", "vector", "pgcrypto", "citext"):
            await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
        await conn.execute(
            """
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'serptank_app') THEN
                CREATE ROLE serptank_app NOLOGIN; END IF;
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'serptank_system') THEN
                CREATE ROLE serptank_system NOLOGIN BYPASSRLS; END IF;
            END $$;
            """
        )
        exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'serptank_api'")
        verb = "ALTER" if exists else "CREATE"
        password = app_password.replace("'", "''")
        await conn.execute(f"{verb} ROLE serptank_api LOGIN PASSWORD '{password}'")
        await conn.execute("GRANT serptank_app TO serptank_api")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
