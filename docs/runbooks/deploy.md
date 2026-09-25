# Runbook: first install and deploys

## First install (once per server)
1. Provision Ubuntu 24.04 LTS on an encrypted-disk VPS. Run `infra/vps/harden.sh` as root
   (key-only SSH, nftables allowing 22/80/443, unattended upgrades, fail2ban, sysctl).
2. Install Docker Engine from Docker's apt repository; add user `serptank` to `docker`.
3. As `serptank`: clone the repository to `/opt/serptank` (read-only deploy key).
4. Create secrets (`infra/secrets/README.md`) and `config/app.env`
   (`infra/deploy/app.env.example`), and `config/deploy.env`:
   ```
   SITE_DOMAIN=app.example.com
   ACME_EMAIL=ops@example.com
   GHCR_OWNER=<github org>
   SMTP_HOST=... SMTP_USERNAME=... EMAIL_FROM="SerpTank <no-reply@example.com>"
   LEGAL_ENTITY=... LEGAL_ADDRESS=... PRIVACY_EMAIL=... SECURITY_EMAIL=...
   ```
   Compose reads it via `set -a; . config/deploy.env; set +a` (the deploy script does this).
5. Point DNS (A/AAAA) at the server; Caddy obtains certificates on first start.
6. Enable backups: copy `infra/backup/serptank-backup.{service,timer}` to
   `/etc/systemd/system/`, create `config/backup.env` (`AGE_RECIPIENT`, `BACKUP_REMOTE`,
   optional `HEALTHCHECK_URL`), configure the rclone remote, then
   `systemctl enable --now serptank-backup.timer`.
7. Stripe (if used): create prices, set `SERPTANK_STRIPE_PRICES`, and point a webhook at
   `https://<domain>/api/v1/billing/stripe/webhook` for `checkout.session.completed`,
   `customer.subscription.*`, `invoice.paid`, `invoice.payment_failed`.

## Deploying a release
1. Tag: `git tag v2026.09.25-1 && git push --tags` -> the **Release** workflow builds, scans
   (Trivy) and pushes `api`, `web`, `renderer` images with SBOM + provenance.
2. Run **Release** manually with `release=<tag>` and `deploy=true`; approve the
   `production` environment. It runs `infra/deploy/deploy.sh <tag>` over SSH:
   pull -> migrate (one-shot, schema owner) -> `up --wait` -> public health checks ->
   record the release, or roll back to the previous one.
3. Watch the API 5xx rate and latency (Prometheus alerts) for 15 minutes.

**Migrations must stay backward compatible for one release** (expand, deploy, contract),
because rollback only reverts images.

## Staging
Use the same compose file on a second host with its own secrets and domain. Run the
ZAP baseline workflow and `k6 run infra/k6/smoke.js` against staging before promoting.
