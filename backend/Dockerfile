# syntax=docker/dockerfile:1.7
# -----------------------------------------------------------------------------
# SerpTank API image (new modular package). Multi-stage, non-root, no build
# tooling or browser in the runtime image (the Playwright renderer gets its own
# isolated image in Module 6).
# Base images should be pinned by digest; Renovate keeps the digests current.
# -----------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS builder

RUN pip install --no-cache-dir uv==0.8.17
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
# Install locked third-party dependencies first (cached layer), then the project.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system --gid 10001 serptank \
    && useradd --system --uid 10001 --gid serptank --no-create-home serptank

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder --chown=root:root /app/.venv /app/.venv
# Migrations ship in the image; M14 runs `alembic upgrade head` as a one-shot job
# with the schema-owner credentials (the API itself connects as serptank_api).
COPY --chown=root:root alembic.ini ./
COPY --chown=root:root migrations ./migrations

USER serptank:serptank
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
# Proxy headers are processed by the app itself (trusted proxies only), so uvicorn's
# own handling is disabled. Server banners are suppressed.
CMD ["uvicorn", "--factory", "serptank.main:create_app", "--host", "0.0.0.0", "--port", "8000", \
     "--no-proxy-headers", "--no-server-header", "--no-date-header", "--timeout-graceful-shutdown", "20"]
