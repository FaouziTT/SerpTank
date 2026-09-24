# ADR 0003: Data model and multi-tenancy (Module 2)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M2

## Decisions

1. **Fresh baseline.** The legacy Alembic history (53 user-scoped tables) is removed; there is no production data to migrate. New baseline `0001` creates `users`, `organizations`, `memberships`, `projects`, `project_markets` and `audit_events`.
2. **Keys and time.** UUIDv7 primary keys (time-ordered, non-enumerable); timezone-aware `created_at`/`updated_at` set by the database.
3. **Tenancy.** Every tenant-owned table uses `TenantMixin` (`organization_id NOT NULL`, indexed, `ON DELETE CASCADE`). "Sites" are merged into `projects`.
4. **Engine-aware markets.** `project_markets` stores country (ISO-2, CHECK), language, optional location, device and `search_engine[]` / `ai_engine[]` PostgreSQL enums. At least one engine is required; Google is the default.
5. **Two-layer isolation.**
   - *Application:* `TenantRepository` filters every query by tenant, forces the tenant on insert, returns 404 for foreign rows and refuses a session bound to a different tenant.
   - *Database:* `ENABLE` + `FORCE ROW LEVEL SECURITY` with policies on `app_current_org_id()` / `app_current_user_id()`. The identity is set with transaction-local `set_config` from an SQLAlchemy `after_begin` hook, so it survives commits within a session and never leaks through the pool.
6. **Roles.** `serptank_app` (API/workers, RLS enforced, no ownership) and `serptank_system` (BYPASSRLS, schedulers/maintenance only) are created by infrastructure (`infra/postgres/init/02-roles.sh`), not by migrations. Migrations grant each table explicitly; nothing is granted by default.
7. **Least privilege per table.** `audit_events`: app role has `SELECT, INSERT` only (append-only). `users`: no `DELETE` for the app role (account deletion is a system job with a grace period).
8. **Hypertables.** `migrations/helpers.create_hypertable` is provided; the time-series tables themselves (`rank_observations`, `gsc_daily`, `bing_daily`, `ai_observations`, `vitals`) are created by the modules that write them (M6-M10), so no table exists without code and tests. *(Deviation from plan §6.2 M2, which listed them here.)*

## Notable policies

- `organizations`: SELECT if bound tenant or the user is a member; INSERT only with `created_by_user_id = current user`; UPDATE/DELETE only for the bound tenant.
- `memberships`: SELECT own memberships across orgs (for the org switcher) or the bound tenant's; writes only within the bound tenant.
- `audit_events`: org events visible to the org; user-level events (no org) only to that user.

## Consequences

- `users` has no RLS: login must find a user by email before any identity is bound. Access is confined to the identity module.
- The container healthcheck, API and workers must use the `serptank_api` login role; using the owner role would silently bypass RLS. M14 provisions the credentials accordingly.
- Tests run against a throwaway database migrated with Alembic and assert behaviour **as the real app role** (cross-tenant reads, inserts, moves and updates, GUC leakage across pooled connections, append-only audit, model/migration drift).
