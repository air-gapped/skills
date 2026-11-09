#!/usr/bin/env bash
#
# Verify the effective configuration of a running vLLM server.
# Prints the loaded model ids, the CacheConfig the engine resolved (from the
# vllm:cache_config_info gauge), prefix-cache counters, and the env vars in
# this shell that change vLLM behaviour, then flags the known footguns.
#
# Usage: check-config.sh [BASE_URL]      (default http://localhost:8000)
#   Sends "Authorization: Bearer $VLLM_API_KEY" (else $OPENAI_API_KEY) if set.
# Exit:  0 clean · 1 a check failed · 2 warnings only
# Test:  scripts/test-check-config.sh

set -uo pipefail

BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"
KEY="${VLLM_API_KEY:-${OPENAI_API_KEY:-}}"
AUTH=()
if [ -n "$KEY" ]; then AUTH=(-H "Authorization: Bearer ${KEY}"); fi

fails=0
warns=0
fail() { echo "FAIL: $*"; fails=$((fails + 1)); }
warn() { echo "WARN: $*"; warns=$((warns + 1)); }

echo "=== vLLM configuration check against ${BASE_URL} ==="
echo

# 1. Reachable? Nothing below means anything if not.
if ! curl -fsS -m 5 "${BASE_URL}/health" >/dev/null 2>&1; then
  fail "cannot reach ${BASE_URL}/health"
  exit 1
fi
echo "OK: /health responds"
echo

# 2. Model id(s) actually loaded. /v1 is behind --api-key.
echo "-- /v1/models --"
resp="$(curl -sS -m 10 -w '\n%{http_code}' ${AUTH[@]+"${AUTH[@]}"} "${BASE_URL}/v1/models" 2>&1)"
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
if [ "$code" = "401" ] || [ "$code" = "403" ]; then
  fail "/v1/models returned ${code} — the server requires an API key; export VLLM_API_KEY and re-run"
elif [ "$code" != "200" ]; then
  fail "/v1/models returned HTTP ${code}"
elif ! command -v jq >/dev/null 2>&1; then
  fail "jq not installed — cannot parse /v1/models"
elif ! ids="$(printf '%s' "$body" | jq -er '.data[] | "  id: \(.id)  owned_by: \(.owned_by // "?")"' 2>/dev/null)"; then
  fail "/v1/models returned 200 but no model entries (empty list, or a proxy error page instead of JSON)"
else
  echo "$ids"
fi
echo

# 3. Resolved CacheConfig, one label per line. /metrics is not behind --api-key.
echo "-- /metrics: vllm:cache_config_info --"
metrics="$(curl -fsS -m 10 "${BASE_URL}/metrics" 2>/dev/null || true)"
if ! printf '%s\n' "$metrics" | grep -q '^vllm:'; then
  warn "/metrics has no vllm: series — endpoint blocked by a proxy, or this is not a vLLM server"
else
  cfg="$(printf '%s\n' "$metrics" | grep '^vllm:cache_config_info' | head -1 || true)"
  if [ -n "$cfg" ]; then
    printf '%s\n' "$cfg" | sed -e 's/^[^{]*{//' -e 's/}[^}]*$//' | tr ',' '\n' | sed 's/^/  /'
  else
    echo "  (not exported — the Rust frontend omits it through v0.33.0;"
    echo "   read 'non-default args:' and 'with config:' in the startup log instead)"
  fi
  echo
  echo "-- /metrics: prefix cache --"
  pc="$(printf '%s\n' "$metrics" | grep -E '^vllm:prefix_cache_(queries|hits)_total' || true)"
  if [ -n "$pc" ]; then
    printf '%s\n' "$pc" | sed 's/^/  /'
  else
    echo "  (no prefix-cache counters yet — no request served, or prefix caching is off)"
  fi
fi
echo

# 4. Env vars in *this* shell — the server's own only when run inside its pod
#    (kubectl exec <pod> -- check-config.sh).
echo "-- VLLM_*/HF_*/TRANSFORMERS_* env (this shell) --"
vars="$(env | grep -E '^(VLLM_|HF_|TRANSFORMERS_|HUGGINGFACE_|HUGGING_FACE_|DO_NOT_TRACK=)' | sort || true)"
if [ -n "$vars" ]; then
  printf '%s\n' "$vars" | sed -E 's/^([A-Z_]*(TOKEN|API_KEY)=).*/\1<redacted>/'
else
  echo "  (none set)"
fi
echo

# 5. Footguns detectable from the environment.
case "${VLLM_PORT:-}" in
  *://*) warn "VLLM_PORT='${VLLM_PORT}' is a URI — a Kubernetes Service named 'vllm' injected it; vLLM fails at startup. Rename the Service or set enableServiceLinks: false." ;;
esac
if [ -n "${VLLM_SERVICE_HOST:-}" ]; then
  warn "VLLM_SERVICE_HOST is set — Kubernetes service links from a Service named 'vllm' are active in this pod."
fi
if [ -n "${TRANSFORMERS_CACHE:-}" ]; then
  warn "TRANSFORMERS_CACHE is set (deprecated). Use HF_HOME instead."
fi
case "${HF_ENDPOINT:-}" in
  */) warn "HF_ENDPOINT ends with '/' — drop the trailing slash." ;;
esac
for v in VLLM_NO_USAGE_STATS VLLM_DO_NOT_TRACK DO_NOT_TRACK; do
  val="${!v:-}"
  if [ -n "$val" ] && [ "$val" != "1" ] && [ "$val" != "0" ]; then
    warn "${v}='${val}' is ignored — only the literal 1 disables usage stats."
  fi
done
# Boolean words on any other VLLM_* var: ignored by some parsers, fatal for others.
while IFS='=' read -r name val; do
  case "$name" in
    VLLM_USE_MODELSCOPE | VLLM_ALLOW_LONG_MAX_MODEL_LEN | VLLM_ALLOW_RUNTIME_LORA_UPDATING) continue ;;
    VLLM_NO_USAGE_STATS | VLLM_DO_NOT_TRACK) continue ;;
  esac
  case "$val" in
    [Tt]rue | TRUE | [Ff]alse | FALSE | [Yy]es | [Nn]o | [Oo]n | [Oo]ff)
      warn "${name}='${val}' — write 1 or 0; boolean words are ignored or raise ValueError depending on the variable."
      ;;
  esac
done < <(env | grep '^VLLM_' || true)

echo
echo "=== done: ${fails} failed, ${warns} warning(s) ==="
if [ "$fails" -gt 0 ]; then exit 1; fi
if [ "$warns" -gt 0 ]; then exit 2; fi
exit 0
