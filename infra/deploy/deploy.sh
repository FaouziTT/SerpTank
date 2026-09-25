#!/usr/bin/env bash
# Deploy a release on the VPS (called by the GitHub "deploy" workflow over SSH, or by hand).
#
#   ./deploy.sh v2026.09.25-1
#
# Pulls the tagged images, runs migrations as a one-shot job, rolls the services and
# health-checks the public site. On failure it rolls back to the previous release
# (images only - migrations must stay backward compatible for one release).
set -euo pipefail

release="${1:?usage: deploy.sh <release-tag>}"
cd "${SERPTANK_DIR:-/opt/serptank}"
[ -f config/deploy.env ] || { echo "missing config/deploy.env" >&2; exit 1; }
# Export for compose interpolation (SITE_DOMAIN, GHCR_OWNER, SMTP_*, ...).
set -a
# shellcheck disable=SC1091
. config/deploy.env
set +a
previous="$(cat config/current-release 2>/dev/null || true)"
compose() { RELEASE="$1" docker compose -f docker-compose.prod.yml "${@:2}"; }

echo "deploying $release (previous: ${previous:-none})"
compose "$release" pull --quiet
compose "$release" run --rm migrate
compose "$release" up -d --remove-orphans --wait --wait-timeout 180

healthy() {
  for _ in $(seq 1 30); do
    # Through Caddy: the web app and a public API route (compose --wait already
    # checked the containers' own healthchecks).
    if curl -fsS --max-time 5 "https://${SITE_DOMAIN}/login" >/dev/null 2>&1 \
      && curl -fsS --max-time 5 "https://${SITE_DOMAIN}/api/v1/public/config" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  return 1
}

if healthy; then
  echo "$release" > config/current-release
  docker image prune -f --filter "until=168h" >/dev/null
  echo "deployed $release"
else
  echo "health check failed" >&2
  if [ -n "$previous" ]; then
    echo "rolling back to $previous" >&2
    compose "$previous" up -d --remove-orphans --wait --wait-timeout 180
  fi
  exit 1
fi
