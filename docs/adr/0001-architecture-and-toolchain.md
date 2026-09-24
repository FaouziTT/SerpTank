# ADR 0001: Modular monolith, toolchain reset, and legacy strategy

- **Status:** accepted
- **Date:** 2026-09-24
- **Module:** M0 (repo reset and toolchain)

## Context

The pre-overhaul codebase could not be built or run from git:

- the frontend `lib/` layer was excluded by an unscoped `.gitignore` rule;
- the backend manifest was UTF-16;
- CI lived in a directory GitHub never reads;
- the compose files referenced missing Dockerfiles and the wrong environment variables.

The phase 1 audit also found critical security defects (see `docs/execution-plan.md` §2.3). Before any feature work can be trusted, we need a reproducible toolchain and CI gates.

## Decision

1. **Architecture.** A modular monolith: one FastAPI deployable in `backend/src/serptank/` with `core/` (platform) and `modules/<feature>/`.
   - Boundaries are enforced by import-linter (`core` never imports `modules`).
   - Feature modules talk to each other only through service interfaces.
2. **Python toolchain:**
   - uv with a committed `uv.lock` on Python 3.13.
   - Ruff for linting and formatting (replacing black, isort, and flake8).
   - Strict mypy, pytest, bandit, and pip-audit.
3. **Frontend toolchain:**
   - pnpm with a committed `pnpm-lock.yaml`, Node 24 (`.nvmrc`), and ESLint 9 flat config.
   - `next`'s bundled `postcss` is overridden to a patched version.
4. **Legacy strategy: rebuild the foundation, port features.**
   - The old code stays in place (`backend/app`, `backend/alembic`, `backend/scripts`, `backend/tests_legacy`, and the current frontend) as a porting reference.
   - It is excluded from the new lint and type gates.
   - Each part is deleted by the module that replaces it.
5. **CI** runs from the repository root. Every action is pinned to a commit SHA. Secret, dependency, and container scanning are required jobs.
6. **Infrastructure:**
   - One PostgreSQL 17 cluster with TimescaleDB and pgvector, plus Redis with a mandatory password.
   - Ports bind to localhost only, even in development.
   - The legacy Traefik/prod compose files and the Kubernetes manifest are removed; production deployment is rebuilt in M14 for the chosen VPS target.

## Consequences

- **Honest CI.** Only code that passes the new gates is gated. Frontend lint, type-check, and build become required in M4, because the legacy frontend has 974 lint errors and cannot compile without the rebuilt `lib/` layer.
- **Security in every image.** Container images are non-root and minimal; the M0 API image is about 180 MB, against several GB for the legacy image. The headless browser moves to an isolated renderer image in M6.
- **History still holds PII.** Git history still contains the removed PII and PDF. A history rewrite needs a force-push and is deferred until explicitly approved.
