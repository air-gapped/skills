#!/usr/bin/env bash
# probe-endpoint.sh — check which non-chat endpoints a running vLLM exposes.
#
# Usage:  probe-endpoint.sh [URL]          (default http://localhost:8000)
# Exit:   0 if healthy, 1 if /health fails, 2 if no non-chat endpoint is live.
#
# Uses a POST with a minimal/invalid body to each route and classifies the
# response code. 404 / "Not Found" => route isn't registered. 405 / 422 /
# anything else => route is there; the model just rejected the payload.

set -euo pipefail

URL="${1:-http://localhost:8000}"
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'
OK() { printf "  ${GREEN}✓${NC} %s\n" "$1"; }
BAD() { printf "  ${RED}✗${NC} %s\n" "$1"; }
WARN() { printf "  ${YELLOW}~${NC} %s\n" "$1"; }

# /health check — bail early if the server is down
if ! curl -sf "$URL/health" >/dev/null 2>&1; then
  BAD "$URL/health failed — server is not reachable/healthy"
  exit 1
fi
OK "$URL/health 200"

# Fetch served model name for nicer output
MODEL=$(curl -sf "$URL/v1/models" 2>/dev/null | \
        python -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null || echo "?")
printf "  Model: %s\n\n" "$MODEL"

# Each route gets a POST with a tiny invalid body — we only care whether the
# route is registered, not whether the call succeeds.
probe() {
  local route="$1" label="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" \
              -X POST "$URL$route" \
              -H "Content-Type: application/json" \
              -d '{}' 2>/dev/null || echo "000")
  if [[ "$code" == "404" ]]; then
    BAD "$label  ($route)  — not registered"
  elif [[ "$code" == "000" ]]; then
    BAD "$label  ($route)  — network error"
  else
    OK  "$label  ($route)  — HTTP $code"
  fi
}

LIVE=0
printf "Pooling-runner endpoints:\n"
probe "/v1/embeddings"  "Embeddings (OpenAI v1)" && LIVE=$((LIVE+1)) || :
probe "/v2/embed"       "Embeddings (Cohere v2) " && LIVE=$((LIVE+1)) || :
probe "/rerank"         "Rerank                 " && LIVE=$((LIVE+1)) || :
probe "/score"          "Score                  " && LIVE=$((LIVE+1)) || :

printf "\nGenerate-runner endpoints:\n"
probe "/v1/audio/transcriptions" "Speech-to-text (ASR)   "
probe "/v1/audio/translations"   "Speech translation     "
probe "/v1/chat/completions"     "Chat completions (OCR = VLM + image)"

# Exit 2 if no pooling/non-chat endpoint is live beyond the default
# /v1/chat/completions — useful as a smoke test in CI.
if [[ "$LIVE" == "0" ]]; then
  printf "\n${YELLOW}Note:${NC} server is up but no pooling endpoints are live.\n"
  printf "  To enable: restart with --runner pooling (plus --convert if needed).\n"
  exit 2
fi
exit 0
