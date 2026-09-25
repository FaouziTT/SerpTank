# Pre-launch checklist

## Platform
- [ ] `infra/vps/harden.sh` applied; SSH key-only; only 22/80/443 open (verify with an external port scan)
- [ ] Disk encryption on the VPS volume; Docker from the official repository
- [ ] All secret files created (distinct, random); `config/app.env` and `deploy.env` reviewed
- [ ] `docker compose config` OK; `docker compose ps` all healthy; only Caddy publishes ports
- [ ] TLS A+ (SSL Labs); HSTS present; add `preload` only after verifying all subdomains
- [ ] Backups: timer enabled, first upload present, dead-man's switch configured, **restore drill done**
- [ ] Prometheus alerts routed to a human (pager/email); external uptime check on `/login`

## Security
- [ ] ZAP baseline against staging: no FAIL rules
- [ ] k6 smoke passes thresholds on staging; rank-check spike: no 5xx
- [ ] Trivy: no fixable HIGH/CRITICAL in release images
- [ ] Renovate enabled; branch protection requires CI on `main`
- [ ] GitHub `production` environment requires reviewer approval
- [ ] `security.txt` served (set `SERPTANK_SECURITY_EMAIL`)

## Product and legal
- [ ] Operator details set (`SERPTANK_LEGAL_*`); privacy, terms and DPA **reviewed by counsel**
- [ ] Subprocessor list matches contracts (DPAs signed with each vendor)
- [ ] Stripe live mode: prices, tax settings, customer portal, webhook endpoint + secret
- [ ] Google OAuth app verification for sensitive scopes (Search Console, Analytics)
- [ ] Google Ads API Basic Access (Keyword Planner) approved, or rented volumes configured
- [ ] Email: SPF, DKIM and DMARC for the sending domain; bounce handling at the provider
- [ ] Live smoke with real vendor keys: `scripts_ci/live_smoke.py`; capture real SERPs into the parser corpus
