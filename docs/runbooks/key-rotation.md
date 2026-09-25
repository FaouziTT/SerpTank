# Runbook: rotating secrets and encryption keys

## Encryption keyring (integration tokens, TOTP seeds)
1. Generate a key: `python -c "from serptank.core.crypto import Keyring; print(Keyring.generate_key())"`.
2. Append it to `secrets/serptank_encryption_keys`: `k1:<old>,k2:<new>`; set
   `SERPTANK_ENCRYPTION_ACTIVE_KEY_ID=k2` in `config/app.env`. Deploy.
3. New writes use `k2`. Beat's maintenance step re-encrypts old values automatically
   (only while more than one key is present), or run it now:
   `docker compose -f docker-compose.prod.yml run --rm beat python -m serptank.maintenance rotate-keys`
   It prints counts and exits non-zero while anything still fails to re-encrypt.
4. When it reports `remaining: 0`, remove `k1` from the file and deploy again.

## Session / CSRF / API-key pepper secrets
- `session_secret`, `csrf_secret`: rotating signs everyone out (sessions and CSRF tokens
  become invalid). Do it after a suspected compromise; announce it.
- `api_key_pepper`: rotating invalidates **all API keys**; customers must recreate them.
  Only after a confirmed leak.

## Database and Redis passwords
Change the role password in Postgres (`ALTER ROLE ... PASSWORD`), update the matching
secret files (password file and URL), then `up -d` the affected services.

## Third-party credentials
Stripe (roll the restricted key and webhook secret in the dashboard), Google OAuth
clients, OpenAI, DataForSEO, SMTP: create the new credential, update the secret file,
redeploy, then revoke the old credential at the provider.
