# SerpTank web

Next.js 16 (App Router) + React 19 + Tailwind 4 frontend. See `../CLAUDE.md` for commands
and `../docs/adr/0005-frontend-foundation.md` for the architecture.

```bash
pnpm install --frozen-lockfile
pnpm dev             # http://localhost:3000 (proxies /api/* to the backend on :8000)
pnpm lint && pnpm typecheck && pnpm test:run
pnpm e2e             # full stack; start ../docker-compose.dev.yml first
pnpm api:types       # regenerate src/lib/api/schema.d.ts from openapi.json
```

Layout: `src/app` (routes: `(auth)`, `(app)`), `src/features/<area>` (feature UI + API
hooks), `src/components/ui` (Radix primitives), `src/lib` (typed API client, server-side
session, WebAuthn, utils), `src/proxy.ts` (CSP nonce + auth redirect).
