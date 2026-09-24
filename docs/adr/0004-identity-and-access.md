# ADR 0004: Identity and access (Module 3)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M3

## Decisions

| Area | Decision |
|---|---|
| Browser auth | Server-side sessions only (Redis). Cookie `__Host-st_session` (HttpOnly, Secure, SameSite=Lax) holds a 256-bit token; Redis stores it under `HMAC(token, session_secret)`. Idle (24 h) and absolute (14 d / 30 d remember-me) timeouts are enforced server-side. Tokens rotate on login, MFA completion, re-auth and password change. A per-user index supports "sign out everywhere" and a device list. The legacy JWT/`localStorage` login is gone. |
| CSRF | Stateless synchronizer token `HMAC(csrf_secret, session_key)`, or bound to a pre-session cookie for anonymous flows (login, register, reset, passkey sign-in). This prevents login CSRF. Enforced by the M1 middleware together with the Origin and Fetch-Metadata checks. |
| Passwords | Argon2id (pwdlib) with transparent bcrypt upgrade. Minimum 12 characters, no composition rules, a local deny-list, and a Have I Been Pwned k-anonymity check (fails open with a log entry). |
| Enumeration | Registration and forgot-password always return 202. Login uses one generic error and verifies a dummy hash for unknown emails. Email verification is required before password sign-in. |
| Brute force | Per-IP limits. A per-account failure window leads to Turnstile CAPTCHA if configured; otherwise throttling applies per *(account, IP)* with progressive delay. There is no global account lockout. |
| MFA | TOTP (encrypted seed, AAD bound to the user, ±1 step, replay-proof via `last_used_step`) plus 10 hashed single-use recovery codes. Passkeys (WebAuthn, ES256/EdDSA/RS256) with required user verification for sign-in count as MFA. An MFA-pending session can only call `/auth/mfa/verify`. Organizations can set `require_mfa`. |
| Step-up | Sensitive operations (TOTP setup and disable, recovery codes, passkey management, API keys, Google unlink) require re-auth within 10 minutes. |
| Google | OIDC Authorization Code + PKCE S256. State, nonce and verifier are server-side, single use and bound to the pre-session. ID tokens are verified against the JWKS (RS256, iss, aud, exp, iat, nonce), and `email_verified` is required. There is **no auto-linking by email**; linking happens only from an authenticated session. |
| API keys | Org-scoped `stk_live_<prefix>_<secret>`. Only the prefix and an HMAC of the secret are stored. Keys have `read`/`write` scopes, expiry and revocation, and last-used is recorded at 5-minute granularity. Keys can never manage members, billing, keys, audit or integrations. |
| RBAC | `tenancy.policies` is the single permission table (owner/admin/editor/viewer/billing). `org_access(permission)` returns **404** for non-members and **403** for members lacking the permission, and binds the tenant for RLS. |
| Pre-auth lookups under RLS | Redeeming emailed tokens, looking up API keys and finding passkey owners use narrow `SECURITY DEFINER` functions for one exact key (`app_consume_email_token`, `app_lookup_api_key`, `app_lookup_webauthn_user`). The app role gets no broad read access. |
| Email | `core.email` provides SMTP (required in production), console and in-memory senders. Mailpit is added to dev compose. Email bodies carrying tokens are never logged. |
| Audit | Registration, login (by method), failures, MFA changes, recovery-code use, re-auth, password changes and resets, session revocation, Google link changes and API key lifecycle events are all logged, with secrets redacted. |

## Verified by tests (as the RLS app role against Postgres and Redis)

- **Auth and sessions:** register → verify → login; login blocked before email verification; enumeration-safe responses; weak and common passwords rejected.
- **CSRF:** a missing pre-session, missing token, token from another browser, or cross-site Origin are all rejected.
- **Session hygiene:** session rotation, logout invalidation, listing and revoking sessions, password reset (single-use token, revokes sessions), password change (revokes other sessions), and brute-force throttling that doesn't lock the owner out from another network.
- **MFA:** TOTP login, code replay rejected, recovery codes single-use, re-auth required for sensitive actions.
- **RBAC:** the role matrix for five roles; 404 for non-members; org MFA requirement.
- **API keys:** create requires re-auth; scopes enforced; tampered or unknown keys rejected; revoked keys fail; keys confined to their org.
- **Google:** state single use and browser-bound, forged signature, wrong aud/iss/nonce, expired token, unverified email, no auto-link, link then sign in.
- **Passkeys:** real WebAuthn ceremonies with a software authenticator (registration, passwordless sign-in, user verification required, clone/sign-count detection, challenge bound to browser and single use, phishing origin rejected).

## Deferred

- **Email address change:** needs verification of the new address. Deferred to M5 settings.
- **Staff impersonation:** needs a consent flow. Deferred to post-launch.
