# SerpTank

Google-first SEO and AI-search visibility platform (multi-tenant SaaS).

> **Status: under active overhaul.** The roadmap, security architecture and module plan
> are in [`docs/execution-plan.md`](docs/execution-plan.md). Development conventions and
> commands are in [`CLAUDE.md`](CLAUDE.md).

| | |
|---|---|
| Backend | Python 3.13 · FastAPI · PostgreSQL 17 (TimescaleDB, pgvector) · Redis · Celery (`backend/`) |
| Frontend | Next.js · React · Tailwind (`frontend/`) |
| Local infra | `docker compose -f docker-compose.dev.yml up -d --wait` (see `.env.example`) |

Security issues: see [`SECURITY.md`](SECURITY.md).
