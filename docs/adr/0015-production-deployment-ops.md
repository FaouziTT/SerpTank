# ADR 0015: Production deployment and operations (Module 14)

- **Status:** accepted · **Date:** 2026-09-25 · **Module:** M14

## Context

The owner chose Docker Compose on a single VPS (plan §0). M14 makes that deployment hardened, repeatable, observable and recoverable, and documents operating it.

## Decisions

1. **Topology** (`docker-compose.prod.yml`):
   - **Caddy** is the only container that publishes ports (80, 443, 443/udp), and serves app and API from one origin (`/api/*` goes to the API, everything else to the web app).
   - **Segmented networks:**
     - `edge`: caddy, web, api.
     - `backend`: an **internal** network, with no internet, for Postgres, Redis and the job runners.
     - `render`: internal, worker to renderer.
     - `egress`: api, worker and renderer to the internet. Outbound calls are still filtered in-process by `SafeHttpClient`.
   - **Trusted proxies:** the API trusts forwarded headers only from the fixed `edge` subnet.
2. **Least privilege:**
   - **Containers:** read-only root filesystems, `cap_drop: ALL` (Caddy gets only `NET_BIND_SERVICE`), `no-new-privileges`, tmpfs scratch space, resource limits, non-root images, and third-party images pinned by digest (Renovate updates them).
   - **Credentials:** each process gets only the Docker secrets it needs. Migrations use the schema-owner URL in a one-shot `migrate` job, while API and workers get the RLS app role and beat gets the scheduler role.
   - **The renderer** now runs with `SERPTANK_COMPONENT=renderer` and validates only its token, so it holds **no** app secrets. Before this, a production renderer would have needed every app secret just to start.
3. **Edge hardening** (`infra/caddy/Caddyfile`):
   - TLS via ACME and HTTP/3.
   - Headers: HSTS, nosniff, referrer policy, permissions policy, COOP/CORP and frame denial. The app's own nonce CSP stays in place.
   - `Server` and `X-Powered-By` are stripped.
   - Internal paths (`/metrics`) return 404.
   - Body-size ceiling, slow-client timeouts, SSE-friendly proxying, and the admin API off.
4. **Releases and deploys** (`.github/workflows/release.yml`, `infra/deploy/deploy.sh`):
   - **Build:** tags build the API, web and renderer images, which must pass Trivy (fixable HIGH/CRITICAL fail). They are pushed to GHCR with SBOM and provenance. Actions are pinned by SHA, and registry login uses the job's short-lived token.
   - **Deploy:** manual and approval-gated through the `production` environment. It runs over SSH with a pinned `known_hosts`, validates the tag, then migrates, rolls the services, health-checks through Caddy, and rolls back automatically to the previous release.
   - Migrations follow expand/contract so one-release rollback is safe.
5. **Backups** (`infra/backup/`):
   - A daily systemd timer takes a `pg_dump`, encrypts it with `age` to an offline public key (the server can't read its own backups), and uploads it with `rclone` to versioned, object-locked storage.
   - A dead-man's-switch ping runs on success, and a size sanity check runs before upload.
   - `restore.sh` supports the monthly drill (into a scratch database) and a confirmed production restore.
   - RPO is 24 h. PITR (pgBackRest) is documented as the next step.
6. **Observability:**
   - Prometheus is an opt-in profile, reachable only through an SSH tunnel. It scrapes the API's internal metrics port.
   - Alert rules cover API down, 5xx over 2%, p95 over 2 s, auth-failure spikes and 403 spikes.
   - External uptime checks and a backup dead-man's switch are required by the launch checklist.
7. **Key rotation:** `serptank.maintenance.rotate_keys` (CLI plus daily beat) re-encrypts integration credentials and TOTP seeds sealed with non-active keys. It only runs while the keyring holds more than one key, so rotation can finish and the old key can be removed. Other secrets are covered in `docs/runbooks/key-rotation.md`.
8. **Host hardening** (`infra/vps/harden.sh`, Ubuntu 24.04):
   - An admin user with key-only SSH and no root or password logins.
   - An nftables default-deny policy allowing 22 (optionally source-restricted), 80 and 443.
   - Unattended upgrades, fail2ban and sysctl hardening.
   - An unprivileged `serptank` deploy user with a mode-700 secrets directory.
9. **Security testing:**
   - An OWASP ZAP baseline workflow runs manually and only against an https staging target. It fails on missing security headers, insecure cookies and error disclosure.
   - A k6 smoke test (public and read paths, SLO thresholds) and a rank-check spike test (202 or 409 expected, never 5xx).
10. **Docs:** runbooks (deploy, backup and restore drill, key rotation, incident response), a pre-launch checklist, and a secrets inventory with sops config.

## Verified

- `docker compose -f docker-compose.prod.yml config` is valid, including the monitoring profile.
- `caddy validate` reports a valid configuration, and `promtool` passes both config and rules (5 rules).
- shellcheck is clean on every script. actionlint is clean on all workflows (it also fixed two warnings in CI).
- k6 smoke against a locally running API passes every threshold (p95 1.8 ms, 0% errors). The spike script runs; it needs staging API keys for a real result.
- Backend: 398 pytest tests pass, with 92% coverage, including the new key-rotation and renderer-config tests. Gates are clean.

## Not verified here

- **Building the images in this sandbox:** `docker build` can't reach PyPI or npm from inside the build (the sandbox's egress proxy isn't available to builds). The CI `api-image`, `web-image` and `renderer-image` jobs build and scan them.
- **A real VPS deploy:** ACME issuance, backups to object storage, the restore drill, ZAP against staging and Lighthouse are all on `docs/launch-checklist.md`.
- The ZAP image is referenced by tag in a `run:` step, which Renovate doesn't pin. Pin its digest when adopting the workflow.
