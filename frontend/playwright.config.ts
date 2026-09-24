import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the real stack: Next.js (production build) + FastAPI +
 * PostgreSQL + Redis + Mailpit. Start infrastructure first:
 *   docker compose -f ../docker-compose.dev.yml up -d --wait
 * The API runs as the RLS-restricted `serptank_api` role, exactly like production.
 */
const env = process.env;
const dbUrl =
  env.E2E_DATABASE_URL ??
  "postgresql+asyncpg://serptank_api:devapp-local-only@127.0.0.1:5432/serptank";
const redisUrl = env.E2E_REDIS_URL ?? "redis://:devredis-local-only@127.0.0.1:6379/3";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    launchOptions: env.E2E_CHROMIUM_PATH ? { executablePath: env.E2E_CHROMIUM_PATH } : {},
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "cd ../backend && uv run uvicorn --factory serptank.main:create_app --port 8000 --no-proxy-headers",
      url: "http://127.0.0.1:8000/healthz",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        SERPTANK_ENVIRONMENT: "development",
        SERPTANK_DATABASE_URL: dbUrl,
        SERPTANK_REDIS_URL: redisUrl,
        SERPTANK_PUBLIC_ORIGIN: "http://localhost:3000",
        SERPTANK_ALLOWED_HOSTS: "localhost,127.0.0.1",
        SERPTANK_EMAIL_BACKEND: "smtp",
        SERPTANK_SMTP_HOST: "127.0.0.1",
        SERPTANK_SMTP_PORT: "1025",
        SERPTANK_BREACHED_PASSWORD_CHECK: "false",
        SERPTANK_LOG_JSON: "true",
      },
    },
    {
      command: "pnpm build && pnpm start --port 3000",
      url: "http://localhost:3000/login",
      reuseExistingServer: false,
      timeout: 300_000,
      env: {
        SERPTANK_DEV_PROXY: "1",
        SERPTANK_BACKEND_ORIGIN: "http://127.0.0.1:8000",
        SERPTANK_INTERNAL_API_URL: "http://127.0.0.1:8000",
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
