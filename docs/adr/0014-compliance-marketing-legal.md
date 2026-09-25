# ADR 0014: Compliance, public site and legal pages (Module 13)

- **Status:** accepted · **Date:** 2026-09-25 · **Module:** M13

## Context

A commercial SaaS needs an honest public site, privacy and legal terms that match what the product really does, self-serve data-subject rights, retention, and bot protection on sign-in. The legacy marketing pages contained fabricated testimonials and statistics (audit M7); those were removed in M4 and are not reintroduced.

## Decisions

1. **Public site** (`app/(marketing)`). It covers the landing, pricing, security, privacy, terms, DPA and subprocessors pages. The pages are indexable; the app stays `noindex`. There are also `robots.txt` (the app and API are disallowed), `sitemap.xml` and canonical URLs.
   - **Content rule:** every claim describes a shipped feature. There are no customers, testimonials or numbers we can't back.
2. **Pricing from data.** `GET /api/v1/public/plans` exposes the plan catalog's limits and engines. Display prices come from `SERPTANK_PRICING_DISPLAY`. When a price isn't configured the page says "shown at checkout" rather than inventing one. Stripe stays authoritative.
3. **Legal pages without placeholders.**
   - The operator's name, address, jurisdiction and privacy and security contacts come from the web server's environment.
   - When they're missing, the page shows a clear notice instead of fake details.
   - `security.txt` (RFC 9116) returns 404 until a security contact is configured.
   - **Subprocessors** come from the backend's live configuration (`GET /api/v1/public/config`), so the list always matches what the deployment actually uses.
4. **Cookies.** Only strictly necessary cookies are set (session, pre-session and CSRF), with no analytics or advertising. So there's no consent banner, and the privacy policy says why.
5. **Data-subject rights:**
   - **Export:** `GET /api/v1/auth/me/export` requires a recent step-up and is rate-limited. It returns JSON with the profile, memberships, passkey names, sessions and the user's own security events. It never includes secrets or hashes.
   - **Account deletion:** `DELETE /api/v1/auth/me` requires a recent step-up. It is refused (`last_owner`) while the user is the last owner of an active organization. Otherwise, immediately:
     - all sessions are revoked;
     - memberships and the user's notifications are removed;
     - passkeys, TOTP, recovery codes and email tokens are deleted;
     - the profile is anonymised, which frees the email for reuse.

     The anonymised row is hard-deleted after 30 days.
   - **Organization data** is exported with the M11 CSV exports.
6. **Retention.** A beat job (`purge_expired`) hard-deletes organizations soft-deleted more than `SERPTANK_DELETION_GRACE_DAYS` (30) ago, which cascades through every tenant table, and anonymised users past the grace period.
7. **Turnstile.** The backend already required a CAPTCHA after repeated sign-in failures. The login form now renders Cloudflare Turnstile when the API asks for one and a site key is configured, then sends the token.
   - **CSP:** the script is injected by our own nonce'd bundle, so `strict-dynamic` allows it, and `frame-src` already allows `challenges.cloudflare.com`.
   - **Fallback:** without a site key, the form explains the wait instead.
8. **Accessibility.** The Playwright e2e run checks the public pages with axe (WCAG 2 A and AA). This caught a real issue: the primary colour's contrast was 4.3:1. It is now 5.4:1.

## Threat model notes

| Threat | Control |
|---|---|
| Account takeover followed by data theft or deletion | Export and deletion both need a fresh step-up (password or TOTP), and export is rate-limited |
| Orphaned organizations | The last-owner guard blocks deletion until ownership moves or the org is deleted |
| Stale credentials after deletion | Sessions are revoked server-side, credentials are destroyed, the client discards its CSRF token, and sign-in fails (tested end to end) |
| Misleading legal or security claims | Operator details come from configuration and show a notice when missing. The subprocessor list is generated. `security.txt` is 404 without a contact |
| Bot sign-in attempts | Progressive throttling plus Turnstile after the failure threshold |

## Verified

- **Backend:** 396 pytest tests pass. Coverage includes public pricing and config (a configured subprocessor list only), export content with no secrets, the last-owner refusal, deletion (sessions revoked, credentials gone, anonymised), leaving shared orgs, and the retention purge.
- **Frontend:** 61 Vitest tests pass, including the Turnstile token round-trip on login and the last-owner message.
- **Playwright e2e (7 tests pass):** axe on `/`, `/pricing` and `/privacy`, `robots.txt`, `sitemap.xml`, the security.txt 404, the operator notice, and export with step-up followed by account deletion and a failed sign-in.

## Not verified here

- Legal review. The privacy policy, terms and DPA describe the product accurately but need review by counsel for the operator's jurisdiction before launch.
- A Lighthouse performance budget. It needs a production build on a real host (M14).
- Turnstile against Cloudflare itself (it needs real site and secret keys).
