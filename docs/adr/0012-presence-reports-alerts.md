# ADR 0012: Search Presence dashboard, exports, alerts and notifications (Module 11)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M11

## Context

M6–M10 produce audits, first-party data, rankings, content analyses and AI observations. M11 pulls them into one Google-first view per project and market, lets people take the data out safely, and tells them when something important changes.

## Decisions

1. **Search Presence** (`reports/presence.py`, `GET /projects/{p}/presence?market_id=`). One payload per market covers:
   - the per-engine CTR-weighted share of voice and rank-bucket distribution, Google first;
   - GSC clicks, impressions, CTR and position for 28 days against the previous 28 days;
   - striking-distance opportunities (positions 8–20);
   - the latest audit score and severity counts;
   - the Core Web Vitals pass rate;
   - AI citation rates, carried over from M10.

   **The score** is `100 × (0.8·classic + 0.2·AI)`. The classic part weights each engine's share of voice by its approximate search share in that country. That table is `ENGINE_SHARE`: Google-dominant by default, with Yandex, Baidu, Naver and Seznam weighted for their home markets. When there's no AI data, the score is classic search only and the UI says so. With no data at all there's **no score**.
2. **Reports.** Instead of a PDF engine, the dashboard has print CSS and a "Print / PDF" button that uses the browser's own PDF output. This adds no server dependency (WeasyPrint and headless PDF rendering would bring a large native stack). A weekly summary is sent as the `weekly_digest` alert (Mondays, in-app plus optional email).
3. **CSV exports** (`reports/exports.py`):
   - **Kinds:** rankings, audit issues (latest crawl), GSC queries (28 days) and AI answers.
   - **Generation:** built by an `export` job on the `reports` queue, capped at 100k rows and 20 MB.
   - **Storage:** kept for 24 hours in `exports.content`. The beat job then drops the content and keeps the row as history.
   - **Formula-injection defence:** any cell starting with `= + - @ \t \r` is prefixed with `'`. Numbers stay numeric, and a UTF-8 BOM lets Excel detect the encoding.
4. **Signed download links:**
   - A signed-in reader asks for a link: `POST …/exports/{id}/link`.
   - The link is `/api/v1/exports/{org}/{export}?exp&sig`. It is valid for 15 minutes and works without a session, so it can go to a script or another browser.
   - The HMAC key is derived only for this purpose from the session secret: `HMAC(session_secret, "serptank/export-link/v1")`.
   - The signature covers org, export and expiry, so it can't be extended or pointed at another tenant or export.
   - The download binds the tenant from the verified path before reading, so RLS still applies.
5. **Alerts** (`reports/alerts.py`). There is one rule per project and kind, each with active, threshold and email settings:
   - `rank_drop`: live Google position, the two latest checks, dropping N or more places or out of the top 10.
   - `ai_citation_lost`: cited in the previous sampling, not in the latest.
   - `audit_regression`: the score fell by N or more, or new critical issues appeared.
   - `cwv_poor`: a CrUX assessment of poor.
   - `indexing_lost`: the URL Inspection verdict went from PASS to not PASS.
   - `weekly_digest`: the Monday summary.

   Evaluation runs hourly through beat, or on demand (`POST …/alerts/evaluate`).
6. **Notifications.**
   - **Delivery:** notifications are per user (`notifications`, unique `(user_id, dedupe_key)`) and fan out to every member who can read the project.
   - **Idempotency:** re-evaluating the same change never notifies twice.
   - **Email:** sent only for newly created notifications, only to owners, admins and editors, and only when the rule has email turned on.
   - **Live updates:** `GET /orgs/{org}/notifications/stream` is an SSE stream with cookie auth. It polls every 5 s, sends keepalives, and ends after 5 minutes so the browser reconnects.
   - **UI:** the header bell uses the stream and falls back to polling every 60 s.

## Threat model notes

| Threat | Control |
|---|---|
| CSV/formula injection from crawled titles, queries or keywords | Formula-starting cells are neutralised on every export (tested with `=cmd` and `=HYPERLINK`) |
| Download link abuse | HMAC-SHA256 over org, export and expiry with a purpose-derived key and constant-time compare. 15-minute TTL, `no-store`, `attachment`, 24 h retention |
| Cross-tenant access | `exports`, `alert_rules` and `notifications` have forced RLS. Foreign IDs return 404, and notification reads are scoped to the caller's own inbox (tested) |
| Notification or email floods | Dedupe keys, at most 50 events per rule per evaluation (the rest are summarised), a rate-limited manual evaluation, and email only to writer roles |
| Server load from long-lived SSE | Bounded 5-minute streams, a 5 s poll, and client reconnects |

## Verified

- **Backend:** 387 pytest tests pass, with 91% coverage. The new modules are at 79–94%.
  - CSV neutralisation, and link sign/verify covering tamper, other tenant, other key and expiry.
  - Presence buckets and engine weights.
  - The dashboard with empty honest blanks, then with rankings, GSC and audit data.
  - Exports end to end, including an anonymous signed download, forged or tampered links (403) and a missing signature (422).
  - Every alert kind raises its notification, with email for rank drops, no duplicates on re-evaluation, the SSE stream, read and read-all, and cross-tenant 404.
  - The hourly scheduler.
  - Gates are clean.
- **Frontend:** 56 Vitest tests pass.
- **Playwright e2e (5 tests pass):** the dashboard's honest blanks, toggling an alert, and exporting then downloading rankings through a signed link.

## Not verified here

- SMTP delivery of alert emails; tests use the in-memory sender.
- The weekly digest on a real Monday (the evaluator only runs then).
- White-label reports for agencies. They are deferred and depend on M12 plan features.
