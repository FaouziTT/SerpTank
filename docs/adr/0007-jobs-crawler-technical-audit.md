# ADR 0007: Jobs, crawler and technical SEO audit (Module 6)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M6

## Context

The audit is the first feature that does real work on customers' sites. It needs:

- long-running background work with visible progress;
- a crawler that is safe (no SSRF, no abuse of third-party sites);
- JavaScript rendering;
- a rule engine grounded in Google's published guidance, with other engines layered on top.

## Decisions

1. **Jobs** (`modules/jobs`):
   - A tenant-scoped `jobs` table holds all state: status, progress, stage, counters, result, and a stable `error_code` with a user-safe message.
   - The queue carries only `(org_id, job_id)` as JSON, never pickle.
   - `execute_job` claims the row with a conditional UPDATE (`queued` → `running`), so redelivered messages are no-ops. It binds the tenant before any read; a forged message naming another org finds nothing under RLS.
   - Unexpected exceptions become `internal_error` with a generic message and a logged trace. Exception text never reaches users.
   - A partial unique index allows only one active crawl per project (409).
   - Cancellation is cooperative: handlers stop at their next progress report.
   - Dispatchers:
     - `InProcessDispatcher` (development and tests; the default).
     - `CeleryDispatcher` (required in staging and production; enforced by config validation).
   - Celery 5.6 uses JSON only, `acks_late`, prefetch 1, and a 4-hour time limit.
   - Beat runs `schedule_due_work` every 10 minutes: scheduled audits plus failing jobs whose heartbeat is older than 15 minutes (`worker_lost`). Discovering due work uses the BYPASSRLS scheduler login. The jobs themselves are inserted through tenant-bound sessions.
2. **Progress over Server-Sent Events.** `GET /jobs/{id}/events` polls the row with short-lived sessions and ends at a terminal state, after 30 minutes, or on disconnect. The frontend falls back to polling if EventSource fails.
3. **Crawler** (`modules/crawler`). The engine is pure orchestration over `SafeHttpClient` and emits records to a sink.
   - **Scope:** only the project host and its www twin are fetched. External links are recorded, never followed.
   - **Robots.txt:** our own RFC 9309 evaluator.
     - Group selection per bot, longest match, allow wins ties, `*` and `$` supported.
     - Every page records whether Googlebot and Bingbot may fetch it. Our crawler obeys the `serptankbot` group (else `*`).
     - A 4xx robots.txt means allow all. A 5xx or unreachable robots.txt means disallow all, and the crawl stops with an honest explanation.
   - **Politeness:** one request at a time per host, with a minimum delay or our bot's `crawl-delay` (capped at 10 s).
   - **Redirects and discovery:** redirects are recorded hop by hop (`follow_redirects=False` in `EgressPolicy`). Canonical and hreflang targets are discovered, as Google does.
   - **Order:** a breadth-first crawl for click depth, then sitemap-only URLs while budget remains.
   - **Probes:** a soft-404 probe, an HTTP→HTTPS probe, and a mobile-UA re-fetch of a sample.
   - **Sitemaps:** parsed with `defusedxml` (no DTDs, entities or XXE). Gzip is capped at 50 MB decompressed.
   - **HTML:** parsed with selectolax. Only extracted facts are stored, never full HTML.
   - **Budgets:** the plan's monthly crawl pages, capped per crawl. Unverified domains get a shallow 100-page crawl, and scheduled audits require verification.
4. **Renderer** (`serptank.renderer`, its own image and service):
   - Headless Chromium through Playwright. **Every browser request is intercepted and fetched by `SafeHttpClient`**, so DNS pinning and private-range blocking apply to subresources and to each redirect hop.
   - Chromium gets a black-hole proxy. WebSockets are closed, service workers blocked, and downloads disabled.
   - Per render: a fresh context, request and byte caps, and a hard wall-clock timeout. If a context hangs, the browser restarts.
   - The service requires a bearer token (≥ 32 bytes in production).
   - The crawler calls it through an internal client at an operator-configured URL. This is the one internal call that doesn't go through `SafeHttpClient`, because its destination is never user-controlled.
   - Audits compare raw and rendered HTML on a sample of pages. With no renderer configured, the UI says the rendering checks were skipped.
