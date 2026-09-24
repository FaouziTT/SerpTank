# ADR 0008: Integrations and indexing (Module 7)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M7

## Context

Google data should come first-party wherever it can: the customer's own Search Console, GA4 and Bing data, plus public field data for Core Web Vitals. First-party AI-search reports exist but have no API yet. Customers also need indexing tools.

## Decisions

1. **Connections.** There is one `connections` row per org and provider:
   - **Google:** OAuth with offline access and incremental scopes.
   - **Bing Webmaster Tools:** the customer's API key.

   Credentials are AES-GCM encrypted with the keyring. The associated data is `connection:<org>:<provider>`, so a ciphertext copied into another org fails to decrypt. Access tokens are cached inside the ciphertext and refreshed before they expire. An `invalid_grant` or a 401 flips the connection to `reauth_required`, and the scheduler stops calling a dead grant. Disconnecting Google revokes the token at Google and unlinks the org's project sources.
2. **Google data OAuth.** It uses a separate client from sign-in and requests only what each feature needs:
   - Search Console read-only;
   - GA4 read-only;
   - optional sitemap write;
   - optional Ads.

   It uses PKCE S256 with server-held `state` (Redis, 10 minutes, single use). The flow is bound to the org and the user who started it. The callback re-checks that the user still has `integrations:manage` and redirects with stable error codes only.
3. **Project sources** (`project_sources`) link a GSC site, a GA4 property or a Bing site to a project.
   - Every link is checked against the connected account's own list of properties.
   - A GSC property must match the project's domain.
   - Linking a GSC property where the user is `siteOwner` or `siteFullUser` counts as **domain-ownership proof** (plan §5.5), with verification method `gsc`.
4. **Syncs** run as jobs on the `integrations` queue and are idempotent: each fetched day or range is replaced, never appended.

   | Source | Fetched per run |
   |---|---|
   | GSC | query × page × country × device per day, paged up to 200k rows per day. The first run backfills 90 days, and every run re-fetches the last 3 days, which Google still revises |
   | GA4 | organic landing pages for the last 30 days |
   | Bing | query statistics (Microsoft `/Date()` values parsed) |
   | CrUX | origin plus key URLs, phone and desktop. A 404 means not enough real-user data, which is stored as nothing rather than guessed |

   - Beat schedules daily syncs and weekly vitals for projects with scheduled audits.
   - Daily metrics live in **TimescaleDB hypertables** with 30-day chunks and RLS, using our own `(project_id, date)` indexes.
5. **AI-search CSV imports.** Search Console's Generative AI report and Bing's AI Performance report have no API, so we import their CSV exports.
   - Columns are matched through aliases, but the schema is strict: a date column and at least one metric are required.
   - Every value is validated, and more than 5% bad rows rejects the whole file.
   - The body is streamed with a 20 MB cap; only this route gets the larger body limit.
   - Both UTF-8 and UTF-16 are accepted.
   - Re-importing replaces the file's date range.
6. **Indexing:**
   - **IndexNow:** a per-project key and a key-file check, submitted per host. Every submission is logged.
   - **Bing:** URL submission through the Webmaster Tools API.
   - **Both require** a verified domain and URLs on the project's own hosts. Foreign URLs are rejected, and the response lists them.
   - **Auto-submit** is opt-in. It sends only new or changed indexable URLs compared with the previous audit, and never on the first audit.
   - **URL Inspection** results are stored. Listing sitemaps is allowed; submitting one needs the extra write scope.
7. **Audit link:** field vitals feed three new page-experience rules: origin poor, origin needs improvement, and key pages poor.
8. **Keyword Planner adapter** (Google Ads REST, developer token plus OAuth). Missing metrics stay missing. The adapter is used by M8.
9. **Logging:** the log redactor strips secret-bearing query parameters (`apikey`, `key`, `token`, `code`) from any logged string, because the Bing and CrUX keys travel in URLs.
10. **UI:**
    - An **org Integrations page:** connect Google with chosen permissions, connect Bing with an API key, see status and reconnect prompts, disconnect.
    - A **project Search data page:** link and sync sources; first-party performance with honest empty states; Core Web Vitals; AI-search imports and totals; URL inspection; IndexNow setup and submission log.

## Threat model notes

| Threat | Control |
|---|---|
| Token theft from the database or backups | Encrypted, context-bound ciphertexts; refresh tokens never leave the server |
| OAuth CSRF or code injection | PKCE, single-use state bound to org and user, permission re-check on callback |
| Linking or submitting someone else's site | Property must be in the account's own list and match the domain; submissions need a verified domain and own-host URLs |
| Secrets in logs | Query-parameter redaction; provider errors mapped to user-safe messages |
| Hostile CSV | Size cap while streaming, strict schema, bad-row threshold, stored as data only |
| Cross-tenant data | RLS on all new tables, including hypertables. A test asserts forced RLS and a policy on **every** table that has an `organization_id` |

## Verified

- **Backend:** 318 pytest tests pass, with 92% coverage. The fake providers enforce what the real ones do:
  - the PKCE verifier matches the challenge;
  - bearer tokens and API keys are checked;
  - IndexNow checks the key location.

  Covered paths:
  - OAuth success, stolen or replayed state, and a bad PKCE verifier;
  - revoked grant leading to `reauth_required`;
  - token refresh and caching;
  - idempotent GSC re-sync;
  - GA4, Bing and vitals syncs;
  - ownership-gated IndexNow;
  - auto-submit after a crawl;
  - URL inspection and the sitemap scope check;
  - CSV parsing edge cases and the upload size limits;
  - the scheduler;
  - the tenant isolation and RLS guard.

  Gates: ruff, mypy, import-linter, bandit and pip-audit are clean, and there is no OpenAPI drift.
- **Frontend:** 44 Vitest tests pass.
- **Playwright e2e (5 tests pass):** the Search data page shows its empty states, creates an IndexNow key, imports a CSV, and shows the Integrations page's "not configured" state.

## Not verified here (needs owner credentials)

- **Live Google, Bing, CrUX, IndexNow and Google Ads calls.** They need a Google Cloud OAuth client with the verified sensitive scopes (webmasters and analytics read-only), an Ads developer token with Basic Access, a CrUX API key, and a real Bing key. Apply for Google OAuth verification and Ads Basic Access now; both take weeks.
- **The exact column headers of the 2026 Gen-AI and Bing AI Performance exports.** The alias table covers the documented names, and an unknown layout fails with a clear message rather than importing wrong data.
