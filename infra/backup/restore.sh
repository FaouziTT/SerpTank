#!/usr/bin/env bash
# Restore a backup into a *scratch* database (monthly restore drill) or, with
# --into-production, into the live database after explicit confirmation.
#
#   AGE_IDENTITY=~/.age/serptank.key ./restore.sh s3:serptank-backups/prod/serptank-...dump.age
#
# Run on a trusted machine that holds the age private key and can reach the target DB.
set -euo pipefail

src="${1:?usage: restore.sh <remote-object> [--into-production]}"
mode="${2:-drill}"
: "${AGE_IDENTITY:?set AGE_IDENTITY to the age private key file}"
: "${RESTORE_DATABASE_URL:?set RESTORE_DATABASE_URL (postgres://owner@host/db)}"

if [ "$mode" = "--into-production" ]; then
  read -r -p "Type RESTORE to overwrite the production database: " answer
  [ "$answer" = "RESTORE" ] || { echo "aborted"; exit 1; }
fi

tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT
rclone copyto "$src" "$tmp/backup.dump.age"
age --decrypt --identity "$AGE_IDENTITY" --output "$tmp/backup.dump" "$tmp/backup.dump.age"

pg_restore --clean --if-exists --no-owner --exit-on-error \
  --dbname "$RESTORE_DATABASE_URL" "$tmp/backup.dump"

# Sanity checks for the drill log.
psql "$RESTORE_DATABASE_URL" -Atc "select 'organizations', count(*) from organizations
  union all select 'users', count(*) from users
  union all select 'alembic', version_num from alembic_version"
echo "restore finished ($mode)"
