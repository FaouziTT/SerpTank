# ADR 0006: Organizations, projects, target markets, members (Module 5)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M5

## Context

M2 created the tenant tables and M3 the identity and RBAC primitives. M5 turns them into the product's top-level structure:

- organizations, members and invitations;
- projects (one website each);
- each project's **target markets** (country, language, optional city, device, and the search and AI engines tracked there);
- domain ownership verification;
- the UI for all of it.

## Decisions

1. **Plan entitlements live in code for now** (`modules/billing/entitlements.py`). Plans are free, pro and agency.
   - Free: Google only (plus the Google AI features), 1 project, 1 market, 2 seats.
   - Pro: adds the Bing family (Bing, Yahoo, DuckDuckGo).
   - Agency: adds the regional engines.
   - Add-ons `engines_bing` and `engines_regional` extend any plan.
   - Violations raise **402 `plan_upgrade_required`** with a `missing` list, so the UI can say exactly what to upgrade.
   - M12 moves plans into data driven by Stripe; the check functions (`require_engines`, `require_below_limit`) stay the same.
   - `GET /orgs/{id}/entitlements` feeds the UI, which shows locked engines as locked rather than hiding them.
2. **Organization creation requires a verified email.** The creator becomes owner. The row gets its UUIDv7 in Python and the tenant identity is bound *before* the insert, because Postgres applies the SELECT policy to `INSERT … RETURNING`.
3. **Invitations:**
   - The token is stored **hashed** (HMAC with the server pepper). It is emailed once and expires after 7 days.
   - **Bound to the invited email address.** The accepting account must have that verified address.
   - Single use. Owners and admins can revoke them.
   - Only owners can invite owners.
   - Duplicate membership is checked **before** the seat limit, so the error is accurate.
   - Acceptance goes through a narrow SECURITY DEFINER lookup (`app_lookup_invitation`), because the invitee has no tenant context yet.
4. **Role management:**
   - A **last-owner guard** blocks demoting or removing the final owner (409 `last_owner`).
   - `can_assign_role` means only owners grant or revoke ownership.
   - **Role changes require a recent step-up** (plan §5.1). The UI uses the shared step-up dialog.
   - Any member may leave an organization themselves.
5. **Organization deletion** is owner-only, requires step-up, and is a soft delete. A 30-day hard-delete job arrives in M13. Turning on `require_mfa` is refused unless the acting admin has MFA, to prevent self-lockout.
6. **Domains** are normalized with IDNA and the Public Suffix List (`accept_unknown=False`). IP addresses, `localhost`, bare public suffixes and unknown TLDs are rejected.
7. **Domain verification.** The token is not secret, since the customer publishes it.
   - **DNS:** a TXT record `serptank-site-verification=<token>` on the registrable domain. The resolver is injectable for tests.
   - **HTML file:** `https://<host>/.well-known/serptank-verification.txt`, fetched through `SafeHttpClient` with a 4 KB and 10 s cap.
   - Checks are rate limited and compared in constant time. Verification is audited.
   - Later modules require it before deep or scheduled crawls and before IndexNow or indexing submissions.
8. **Markets:**
   - Each is unique per project (duplicates return 409), ordered by creation time, and entitlement-checked on create.
   - The last market can't be removed, because every later feature is scoped to one.
   - Projects are soft-deleted and hidden from every query.
9. **UI:**
   - Organization layout (server component): resolves the org and the caller's role through the API. Foreign or unknown orgs render a real **404**, and an org that requires MFA shows an explanation instead of data.
   - Navigation: an org switcher in the shell and role-filtered org navigation. The client mirror of the role matrix only hides controls; the API still decides.
   - Pages: projects (plan usage, honest empty state), project detail (markets, verification instructions, rename, delete), members and invitations, settings (name, require MFA, API keys shown once after step-up, delete with typed confirmation), and audit log (keyset pagination).
   - Invitations: `/invite?token=` accepts an invitation and removes the token from the address bar. The page sets `no-referrer`. Anonymous visitors go to sign-in with `next` preserved.

## Threat model notes

| Threat | Control |
|---|---|
| Cross-tenant access to orgs, projects or markets | RLS plus the tenant repository; foreign IDs return 404 in the API and the UI |
| Invitation token theft or replay | Hashed at rest, single use, 7-day expiry, bound to the invited email, which must be verified, removed from the URL, `no-referrer` |
| Privilege escalation through invitations or role edits | `can_assign_role` (owner-only ownership), last-owner guard, step-up for role changes, audit events |
| Seat or plan bypass | Server-side limit and engine checks on every create; the UI state is advisory only |
| SSRF through HTML-file verification | `SafeHttpClient` (private ranges blocked, IP pinned, size and time capped) |
| Claiming someone else's domain | Proof via DNS TXT or a well-known file; later modules gate crawling and indexing on it |

## Verified

- **Backend:** 209 pytest tests pass (28 new for tenancy and projects), with 92% total coverage.
  - Coverage is now measured correctly for async code: `concurrency = ["greenlet", "thread"]`.
  - ruff, mypy strict, import-linter and bandit are clean. There is no OpenAPI drift.
- **Frontend:** 37 Vitest tests pass (16 new): the permission mirror, market validation, navigation, locked engines, the empty and plan-limit states, invitation errors, and the API key step-up and show-once flow. Lint, format, typecheck and build are clean, and `pnpm audit` is clean.
- **Playwright e2e on the real stack** (5 tests pass). The new flow:
  1. The owner creates an org and a project, and the Bing checkbox is locked on the free plan.
  2. The owner gets the DNS instructions and invites an editor.
  3. The invitee registers, verifies, opens the link, and joins.
  4. The editor has no audit-log link.
  5. The owner sees the new member and the audit trail.
  6. A foreign org URL returns 404.
  - Registration is rate limited per IP, so the e2e helper waits out the limiter rather than weakening it.

## Deferred

- Live DNS and HTML checks against real domains (covered by unit tests with injected resolvers and a fake internet).
- Ownership transfer UI beyond the role select, and a mobile navigation drawer.
- Plan data in the database and Stripe (M12). The org hard-delete retention job (M13).
