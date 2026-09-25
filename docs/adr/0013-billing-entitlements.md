# ADR 0013: Stripe billing and entitlements (Module 12)

- **Status:** accepted · **Date:** 2026-09-25 · **Module:** M12

## Context

The legacy app let any user `POST /subscriptions/subscribe` to any plan with arbitrary trial days, and let users write their own usage records (audit finding C3). A commercial SaaS needs real payments, plans enforced on the server, engine add-ons, and honest handling of failed payments.

## Decisions

1. **Plans as data, prices from configuration.**
   - `billing/entitlements.PLANS` defines limits and engines for free, pro and agency.
   - `SERPTANK_STRIPE_PRICES` maps plan and add-on codes to Stripe price ids.
   - The add-ons are `engines_bing` (Bing, Yahoo, DuckDuckGo) and `engines_regional` (Yandex, Baidu, Naver, Seznam).
   - `organizations.addons` holds the purchased add-ons.
   - `plan_of(org)` is now the single way modules resolve the effective plan (it replaced 16 `plan_for(org.plan_code)` call sites).
2. **Only verified Stripe webhooks change a plan.** No API endpoint grants a plan:
   - Checkout creates a Stripe Checkout Session, which requires `billing:manage` plus a recent step-up and is rate-limited.
   - The org's plan changes only when `customer.subscription.*` events arrive.
   - Those events carry `org_id` metadata, which only our server sets, on the session and subscription.
3. **Webhook handling:**
   - The endpoint is `POST /api/v1/billing/stripe/webhook`, the one CSRF-exempt path.
   - Stripe's `t=…,v1=…` HMAC-SHA256 is verified with a constant-time compare and a 5-minute tolerance. Several `v1` values are accepted, which allows secret rotation.
   - Each event id is recorded in `stripe_events` first, so replays and retries are no-ops.
   - The event is then applied under the org's RLS identity.
   - Every plan change is written to the org's audit log as `billing.plan_changed`.
4. **No Stripe SDK.** A small client (`billing/stripe.py`) calls Stripe over `SafeHttpClient`, like every other outbound request (CLAUDE.md). It uses bracketed form encoding, a pinned `Stripe-Version`, and idempotency keys on Checkout (per org, selection and minute).
5. **Dunning:**
   - `invoice.payment_failed` sets `past_due` and starts a grace period (`SERPTANK_BILLING_GRACE_DAYS`, default 7), during which paid features stay on.
   - Beat `expire_grace_periods` drops orgs whose grace has expired to free.
   - `invoice.paid` clears the grace period.
   - Cancellation or `unpaid` means free immediately.
   - **Downgrades keep history.** Rank checks and AI sampling simply stop for engines the plan no longer includes, because every job already filters by entitled engines.
6. **Invoices are Stripe's own.** `GET /billing/invoices` lists them from Stripe, passing through only `https` links. Nothing is generated or invented locally. If Stripe isn't configured, the page says so and still shows plan and usage.
7. **Usage metering** is computed from the real tables: projects, members, tracked keywords, crawled pages this month, SERP requests today, AI samples and LLM tokens this month.
8. **Legacy removed:** `app/api/.../subscriptions.py` (self-serve subscribe and user-writable `/usage/track`), the legacy `billing.py`, and their service and schemas.

## Threat model notes

| Threat | Control |
|---|---|
| Self-granting a paid plan (legacy C3) | There is no endpoint that writes a plan. Only signed webhooks change it, and the checkout UI result is ignored until the webhook arrives |
| Forged or replayed webhooks | HMAC with a secret, a timestamp tolerance, an event-id replay guard, and the webhook is the only CSRF-exempt path |
| Phishing through the checkout redirect | The frontend navigates only to `https://*.stripe.com` URLs returned by our API (tested with a hostile URL) |
| Cross-tenant billing access | `organization_billing` has forced RLS, `billing:manage` is required, and foreign orgs return 404 |
| Accidental double charge | Stripe idempotency keys, and a 409 if a live subscription exists (changes go through the Portal) |

## Verified

- **Backend:** 392 pytest tests pass, with 92% coverage. The billing module is at 86–97%.
  - Form flattening, the price map and plan-from-items.
  - Webhook signatures: valid, wrong secret, altered body, stale timestamp, missing parts, rotated secrets.
  - The overview and usage, checkout request shape (client reference, metadata, line items, idempotency) against a fake Stripe, and portal and invoices with the non-https link dropped.
  - A subscription grants pro plus Bing, and a replay returns duplicate. A forged event returns 400 and changes nothing.
  - Payment failure keeps paid features until grace expiry, then drops to free.
  - Re-subscribe and cancel, and the audit log records each change.
  - Cross-tenant 404, and a 503 when unconfigured.
  - Gates are clean, the migration round-trips, and `alembic check` passes.
- **Frontend:** 59 Vitest tests pass.
- **Playwright e2e (5 tests pass):** the unconfigured billing page with usage.

## Not verified here

- Live Stripe: test-mode keys and prices are needed. Use the Stripe CLI (`stripe listen --forward-to …/api/v1/billing/stripe/webhook`) and run a test-mode checkout.
- Tax, proration and coupon settings. These are configured in the Stripe Dashboard and Portal, not in code.
