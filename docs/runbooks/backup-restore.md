# Runbook: backups and the monthly restore drill

**What:** daily `pg_dump` (custom format) of the whole database, encrypted with `age` to
the team's public key, uploaded with `rclone` to S3-compatible storage with versioning and
object lock (set a retention of at least 35 days on the bucket). RPO: 24 hours.
The private key is kept offline by two people; the server cannot read its own backups.

**Monitoring:** `HEALTHCHECK_URL` is pinged after each successful upload; configure the
dead-man's switch to alert if no ping arrives for 26 hours.

## Monthly restore drill (record the result in the ops log)
1. On a trusted machine with the age identity and `pg_restore` 17:
   `rclone lsf s3:serptank-backups/prod | tail -3` -> pick the latest.
2. Start a scratch Postgres 17 + TimescaleDB container and create the three roles
   (`infra/postgres/init/02-roles.sh`).
3. `AGE_IDENTITY=... RESTORE_DATABASE_URL=postgres://serptank@localhost/scratch ./infra/backup/restore.sh <object>`
4. Check the printed counts look right and `alembic_version` matches production.
5. Point a local API at the scratch DB and sign in with a test account.
6. Destroy the scratch database and the decrypted files.

## Real restore (data loss)
Stop `api`, `worker`, `beat`; run `restore.sh <object> --into-production` against the
owner URL; start services; announce the recovery point to customers (data after the
backup time is lost). Rotate secrets if the incident involved compromise.

## Point-in-time recovery (next step)
For RPO < 24 h, enable WAL archiving with pgBackRest (shipped in the
`timescaledb-ha` image) to the same bucket. Not configured yet.
