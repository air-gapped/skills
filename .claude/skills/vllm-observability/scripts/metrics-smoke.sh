#!/usr/bin/env bash
#
# Smoke-check a vLLM /metrics endpoint. Confirms:
#   - /health responds
#   - /metrics responds and is Prometheus text format
#   - Load-bearing series are present (scheduler, KV, latency, outcomes)
#   - Deprecated / renamed names aren't silently empty
#   - Key histogram buckets exist
#   - DCGM exporter (if passed a second URL) exports pairing metrics
#
# Exit code: 0 on all-pass, 1 on any FAIL, 2 on WARN-but-usable.
#
# Usage:
#   metrics-smoke.sh <vllm-base-url> [dcgm-exporter-url]
#   metrics-smoke.sh http://vllm.svc.cluster.local:8000 http://dcgm-exporter:9400

set -euo pipefail

VLLM_URL="${1:?vLLM base URL required, e.g. http://localhost:8000}"
DCGM_URL="${2:-}"

# Colors
RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; BLD=$'\033[1m'; CLR=$'\033[0m'
pass() { printf "  %s[PASS]%s %s\n" "$GRN" "$CLR" "$1"; }
warn() { printf "  %s[WARN]%s %s\n" "$YLW" "$CLR" "$1"; WARN_COUNT=$((WARN_COUNT+1)); }
fail() { printf "  %s[FAIL]%s %s\n" "$RED" "$CLR" "$1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
WARN_COUNT=0; FAIL_COUNT=0

printf "%s=== vLLM observability smoke-check against %s ===%s\n" "$BLD" "$VLLM_URL" "$CLR"
echo

# 1. /health
printf "%s-- /health --%s\n" "$BLD" "$CLR"
if curl -fsS -m 5 "${VLLM_URL}/health" >/dev/null 2>&1; then
  pass "/health responds 200"
else
  fail "/health unreachable or returned non-2xx"
  echo
  printf "%sCannot proceed without a reachable /health. Aborting.%s\n" "$RED" "$CLR"
  exit 1
fi
echo

# 2. /metrics reachable + format
printf "%s-- /metrics format --%s\n" "$BLD" "$CLR"
METRICS="$(curl -fsS -m 10 "${VLLM_URL}/metrics" 2>/dev/null || true)"
if [ -z "$METRICS" ]; then
  fail "/metrics returned empty or failed"
  exit 1
fi
if printf '%s' "$METRICS" | head -5 | grep -qE '^# (HELP|TYPE) '; then
  pass "Prometheus text format detected"
else
  fail "/metrics did not start with # HELP/# TYPE lines"
fi
METRIC_COUNT="$(printf '%s' "$METRICS" | grep -cE '^vllm:' || true)"
printf "  -- emitted %d vllm:* series\n" "$METRIC_COUNT"
echo

# 3. Load-bearing series
printf "%s-- Load-bearing metrics --%s\n" "$BLD" "$CLR"

check_present() {
  local pattern="$1"
  local label="$2"
  if printf '%s' "$METRICS" | grep -qE "^${pattern}"; then
    pass "$label present"
  else
    fail "$label missing"
  fi
}

check_present 'vllm:num_requests_running' 'vllm:num_requests_running'
check_present 'vllm:num_requests_waiting' 'vllm:num_requests_waiting'
check_present 'vllm:num_preemptions_total' 'vllm:num_preemptions_total'

# KV cache — handle the rename saga
if printf '%s' "$METRICS" | grep -qE '^vllm:kv_cache_usage_perc'; then
  pass 'vllm:kv_cache_usage_perc present (V1 name)'
elif printf '%s' "$METRICS" | grep -qE '^vllm:gpu_cache_usage_perc'; then
  warn 'vllm:gpu_cache_usage_perc present (pre-rename name); consider upgrading dashboards'
else
  fail 'no KV cache usage metric present under either name'
fi

check_present 'vllm:prefix_cache_queries_total' 'vllm:prefix_cache_queries_total'
check_present 'vllm:prefix_cache_hits_total'    'vllm:prefix_cache_hits_total'
check_present 'vllm:prompt_tokens_total'        'vllm:prompt_tokens_total'
check_present 'vllm:generation_tokens_total'    'vllm:generation_tokens_total'
check_present 'vllm:request_success_total'      'vllm:request_success_total'

# Latency histograms — check for at least the `_bucket` series
check_present 'vllm:time_to_first_token_seconds_bucket{' 'vllm:time_to_first_token_seconds_bucket'
check_present 'vllm:inter_token_latency_seconds_bucket{' 'vllm:inter_token_latency_seconds_bucket'
check_present 'vllm:request_queue_time_seconds_bucket{'  'vllm:request_queue_time_seconds_bucket'
check_present 'vllm:e2e_request_latency_seconds_bucket{' 'vllm:e2e_request_latency_seconds_bucket'
echo

# 4. Deprecated / misleading metrics
printf "%s-- Deprecated / deceptive metrics --%s\n" "$BLD" "$CLR"

if printf '%s' "$METRICS" | grep -qE '^vllm:num_requests_swapped '; then
  warn 'vllm:num_requests_swapped present (deprecated on V1, always 0). Dashboards should use num_preemptions_total'
fi
if printf '%s' "$METRICS" | grep -qE '^vllm:cpu_cache_usage_perc '; then
  warn 'vllm:cpu_cache_usage_perc present (removed on V1). Indicates old engine or stale export'
fi
if printf '%s' "$METRICS" | grep -qE '^vllm:time_per_output_token_seconds_bucket{'; then
  warn 'vllm:time_per_output_token_seconds present (V0 name; V1 uses inter_token_latency_seconds + request_time_per_output_token_seconds)'
fi
echo

# 5. Labels sanity
printf "%s-- Labels sanity --%s\n" "$BLD" "$CLR"
MODEL_LABELS="$(printf '%s' "$METRICS" | grep -oE 'model_name="[^"]+"' | sort -u | head -5)"
if [ -n "$MODEL_LABELS" ]; then
  pass "model_name label present:"
  printf '%s\n' "$MODEL_LABELS" | sed 's/^/      /'
else
  warn 'no model_name label found on vllm:* series (DP/multi-model label collisions likely)'
fi
ENGINE_LABELS="$(printf '%s' "$METRICS" | grep -oE 'engine="[^"]+"' | sort -u | head -5)"
if [ -n "$ENGINE_LABELS" ]; then
  pass "engine label present: $(printf '%s' "$ENGINE_LABELS" | paste -sd ' ' -)"
fi
echo

# 6. Quick health snapshot
printf "%s-- Snapshot --%s\n" "$BLD" "$CLR"
printf '%s' "$METRICS" | awk '
  /^vllm:num_requests_running / { printf "  running  : %.0f\n", $NF }
  /^vllm:num_requests_waiting / { printf "  waiting  : %.0f\n", $NF }
  /^vllm:kv_cache_usage_perc / || /^vllm:gpu_cache_usage_perc / { printf "  kv_usage : %.2f\n", $NF }
  /^vllm:num_preemptions_total / { printf "  preempt  : %.0f (total since start)\n", $NF }
' | head -8
echo

# 7. DCGM pairing (optional)
if [ -n "$DCGM_URL" ]; then
  printf "%s-- DCGM exporter (%s) --%s\n" "$BLD" "$DCGM_URL" "$CLR"
  DCGM="$(curl -fsS -m 5 "${DCGM_URL}/metrics" 2>/dev/null || true)"
  if [ -z "$DCGM" ]; then
    fail "DCGM exporter unreachable"
  else
    for m in DCGM_FI_DEV_GPU_UTIL DCGM_FI_PROF_SM_OCCUPANCY DCGM_FI_DEV_FB_USED DCGM_FI_DEV_MEM_COPY_UTIL DCGM_FI_DEV_GPU_TEMP DCGM_FI_DEV_XID_ERRORS; do
      if printf '%s' "$DCGM" | grep -qE "^${m} "; then
        pass "$m present"
      else
        warn "$m missing from DCGM export"
      fi
    done
  fi
  echo
fi

# 8. Summary
printf "%s=== Summary ===%s\n" "$BLD" "$CLR"
printf "  PASSES: %d load-bearing metrics confirmed\n" "$((METRIC_COUNT))"
printf "  WARNS : %d\n" "$WARN_COUNT"
printf "  FAILS : %d\n" "$FAIL_COUNT"
echo
if [ "$FAIL_COUNT" -gt 0 ]; then
  printf "%sOverall: FAIL%s\n" "$RED" "$CLR"
  exit 1
elif [ "$WARN_COUNT" -gt 0 ]; then
  printf "%sOverall: PASS with warnings%s\n" "$YLW" "$CLR"
  exit 2
else
  printf "%sOverall: PASS%s\n" "$GRN" "$CLR"
  exit 0
fi
