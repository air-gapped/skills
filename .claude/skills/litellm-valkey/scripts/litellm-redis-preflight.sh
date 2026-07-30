#!/usr/bin/env bash
# litellm-redis-preflight.sh — is this LiteLLM proxy actually coordinating through Redis?
#
# Usage: litellm-redis-preflight.sh <base-url> <admin-key>
#   e.g. litellm-redis-preflight.sh http://localhost:4000 sk-master-...
#
# Checks (admin key required; endpoints are undocumented but stable since v1.93.0):
#   1. GET  /coordination_redis/settings       -> which of the 4 sources won (null = PER-POD MODE)
#   2. POST /coordination_redis/settings/test  -> live ping through the real client-build path
#   3. GET  /cache/ping                        -> response cache health (independent of coordination)
#
# Exit codes: 0 = coordinating and healthy, 1 = usage error, 2 = per-pod mode, 3 = unhealthy.

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "usage: $0 <base-url> <admin-key>" >&2
  exit 1
fi
BASE="${1%/}"
KEY="$2"

command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }

auth=(-H "Authorization: Bearer ${KEY}")

BODY="" STATUS="" CTYPE=""
do_fetch() { # method path [json-body] -> sets BODY, STATUS, CTYPE (no subshell: globals survive)
  local method="$1" path="$2" data="${3:-}" resp
  local args=(-sS -w $'\n%{http_code}\t%{content_type}' -X "$method" "${auth[@]}")
  [ -n "$data" ] && args+=(-H "Content-Type: application/json" -d "$data")
  resp="$(curl "${args[@]}" "${BASE}${path}")"
  STATUS="$(printf '%s\n' "$resp" | tail -1 | cut -f1)"
  CTYPE="$(printf '%s\n' "$resp" | tail -1 | cut -f2)"
  BODY="$(printf '%s\n' "$resp" | sed '$d')"
}

echo "== 1. Coordination source (${BASE}/coordination_redis/settings)"
do_fetch GET /coordination_redis/settings
if [ "$STATUS" != "200" ]; then
  echo "   HTTP ${STATUS} — pre-v1.93.0 proxy (endpoint missing), non-admin key, or lazy-load failure" >&2
  echo "   On <v1.93.0 there is no dedicated coordination config: coordination borrows the" >&2
  echo "   response-cache Redis (cache: true) or is per-pod. See references/coordination-redis.md" >&2
  exit 2
fi
if ! printf '%s' "$BODY" | jq -e . >/dev/null 2>&1; then
  echo "   Non-JSON response (content-type: ${CTYPE}) — wrong base URL?" >&2
  exit 1
fi
source_val="$(printf '%s' "$BODY" | jq -r '.source // empty')"
printf '%s' "$BODY" | jq '{source, values}'
if [ -z "$source_val" ] || [ "$source_val" = "null" ]; then
  echo
  echo "   *** NO COORDINATION SOURCE — this fleet enforces rate limits and budgets PER POD. ***"
  echo "   Fix: set general_settings.coordination_redis (v1.93.0+), or cache: true with a"
  echo "   plain-Redis cache_params, or REDIS_* env WITH cache: true. See the skill's SKILL.md."
  exit 2
fi
case "$source_val" in
  coordination_redis) echo "   source=coordination_redis (explicit block — check it isn't a DB/UI copy shadowing the config file)";;
  cache_backend)      echo "   source=cache_backend (borrowed response-cache client — cache failures couple into rate limiting via the shared circuit breaker)";;
  environment)        echo "   source=environment (REDIS_* env fallback)";;
  *)                  echo "   source=${source_val}";;
esac

echo
echo "== 2. Coordination live ping (${BASE}/coordination_redis/settings/test)"
do_fetch POST /coordination_redis/settings/test '{"settings": {}}'
if [ "$STATUS" = "200" ]; then
  printf '%s' "$BODY" | jq .
  health="$(printf '%s' "$BODY" | jq -r '.status // empty')"
  [ "$health" = "healthy" ] || { echo "   *** coordination Redis UNHEALTHY ***"; exit 3; }
else
  echo "   HTTP ${STATUS}: $(printf '%s' "$BODY" | head -c 300)"
fi

echo
echo "== 3. Response cache ping (${BASE}/cache/ping) — independent of coordination"
do_fetch GET /cache/ping
if [ "$STATUS" = "200" ]; then
  printf '%s' "$BODY" | jq '{status: (.status // .cache_type // "ok")}' 2>/dev/null || printf '%.300s\n' "$BODY"
else
  echo "   HTTP ${STATUS} (no response cache configured is fine — coordination is separate)"
fi

echo
echo "Preflight passed: coordination source='${source_val}', ping healthy."
echo "Remember: this proves wiring, not enforcement. Run the 429 canary (drive one key past its"
echo "RPM limit across ALL pods; onset must be ~1x the limit, not ~Nx) after failovers/upgrades."
