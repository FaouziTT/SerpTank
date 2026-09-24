# ADR 0005: Frontend foundation (Module 4)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M4

## Context

The legacy frontend could not compile: all 45 routes imported the never-committed `lib/` layer, and most pages rendered fabricated "fallback" data when API calls failed.

## Decisions

1. **Rebuild, don't patch.** A new `src/` app replaces the legacy routes. Only 26 genuine Radix/shadcn UI primitives are kept, lightly fixed. Legacy pages, fake-data charts, the socket.io client and debug routes are removed (they remain in git history). Each later module builds its own pages on real APIs.
2. **Stack:** Next.js **16.3.6**, React **19.3**, Tailwind **4** (CSS-first `@theme`), TypeScript 5.9 strict (with `noUncheckedIndexedAccess`), ESLint 9 flat config, zod 4, react-hook-form, TanStack Query 5, Vitest 5 + Testing Library + MSW, Playwright.
   - ESLint 10 is blocked: `eslint-plugin-react` is incompatible.
   - TypeScript 7 (the Go port) is deferred until the tooling supports it.
3. **Typed API contract.** The backend exports OpenAPI (`python -m serptank.openapi_export`), and `openapi-typescript` generates `schema.d.ts`. CI fails if the committed schema or types drift from the backend. The browser uses `openapi-fetch` with a CSRF middleware: it fetches the token, sends it on unsafe methods and adopts rotated tokens.
4. **Auth UX without tokens in JS.** Cookies are HttpOnly and never read by JS.
   - `proxy.ts` (Next 16's replacement for middleware) only does a cheap cookie-presence redirect.
   - The **authoritative check** is the server-side `getSession()` in `(app)/layout.tsx`, which forwards the cookie to the API.
   - Post-login redirects go through `safeNextPath` (open-redirect safe).
5. **CSP.** A per-request nonce with `script-src 'nonce-…' 'strict-dynamic'`, plus `object-src 'none'`, `base-uri 'none'` and `frame-ancestors 'none'`. All pages render dynamically so nonces apply. `style-src 'unsafe-inline'` is kept because Radix positions overlays with inline style attributes.
6. **Honest states.** Pages show loading, empty and error states. `ErrorState` shows only user-safe problem details plus the trace id, never raw exception text.
7. **Screens delivered:**
   - Auth: register (enumeration-safe copy), email verification, sign in (password, passkey, Google), MFA (TOTP or recovery code), forgot and reset password.
   - App: shell with account menu and a dashboard with an honest empty state.
   - Security settings: password, TOTP with QR code and recovery codes, passkeys, Google link and unlink, active sessions and "sign out everywhere".
   - A generic **step-up re-auth dialog** that transparently retries after `reauth_required`.
8. **Containers.** A standalone Next build on `node:24-bookworm-slim`, non-root, with a healthcheck and no `X-Powered-By` header. In production, Caddy (M14) serves web and API on one origin. Next's `/api` rewrite is for development only.

## Verified

- Lint, format, type-check and production build are clean. `pnpm audit` is clean.
- 21 Vitest tests: CSRF middleware, token rotation, problem mapping, 204 handling, open-redirect guard, CSP and proxy redirects, login form behaviour with MSW.
- 4 Playwright e2e tests against the **real stack** (Next production build + FastAPI as the RLS app role + Postgres + Redis + Mailpit):
  - register → email → verify → sign in → dashboard, with no console errors;
  - anonymous redirect and strict CSP header;
  - generic sign-in error;
  - TOTP enrollment through the step-up dialog, then MFA sign-in with a recovery code.
- The web image builds and runs non-root with the CSP header. Local builds in this sandbox needed `NODE_USE_ENV_PROXY=1` for the egress proxy; that is sandbox-only and not in the Dockerfile.

## Bugs found by the e2e run and fixed

- The CSRF response hook tried to parse JSON from empty 204 bodies, which broke email verification and logout. A regression test now covers it.
- A hydration mismatch from `browserSupportsWebAuthn()` during SSR. Feature detection now uses `useSyncExternalStore`.

## Deferred

- The Cloudflare Turnstile widget: the API reports `captcha_required`; the UI shows a wait message until the widget ships (M13).
- Dark-mode toggle, and the org switcher (M5).
