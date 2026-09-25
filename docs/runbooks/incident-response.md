# Runbook: incident response

**Severity:** SEV1 = data exposure, full outage or payment failure for everyone;
SEV2 = major feature down or degraded; SEV3 = minor.

1. **Declare** in the incident channel: owner, severity, start time. One person leads.
2. **Stabilise** (prefer rollback): `infra/deploy/deploy.sh <previous tag>`. Disable a
   misbehaving feature with its kill switch where one exists (`SERPTANK_LLM_ENABLED=false`,
   empty vendor credentials), or scale workers to 0 for runaway jobs.
3. **Suspected compromise:**
   - Preserve evidence first: `docker compose logs --since 24h > incident-logs.txt`,
     export the security audit log (`audit_events`).
   - Revoke: sign everyone out (rotate `session_secret`), rotate affected secrets
     (`key-rotation.md`), revoke leaked API keys, disconnect affected integrations.
   - Check the audit log for role changes, API-key creation, exports and billing changes.
4. **Communicate:** status page / email for SEV1-2. Personal-data breaches: notify the
   supervisory authority within 72 hours where required and affected customers without
   undue delay (processor duty in the DPA).
5. **Recover and verify:** health checks, Prometheus alerts clear, spot-check tenants.
6. **Post-incident review** within 5 working days: timeline, root cause, fixes with owners.