5. **Audit rules** (`modules/audit`): 74 rules with metadata (severity, effort, explanation, fix, Google documentation link).

   | Category | Rules |
   |---|---|
   | Indexability | 20 |
   | Content | 13 |
   | Crawlability | 7 |
   | Page experience | 7 |
   | Engine deltas | 7 |
   | International | 6 |
   | Rendering | 5 |
   | Structured data | 4 |
   | Links | 3 |
   | Spam red flags | 2 |

   - **Scope:** baseline rules apply everywhere. Engine deltas apply only when the project tracks that engine (Bing blocked pages, noindex or crawl-delay; Google ignoring crawl-delay; Yandex directives; Baidu language), and they never count as Google errors.
   - **Scoring:** `100·100/(100+penalty)`. Penalty is severity weight × reach, where reach is 1 for site-level issues and √(share of pages affected) otherwise. There is a score per engine, with Google as the headline.
   - **Priority** is impact divided by effort.
   - A rule that crashes is reported in `failed_rules`, never silently dropped.
6. **Core Web Vitals** from PageSpeed and CrUX need the Google integrations, so they move to M7. M6 flags slow server responses and oversized HTML.
7. **UI:**
   - A project audit page:
     - run and stop controls, a live progress bar, plan usage and honest failure messages;
     - score cards per engine lens and affected URLs by severity;
     - issues grouped by category and sorted by priority, expandable to explanation, fix, documentation link and paginated occurrences (details shown as plain text);
     - a filterable, searchable URL table;
     - audit history.
   - An automatic-audit schedule on the project page, enabled only for verified domains.
8. **Legacy removed:** `app/services/crawler/*`, `crawler.py`, `diagnostic*.py`, `seo_analysis.py` and the legacy diagnostic endpoints. Their useful ideas were ported. Scrapy, Twisted and pyppeteer are gone for good.

## Threat model notes

| Threat | Control |
|---|---|
| SSRF through crawl targets, redirects, sitemaps or subresources | `SafeHttpClient` on every hop (private, loopback, metadata and CGNAT ranges blocked; IP pinned; ports 80 and 443 only). The renderer intercepts all Chromium traffic. Tested with metadata IPs, a private-IP host and redirects |
| DNS rebinding | Resolve once, reject if any record is internal, connect to the pinned IP |
| Hostile HTML, XML or JS (bombs, XXE, infinite loops, huge pages) | defusedxml, decompression caps, 16 MB page cap, link, JSON-LD and string caps, renderer wall clock and browser restart |
| Using SerpTank to hammer third-party sites | Scope limited to the project host, robots obeyed, per-host serialization with delay, per-org rate limit on starts, monthly budgets, shallow crawl until verified |
| Cross-tenant access to crawls, issues or jobs | RLS on all five new tables, tenant repositories, 404 on foreign IDs (tested). Workers bind the job's tenant |
| Queue poisoning | JSON-only Celery, identifiers only, tenant-bound claim |
| Stored XSS from crawled content | Stored as data. The UI renders it as text only; references open with `noopener noreferrer` |

## Verified

- **Backend:**
  - 281 pytest tests pass, with 92% total coverage.
  - The golden audit of a fixture site with 20 known defects detects all of them, and the Bing lens adds the Bing deltas.
  - SSE stream, cancellation and idempotent redelivery, budget exhaustion (402), tenant isolation, the scheduler and stale-job recovery all have tests.
  - Real headless Chromium renders JavaScript while metadata and loopback requests are blocked, and an infinite-loop page hits the timeout.
  - Every rule category has unit tests on hand-built sites.
  - ruff, mypy strict, import-linter (three contracts), bandit and pip-audit are clean. There is no OpenAPI drift.
- **Frontend:** 41 Vitest tests pass. Lint, format, typecheck and build are clean, and `pnpm audit` is clean.
- **Playwright e2e on the real stack:** 5 tests pass. The audit flow starts a crawl from the UI and receives the honest `robots_unreachable` failure over SSE, because the e2e domain doesn't resolve.

## Not verified here

- **The renderer Docker image.** This sandbox's network policy blocks the Debian mirrors that `playwright install --with-deps` needs. CI builds it (`renderer-image` job). The renderer code itself was verified against a real Chromium.
- **A successful crawl of a live public site end to end.** Egress from this sandbox is proxied. The full pipeline is verified against the fake-internet fixture site.
- **Celery workers against a real broker.** Configuration and dispatch are unit-tested. Workers run the same `execute_job` that the in-process runner exercises in tests.

## Deferred

- Core Web Vitals (PSI and CrUX) → M7.
- IndexNow readiness → M7.
- Full rendered crawls (beyond a sample) as a paid option.
- Per-project crawl settings (include/exclude paths, custom UA).
