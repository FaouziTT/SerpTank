# ADR 0002: Platform core (Module 1)

- **Status:** accepted · **Date:** 2026-09-24 · **Module:** M1

## Decisions

| Area | Decision | Replaces (legacy finding) |
|---|---|---|
| Config | `pydantic-settings`, prefix `SERPTANK_`, Docker secrets via `/run/secrets`. **Fail-closed** in staging/production: purpose-separated secrets (session, CSRF, API-key pepper), ≥32 bytes, all distinct; encryption keyring required; `https` origin; no wildcard hosts. | Single `SECRET_KEY`; warnings only (H7, M4) |
| Errors | RFC 9457 Problem Details with stable `code` and `trace_id`; unhandled exceptions return a generic 500, details only in logs. Validation errors never echo input. | 144 `str(e)` leaks (M1) |
| Logging | structlog JSON; recursive redaction of secret-like keys; emails replaced by a keyed hash; access log omits query strings. | Session IDs/emails in logs (H7) |
| Crypto | AES-256-GCM keyring with key ids and associated data (rotation-ready); HMAC-SHA256 for stored tokens. | Fernet with hard-coded dev key; plaintext reset tokens (H7) |
| SSRF | `SafeHttpClient`: scheme/port/userinfo policy, all resolved addresses must be public (incl. IPv4 embedded in IPv6, decimal/hex/octal IPv4 forms), IP pinning with SNI verification, manual redirects re-validated per hop, credentials stripped cross-origin, size/time/content-type caps, `trust_env=False`. | No SSRF protection (C1) |
| Middleware | Pure ASGI, explicit order: trusted proxy headers → request id/access log → metrics → security headers (CSP, HSTS, nosniff, frame/referrer policy, `no-store`) → Host allow-list → body-size limit → CSRF (Fetch-Metadata + Origin/Referer; session-token hook for M3). | Inverted order, CORS reflection, broken CSRF (C4, H3, M2) |
| Rate limiting | Redis GCRA in one atomic Lua script, server time, per-bucket subjects; client IP only from trusted proxies. | Spoofable `X-Forwarded-For` (H4) |
| Ops | `/healthz` (liveness) and `/readyz` (DB + Redis with 2 s deadline); Prometheus metrics on an internal-only port, route-template labels; docs off in production. | Public `/metrics`, `/docs` (H9) |
| Runtime | `uvicorn --factory`, no server/date header, graceful shutdown; image healthcheck. | Gunicorn + Chrome in API image |

## Threat-model notes

- **DNS rebinding:** mitigated by pinning; if an egress proxy is configured (renderer), the proxy must enforce the same policy (Smokescreen, M6).
- **Host header in health checks:** production `SERPTANK_ALLOWED_HOSTS` must include `127.0.0.1` for the container healthcheck (set in M14 compose).
- **CSRF for API-key clients:** requests without cookies and without `Origin` are treated as non-browser and pass the Origin check; they are still authenticated by API key (M3).
