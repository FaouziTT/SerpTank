#!/usr/bin/env bash
# Encrypted, off-site PostgreSQL backup (run daily by serptank-backup.timer).
#
#   pg_dump (custom format) -> age (public-key encryption) -> rclone (S3-compatible,
#   bucket with object lock / versioning) ; then prune local temp and verify listing.
#
# Requires on the host: docker, age, rclone (configured remote named in BACKUP_REMOTE).
# The age *private* key is NOT on the server; restores happen with it on a trusted box.
set -euo pipefail

: "${SERPTANK_DIR:=/opt/serptank}"
: "${AGE_RECIPIENT:?set AGE_RECIPIENT (age public key)}"
: "${BACKUP_REMOTE:?set BACKUP_REMOTE, e.g. s3:serptank-backups/prod}"
: "${HEALTHCHECK_URL:=}"  # optional dead-man's-switch URL pinged on success

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
name="serptank-${stamp}.dump.age"
tmp="$(mktemp -d)"
trap 'rm -rf -- "${tmp:?}"' EXIT

cd "$SERPTANK_DIR"
# Compose needs the deployment variables to interpolate the file.
set -a
# shellcheck disable=SC1091
. config/deploy.env
RELEASE="$(cat config/current-release)"
export RELEASE
set +a
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump --format=custom --no-owner --username=serptank serptank \
  | age --encrypt --recipient "$AGE_RECIPIENT" --output "$tmp/$name"

# Refuse to upload an obviously broken dump.
size="$(stat -c %s "$tmp/$name")"
if [ "$size" -lt 1024 ]; then
  echo "backup too small ($size bytes); aborting" >&2
  exit 1
fi

rclone copyto "$tmp/$name" "$BACKUP_REMOTE/$name" --s3-no-check-bucket
rclone lsf "$BACKUP_REMOTE/$name" >/dev/null   # verify it landed
echo "uploaded $name ($size bytes)"

if [ -n "$HEALTHCHECK_URL" ]; then
  curl -fsS --max-time 10 "$HEALTHCHECK_URL" >/dev/null || true
fi
