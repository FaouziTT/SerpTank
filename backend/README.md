# SerpTank backend

FastAPI API and Celery workers for SerpTank. See `../docs/execution-plan.md` for the
roadmap and `../CLAUDE.md` for day-to-day commands.

* `src/serptank/` - the new modular-monolith package (being built module by module).
* `app/`, `alembic/`, `scripts/`, `tests_legacy/` - **legacy** pre-overhaul code, kept only
  as a porting reference. Each part is deleted when the module replacing it lands.

```bash
uv sync --locked            # install (Python 3.13)
uv run pytest               # tests
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports         # module-boundary contracts
```
