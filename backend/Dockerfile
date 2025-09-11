# Production Dockerfile for Voltex Backend
# Multi-stage build for optimized image size and security

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Create non-root user for security
RUN groupadd -r voltex && useradd -r -g voltex voltex

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        wget \
        gnupg2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for web crawling (if needed)
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O- https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /etc/apt/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/voltex/.local

# Copy application code
COPY --chown=voltex:voltex . .

# Install Playwright browsers as voltex user
USER voltex
ENV PATH=/home/voltex/.local/bin:$PATH
RUN playwright install chromium

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/home/voltex/.local/bin:$PATH

# Create necessary directories
RUN mkdir -p /app/logs /app/temp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run as non-root user
USER voltex

# Use gunicorn for production with uvicorn workers
CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]