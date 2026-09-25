#!/bin/sh
# Creates the database roles used by SerpTank (runs once on a fresh dev volume).
#
#   serptank_app     NOLOGIN group role, subject to Row-Level Security
#   serptank_system  NOLOGIN group role with BYPASSRLS (schedulers/maintenance only)
#   serptank_api     LOGIN role for the API and workers   (member of serptank_app)
#   serptank_sched   LOGIN role for cross-tenant schedulers (member of serptank_system)
#
# In production the same roles are created by the M14 provisioning script with
# secrets from sops; the schema owner (POSTGRES_USER) only runs migrations.
set -eu
# Production passes Docker secrets as *_FILE paths; read them when present.
if [ -n "${POSTGRES_APP_PASSWORD_FILE:-}" ]; then POSTGRES_APP_PASSWORD="$(cat "$POSTGRES_APP_PASSWORD_FILE")"; fi
if [ -n "${POSTGRES_SCHED_PASSWORD_FILE:-}" ]; then POSTGRES_SCHED_PASSWORD="$(cat "$POSTGRES_SCHED_PASSWORD_FILE")"; fi
: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD must be set}"
: "${POSTGRES_SCHED_PASSWORD:?POSTGRES_SCHED_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_pw="$POSTGRES_APP_PASSWORD" -v sched_pw="$POSTGRES_SCHED_PASSWORD" <<'SQL'
CREATE ROLE serptank_app NOLOGIN;
CREATE ROLE serptank_system NOLOGIN BYPASSRLS;
CREATE ROLE serptank_api LOGIN PASSWORD :'app_pw' IN ROLE serptank_app;
CREATE ROLE serptank_sched LOGIN PASSWORD :'sched_pw' IN ROLE serptank_system;
SQL
