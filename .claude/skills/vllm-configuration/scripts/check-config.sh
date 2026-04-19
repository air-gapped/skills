#!/usr/bin/env bash
#
# Verify the effective configuration of a running vLLM server.
# Dumps the resolved model id, prefix-caching / KV-cache state from Prometheus
# metrics, and the env vars most likely to affect behaviour.
#
# Usage: check-config.sh [BASE_URL]
#   BASE_URL: e.g. http://localhost:8000 (default)

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "=== vLLM configuration check against ${BASE_URL} ==="
echo

# 1. Is the server reachable?
if ! curl -fsS -m 3 "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "FAIL: cannot reach ${BASE_URL}/health"
  exit 1
fi
echo "OK: /health responds"
echo

# 2. Model id(s) actually loaded
echo "-- /v1/models --"
if curl -fsS "${BASE_URL}/v1/models" 2>/dev/null | jq -r '.data[] | "  id: \(.id)  owned_by: \(.owned_by // "?")"' 2>/dev/null; then
  :
else
  echo "  (no JSON response or auth required; try with OPENAI_API_KEY)"
fi
echo

# 3. Engine config signals from /metrics
echo "-- /metrics (config-relevant lines) --"
if curl -fsS "${BASE_URL}/metrics" 2>/dev/null | grep -E '^# HELP (vllm:gpu_cache|vllm:cpu_cache|vllm:num_gpu_blocks|vllm:num_cpu_blocks|vllm:prefix_cache|vllm:kv_cache)' | head -20; then
  :
else
  echo "  (no /metrics endpoint — either disabled or not reachable)"
fi
echo

# 4. Prefix cache actually on?
PREFIX_QUERIES="$(curl -fsS "${BASE_URL}/metrics" 2>/dev/null | grep -E '^vllm:prefix_cache_queries_total' | awk '{print $2}' | head -1 || true)"
if [ -n "${PREFIX_QUERIES:-}" ]; then
  echo "Prefix cache queries so far: ${PREFIX_QUERIES}"
else
  echo "Prefix cache metric not present — either disabled or very old vLLM"
fi
echo

# 5. Env vars on *this* host (not the server's host; useful when running alongside)
echo "-- Local VLLM_*/HF_*/TRANSFORMERS_* env (this shell) --"
env | grep -E '^(VLLM_|HF_|TRANSFORMERS_|HUGGINGFACE_|DO_NOT_TRACK)' | sort | sed 's/\(TOKEN=\|API_KEY=\).*/\1<redacted>/'
echo

# 6. Warn on the common footguns if we can detect them locally
if env | grep -q '^VLLM_SERVICE_HOST='; then
  echo "WARN: VLLM_SERVICE_HOST is set — this is usually k8s injecting a Service named 'vllm'."
  echo "      Rename the Service to avoid env var collisions."
fi
if env | grep -q '^TRANSFORMERS_CACHE='; then
  echo "WARN: TRANSFORMERS_CACHE is set (deprecated). Use HF_HOME instead."
fi
if [ "${HF_ENDPOINT:-}" != "" ]; then
  case "${HF_ENDPOINT}" in
    */) echo "WARN: HF_ENDPOINT ends with '/' which is known to break. Drop the trailing slash." ;;
  esac
fi

echo
echo "=== done ==="
