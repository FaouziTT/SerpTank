"""Reusable DDL for migrations: tenant RLS, role grants, TimescaleDB hypertables.

Database roles (created by infrastructure, see infra/postgres/init/02-roles.sh):

* ``serptank_app``    - NOLOGIN group role for the API/workers. Subject to RLS.
* ``serptank_system`` - NOLOGIN, BYPASSRLS. Only for cross-tenant maintenance
  (schedulers enumerating due work, retention jobs). Never used for request handling.

Migrations run as the schema owner. Every table must be granted explicitly; there are
no blanket default privileges, so a forgotten grant fails closed.
"""

from __future__ import annotations

from alembic import op

APP_ROLE = "serptank_app"
SYSTEM_ROLE = "serptank_system"

CRUD = "SELECT, INSERT, UPDATE, DELETE"


def execute_all(*statements: str) -> None:
    """Run statements one by one (asyncpg rejects multi-statement strings)."""
    for statement in statements:
        op.execute(statement)


def require_roles() -> None:
    """Fail with a clear message if the infrastructure roles are missing."""
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}')
             OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{SYSTEM_ROLE}') THEN
            RAISE EXCEPTION 'Roles {APP_ROLE}/{SYSTEM_ROLE} are missing. '
              'Create them first (infra/postgres/init/02-roles.sh).';
          END IF;
        END $$;
        """
    )


def create_identity_functions() -> None:
    """SQL helpers reading the transaction-local identity set by the application."""
    execute_all(
        """CREATE OR REPLACE FUNCTION app_current_org_id() RETURNS uuid
          LANGUAGE sql STABLE PARALLEL SAFE
          AS $$ SELECT nullif(current_setting('app.org_id', true), '')::uuid $$""",
        """CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid
          LANGUAGE sql STABLE PARALLEL SAFE
          AS $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$""",
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}, {SYSTEM_ROLE}")
    op.execute(
        f"GRANT EXECUTE ON FUNCTION app_current_org_id(), app_current_user_id() "
        f"TO {APP_ROLE}, {SYSTEM_ROLE}"
    )


def grant_table(table: str, app_privileges: str = CRUD) -> None:
    op.execute(f"GRANT {app_privileges} ON TABLE {table} TO {APP_ROLE}")
    op.execute(f"GRANT {CRUD} ON TABLE {table} TO {SYSTEM_ROLE}")


def enable_tenant_rls(table: str, *, app_privileges: str = CRUD) -> None:
    """Standard tenant policy: rows are visible/writable only for the bound organization."""
    grant_table(table, app_privileges)
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING (organization_id = app_current_org_id()) "
        f"WITH CHECK (organization_id = app_current_org_id())"
    )


def enable_rls_only(table: str) -> None:
    """Enable + force RLS; the caller creates bespoke policies."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def create_hypertable(table: str, time_column: str, chunk_interval: str = "7 days") -> None:
    """Convert ``table`` into a TimescaleDB hypertable (time-series data, plan §4.1)."""
    op.execute(
        f"SELECT create_hypertable('{table}', by_range('{time_column}', "
        f"INTERVAL '{chunk_interval}'), if_not_exists => TRUE)"
    )
