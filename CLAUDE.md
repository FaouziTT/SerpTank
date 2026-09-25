# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What SerpTank is

SerpTank is a multi-tenant SEO SaaS with two tracks:

- **Classic search, Google first.** Technical audits, indexing, keyword research, rank tracking, and on-page optimization. Bing, Yahoo, DuckDuckGo, Yandex, Baidu, Naver, and Seznam are plan add-ons.
- **AI search.** Visibility and citations in Google AI Overviews and AI Mode, ChatGPT, Perplexity, Gemini, Copilot, and Claude.

**The roadmap and every architectural and security decision live in [`docs/execution-plan.md`](docs/execution-plan.md). Read it before changing anything.** Work proceeds one module at a time (M0–M14), each in its own PR and each approved by the owner before the next starts. Decisions are recorded as ADRs in `docs/adr/`.

## Repository layout (during the overhaul)

| Path | Status |
|---|---|
| `backend/src/serptank/` | **New** modular-monolith package: `core/` (platform) and `modules/<feature>/`. All new backend code goes here. |
| `backend/tests/` | **New** test suite (pytest). |
| `backend/app/`, `backend/alembic/`, `backend/scripts/`, `backend/tests_legacy/` | **Legacy**, reference only. Do not extend. Port the useful logic into the new package in the owning module, then delete it. |
| `frontend/src/` | Next.js 16 app (rebuilt in M4): `app/` routes, `features/<area>/`, `components/ui/` primitives, `lib/` typed API client (generated from the backend OpenAPI). |
| `infra/` | Infrastructure (Postgres init SQL; Caddy, backups, and more arrive in M14). |
| `docs/` | Execution plan, ADRs, archived audits. |

## Commands

### Backend (`cd backend`, Python 3.13, uv)

```bash
uv sync --locked --all-extras          # install exactly what uv.lock pins (+ renderer extra)
uv run pytest                          # tests (with coverage: --cov)
uv run ruff check . && uv run ruff format --check .
uv run mypy                            # strict
uv run lint-imports                    # module-boundary contracts
uv run bandit -q -r src
uv export --locked --no-dev --all-extras --no-emit-project --format requirements-txt > /tmp/r.txt && uv run pip-audit -r /tmp/r.txt
```

Background jobs run in-process in development (`SERPTANK_JOBS_BACKEND=inprocess`, the default). Production uses Celery workers and beat (same image as the API):

```bash
uv run celery -A serptank.workers.app worker -Q default,crawl -c 2
uv run celery -A serptank.workers.app beat
uv run uvicorn --factory serptank.renderer.app:create_app --port 8100   # isolated JS renderer
```

Paid providers are only ever called by hand: `uv run python scripts_ci/live_smoke.py "query" US en` (see the script header). CI and tests use recorded fixtures and fakes.

The renderer is optional (`SERPTANK_RENDERER_URL` + `SERPTANK_RENDERER_TOKEN`). Without it, audits skip the JavaScript-rendering checks and say so in the UI. Renderer tests need Chromium: `uv run playwright install chromium` and `SERPTANK_TEST_RENDERER=1`.

To add a dependency, run `uv add <pkg>` (or `uv add --group dev <pkg>`) and commit `uv.lock`. Every runtime dependency needs a reason; see plan §7.

### Frontend (`cd frontend`, Node 24, pnpm)

```bash
pnpm install --frozen-lockfile
pnpm lint && pnpm typecheck && pnpm test:run && pnpm build
pnpm audit
pnpm e2e                               # Playwright, full stack (start dev compose first)
pnpm api:types                         # after backend API changes (see below)
```

### API contract

After changing backend routes or schemas, regenerate the frontend types (CI checks drift):

```bash
cd backend && uv run python -m serptank.openapi_export > ../frontend/src/lib/api/openapi.json
cd ../frontend && pnpm api:types
```

### Local infrastructure

```bash
cp .env.example .env                   # set real random passwords
docker compose -f docker-compose.dev.yml up -d --wait
```

This starts PostgreSQL 17 (with TimescaleDB, pgvector, pgcrypto, and citext) and Redis with a mandatory password. Both are bound to `127.0.0.1` only.

### Production (Module 14)

Single hardened VPS with Docker Compose (`docker-compose.prod.yml`): Caddy (TLS, the only
published ports) -> web + api; Celery worker and beat; isolated renderer; Postgres and Redis on
an internal network. Secrets are Docker secret files (`infra/secrets/README.md`).

```bash
infra/deploy/deploy.sh <release-tag>                     # pull, migrate, roll, health-check, auto-rollback
docker compose -f docker-compose.prod.yml run --rm beat python -m serptank.maintenance rotate-keys
```

Runbooks live in `docs/runbooks/` (deploy, backup/restore drill, key rotation, incident response);
`docs/launch-checklist.md` gates go-live. Releases are built by `.github/workflows/release.yml`.

### Repo hygiene

```bash
uvx pre-commit install                 # ruff, gitleaks, basic checks on commit
```

## Non-negotiable rules

- **Tenant isolation.** Every tenant-owned row has `organization_id`. Access goes through the tenant-scoped repository, and Postgres RLS backs it up. Cross-tenant lookups return 404.
- **No outbound request bypasses `SafeHttpClient`** (SSRF protection), including crawls, webhooks, and provider calls.
- **Browser auth is cookie sessions only**: no tokens in `localStorage`, and CSRF plus Origin checks on every unsafe method.
- **Never show fabricated data.** If data is unavailable, say so in the UI.
- **Never return exception text to clients.** Use RFC 9457 Problem Details with stable error codes.
- **No new dependency without a lockfile update and a passing audit.** No unpinned GitHub Actions or base images.
- **Secrets never go in git**: `.env` is ignored, and production secrets are sops-encrypted Docker secrets.
- **Code style.** New code is typed (mypy strict and TS strict), commented where intent isn't obvious, and ships with tests in the same PR.
