#!/usr/bin/env bash
# probe-endpoint.sh — check which non-chat endpoints a running vLLM exposes.
#
# Usage:  probe-endpoint.sh [URL]          (default http://localhost:8000)
# Env:    VLLM_API_KEY (or OPENAI_API_KEY) — sent as a Bearer token when set.
# Exit:   0  at least one non-chat endpoint (pooling or speech-to-text) is live
#         1  /health failed
#         2  no non-chat endpoint is registered (every route answered 404)
#         3  could not tell — some route answered 401/403, 5xx or not at all,
#            and none answered as live
#
# Each route gets a POST with an empty JSON body. 404 means the route is not
# registered. 401/403 (auth), 5xx (gateway or paused engine) and network
# errors say nothing about registration. Any other code (400, 405, 415, 422,
# 2xx) means the route exists and rejected or accepted the payload.

set -uo pipefail

URL="${1:-http://localhost:8000}"
URL="${URL%/}"
KEY="${VLLM_API_KEY:-${OPENAI_API_KEY:-}}"

if [[ -t 1 ]]; then
  GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[0;33m'; NC=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; NC=""
fi
OK()   { printf '  %s✓%s %s\n' "$GREEN" "$NC" "$1"; }
BAD()  { printf '  %s✗%s %s\n' "$RED" "$NC" "$1"; }
WARN() { printf '  %s~%s %s\n' "$YELLOW" "$NC" "$1"; }

AUTH=()
if [[ -n "$KEY" ]]; then
  AUTH=(-H "Authorization: Bearer $KEY")
fi

# /health check — bail early if the server is down
if ! curl -sf --max-time 10 "$URL/health" >/dev/null 2>&1; then
  BAD "$URL/health failed — server is not reachable/healthy"
  exit 1
fi
OK "$URL/health 200"

# Fetch served model name for nicer output
MODEL=$(curl -sf --max-time 10 "${AUTH[@]}" "$URL/v1/models" 2>/dev/null |
        python3 -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null) || MODEL="?"
printf '  Model: %s\n\n' "${MODEL:-?}"

# probe ROUTE LABEL — returns 0 live, 1 not registered, 2 indeterminate
probe() {
  local route="$1" label="$2" code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
              -X POST "$URL$route" "${AUTH[@]}" \
              -H "Content-Type: application/json" \
              -d '{}' 2>/dev/null) || code="000"
  case "$code" in
    404)
      BAD "$label  ($route)  — not registered"; return 1 ;;
    000)
      WARN "$label  ($route)  — no response (network error or timeout)"; return 2 ;;
    401|403)
      WARN "$label  ($route)  — HTTP $code, auth required: set VLLM_API_KEY"; return 2 ;;
    5??)
      WARN "$label  ($route)  — HTTP $code, cannot tell whether the route exists"; return 2 ;;
    *)
      OK "$label  ($route)  — HTTP $code"; return 0 ;;
  esac
}

LIVE=0
UNKNOWN=0
count() {
  probe "$1" "$2"
  case $? in
    0) LIVE=$((LIVE + 1)) ;;
    2) UNKNOWN=$((UNKNOWN + 1)) ;;
  esac
}

printf 'Pooling-runner endpoints:\n'
count "/v1/embeddings" "Embeddings (OpenAI v1)"
count "/v2/embed"      "Embeddings (Cohere v2)"
count "/rerank"        "Rerank"
count "/score"         "Score"

printf '\nGenerate-runner endpoints:\n'
count "/v1/audio/transcriptions" "Speech-to-text (ASR)"
count "/v1/audio/translations"   "Speech translation"
# Chat is reported but never counted: every generate server has it.
probe "/v1/chat/completions" "Chat completions (OCR = VLM + image)" || :

if (( LIVE > 0 )); then
  exit 0
fi
if (( UNKNOWN > 0 )); then
  printf '\n%sNote:%s %d route(s) gave no usable answer; nothing confirmed live.\n' \
    "$YELLOW" "$NC" "$UNKNOWN"
  exit 3
fi
printf '\n%sNote:%s server is up but no pooling or speech-to-text endpoint is registered.\n' \
  "$YELLOW" "$NC"
printf '  Pooling: restart with --runner pooling (plus --convert if needed).\n'
exit 2
