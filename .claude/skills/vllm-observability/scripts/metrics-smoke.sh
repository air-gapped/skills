#!/usr/bin/env bash
#
# Smoke-check a vLLM /metrics endpoint. Confirms:
#   - /health responds
#   - /metrics responds and is Prometheus text format
#   - Load-bearing series are present (scheduler, KV, latency, outcomes)
#   - Deprecated / removed names are not still being exported
#   - DCGM exporter (if passed a second URL) exports the pairing metrics
#
# Exit code: 0 on all-pass, 1 on any FAIL, 2 on WARN-but-usable.
#
# Usage:
#   metrics-smoke.sh <vllm-base-url> [dcgm-exporter-url]
#   metrics-smoke.sh http://vllm.svc.cluster.local:8000 http://dcgm-exporter:9400
#   metrics-smoke.sh --file <metrics.txt> [--dcgm-file <dcgm.txt>]   # saved scrapes, offline
#   metrics-smoke.sh --selfcheck    # planted cases; exit 0 = every check still fires

set -euo pipefail

SELF="${BASH_SOURCE[0]}"
TMP="$(mktemp -d -t metrics-smoke.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------- selfcheck
selfcheck() {
  local L='{model_name="m",engine="0"}' G='{gpu="0",modelName="H100"}' n bad=0
  good() {
    printf '# HELP vllm:num_requests_running h\n# TYPE vllm:num_requests_running gauge\n'
    for n in num_requests_running num_requests_waiting kv_cache_usage_perc num_preemptions_total \
             prefix_cache_queries_total prefix_cache_hits_total prompt_tokens_total generation_tokens_total; do
      [ "$n" = "${1:-}" ] || printf 'vllm:%s%s 0.0\n' "$n" "$L"
    done
    printf 'vllm:num_requests_waiting_by_reason{reason="capacity",model_name="m",engine="0"} 0.0\n'
    printf 'vllm:request_success_total{finished_reason="stop",model_name="m",engine="0"} 1.0\n'
    for n in time_to_first_token inter_token_latency request_queue_time e2e_request_latency; do
      [ "$n" = "${1:-}" ] || printf 'vllm:%s_seconds_bucket{le="+Inf",model_name="m",engine="0"} 1.0\n' "$n"
    done
  }
  good > "$TMP/ok"
  # A real endpoint is larger than a 64 KiB pipe buffer; the checks must not depend on size.
  { good; for n in $(seq 1 4000); do printf 'vllm:pad_bucket{le="%s",model_name="m",engine="0"} 1.0\n' "$n"; done; } > "$TMP/big"
  { good; printf 'vllm:num_requests_swapped%s 0.0\nvllm:cpu_cache_usage_perc%s 0.0\n' "$L" "$L"; } > "$TMP/deprecated"
  good num_requests_waiting > "$TMP/no_waiting"     # only the _by_reason sibling remains
  good time_to_first_token > "$TMP/no_ttft"
  printf '<html><body><h1>502 Bad Gateway</h1></body></html>\n' > "$TMP/html"
  printf '# HELP process_cpu_seconds_total h\n# TYPE process_cpu_seconds_total counter\nprocess_cpu_seconds_total 1.0\n' > "$TMP/other"
  for n in GPU_UTIL FB_USED MEM_COPY_UTIL GPU_TEMP XID_ERRORS; do printf 'DCGM_FI_DEV_%s%s 1\n' "$n" "$G"; done > "$TMP/dcgm_default"
  { cat "$TMP/dcgm_default"; printf 'DCGM_FI_PROF_SM_OCCUPANCY%s 0.4\n' "$G"; } > "$TMP/dcgm_old"
  for n in DEV_GPU_UTIL_RATIO DEV_FB_USED_BYTES DEV_MEMORY_UTIL_RATIO DEV_GPU_TEMP_CELSIUS DEV_XID_ERROR PROF_SM_OCCUPANCY_RATIO; do
    printf 'DCGM_FI_%s%s 1\n' "$n" "$G"
  done > "$TMP/dcgm_new"

  expect() { # <want-exit> <label> <args...>
    local want="$1" label="$2" rc=0; shift 2
    bash "$SELF" "$@" >/dev/null 2>&1 || rc=$?
    if [ "$rc" = "$want" ]; then printf '  ok       %-34s exit %s\n' "$label" "$rc"
    else printf '  MISMATCH %-34s exit %s, want %s\n' "$label" "$rc" "$want"; bad=1; fi
  }
  expect 0 "healthy endpoint"                 --file "$TMP/ok"
  expect 0 "healthy endpoint > 64 KiB"        --file "$TMP/big"
  expect 2 "deprecated names exported"        --file "$TMP/deprecated"
  expect 1 "num_requests_waiting missing"     --file "$TMP/no_waiting"
  expect 1 "TTFT histogram missing"           --file "$TMP/no_ttft"
  expect 1 "HTML error page"                  --file "$TMP/html"
  expect 1 "Prometheus text, no vllm: series" --file "$TMP/other"
  expect 0 "DCGM names, exporter <= 4.8.4"    --file "$TMP/ok" --dcgm-file "$TMP/dcgm_old"
  expect 0 "DCGM names, exporter 4.9.0+"      --file "$TMP/ok" --dcgm-file "$TMP/dcgm_new"
  expect 2 "DCGM default CSV (no SM occupancy)" --file "$TMP/ok" --dcgm-file "$TMP/dcgm_default"
  expect 1 "DCGM target returns HTML"         --file "$TMP/ok" --dcgm-file "$TMP/html"
  if [ "$bad" != 0 ]; then echo "selfcheck: FAIL"; exit 1; fi
  echo "selfcheck: PASS"
  exit 0
}

# ---------------------------------------------------------------- arguments
VLLM_URL=""; DCGM_URL=""; METRICS_FILE=""; DCGM_FILE=""
case "${1:-}" in
  --selfcheck) selfcheck ;;
  --file)
    METRICS_FILE="${2:?--file needs a path}"
    if [ "${3:-}" = "--dcgm-file" ]; then DCGM_FILE="${4:?--dcgm-file needs a path}"; fi
    ;;
  *)
    VLLM_URL="${1:?vLLM base URL required, e.g. http://localhost:8000}"
    DCGM_URL="${2:-}"
    ;;
esac

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; BLD=$'\033[1m'; CLR=$'\033[0m'
PASS_COUNT=0; WARN_COUNT=0; FAIL_COUNT=0
pass() { printf "  %s[PASS]%s %s\n" "$GRN" "$CLR" "$1"; PASS_COUNT=$((PASS_COUNT+1)); }
warn() { printf "  %s[WARN]%s %s\n" "$YLW" "$CLR" "$1"; WARN_COUNT=$((WARN_COUNT+1)); }
fail() { printf "  %s[FAIL]%s %s\n" "$RED" "$CLR" "$1"; FAIL_COUNT=$((FAIL_COUNT+1)); }

# Exact-name match on a saved scrape. A series line is `name{labels} value` or
# `name value`, so the name must be followed by `{` or a space — a bare prefix
# match would accept `num_requests_waiting_by_reason` for `num_requests_waiting`.
# Greps read the file directly: piping a large scrape into `grep -q` under
# pipefail reports a match as a failure once the scrape exceeds the pipe buffer.
has_series() { grep -qE "^$1(\{| )" "$2"; }

printf "%s=== vLLM observability smoke-check against %s ===%s\n" "$BLD" "${VLLM_URL:-$METRICS_FILE}" "$CLR"
echo

# 1. /health and /metrics
M="$TMP/metrics"
if [ -n "$METRICS_FILE" ]; then
  [ -r "$METRICS_FILE" ] || { fail "cannot read $METRICS_FILE"; exit 1; }
  cp "$METRICS_FILE" "$M"
else
  printf "%s-- /health --%s\n" "$BLD" "$CLR"
  if curl -fsS -m 5 "${VLLM_URL}/health" >/dev/null 2>&1; then
    pass "/health responds 200"
  else
    fail "/health unreachable or returned non-2xx"
    printf "%sCannot proceed without a reachable /health. Aborting.%s\n" "$RED" "$CLR"
    exit 1
  fi
  echo
  if ! curl -fsS -m 10 -o "$M" "${VLLM_URL}/metrics" 2>/dev/null; then
    fail "/metrics unreachable or returned non-2xx"
    exit 1
  fi
fi

printf "%s-- /metrics format --%s\n" "$BLD" "$CLR"
if [ ! -s "$M" ]; then
  fail "/metrics returned an empty body"
  exit 1
fi
if grep -qE '^# (HELP|TYPE) ' "$M"; then
  pass "Prometheus text format detected"
else
  fail "/metrics has no # HELP / # TYPE lines (error page or wrong target?)"
fi
SERIES_COUNT="$(grep -cE '^vllm:' "$M" || true)"
printf "  -- %d vllm:* sample lines\n" "$SERIES_COUNT"
echo

# 2. Load-bearing series
printf "%s-- Load-bearing metrics --%s\n" "$BLD" "$CLR"
check_present() {
  if has_series "$1" "$M"; then pass "$1 present"; else fail "$1 missing"; fi
}

check_present 'vllm:num_requests_running'
check_present 'vllm:num_requests_waiting'
check_present 'vllm:num_preemptions_total'

if has_series 'vllm:kv_cache_usage_perc' "$M"; then
  pass 'vllm:kv_cache_usage_perc present'
elif has_series 'vllm:gpu_cache_usage_perc' "$M"; then
  warn 'only vllm:gpu_cache_usage_perc present (engine <= v0.11.x); the name is gone from v0.12.0'
else
  fail 'no KV cache usage metric present under either name'
fi

check_present 'vllm:prefix_cache_queries_total'
check_present 'vllm:prefix_cache_hits_total'
check_present 'vllm:prompt_tokens_total'
check_present 'vllm:generation_tokens_total'
check_present 'vllm:request_success_total'
check_present 'vllm:time_to_first_token_seconds_bucket'
check_present 'vllm:inter_token_latency_seconds_bucket'
check_present 'vllm:request_queue_time_seconds_bucket'
check_present 'vllm:e2e_request_latency_seconds_bucket'
echo

# 3. Deprecated / removed names still being exported
printf "%s-- Deprecated metrics --%s\n" "$BLD" "$CLR"
if has_series 'vllm:num_requests_swapped' "$M"; then
  warn 'vllm:num_requests_swapped present (deprecated on V1, always 0). Dashboards should use num_preemptions_total'
fi
if has_series 'vllm:cpu_cache_usage_perc' "$M"; then
  warn 'vllm:cpu_cache_usage_perc present (removed on V1). Indicates old engine or stale export'
fi
if has_series 'vllm:time_per_output_token_seconds_bucket' "$M"; then
  warn 'vllm:time_per_output_token_seconds present (V0 name; V1 uses inter_token_latency_seconds + request_time_per_output_token_seconds)'
fi
echo

# 4. Labels sanity
printf "%s-- Labels sanity --%s\n" "$BLD" "$CLR"
MODEL_LABELS="$(grep -oE 'model_name="[^"]+"' "$M" | sort -u | sed -n '1,5p' || true)"
if [ -n "$MODEL_LABELS" ]; then
  pass "model_name label present:"
  printf '%s\n' "$MODEL_LABELS" | sed 's/^/      /'
else
  warn 'no model_name label found on vllm:* series'
fi
ENGINE_LABELS="$(grep -oE 'engine="[^"]+"' "$M" | sort -u | sed -n '1,5p' | paste -sd ' ' - || true)"
[ -z "$ENGINE_LABELS" ] || pass "engine label present: $ENGINE_LABELS"
echo

# 5. Snapshot (gauges summed across engines, KV usage as the max)
printf "%s-- Snapshot --%s\n" "$BLD" "$CLR"
awk '
  { name = $1; sub(/\{.*/, "", name) }
  name == "vllm:num_requests_running"  { run += $NF; r = 1 }
  name == "vllm:num_requests_waiting"  { wait += $NF; w = 1 }
  name == "vllm:num_preemptions_total" { pre += $NF; p = 1 }
  name == "vllm:kv_cache_usage_perc" || name == "vllm:gpu_cache_usage_perc" { if ($NF > kv) kv = $NF; k = 1 }
  END {
    if (r) printf "  running  : %.0f\n", run
    if (w) printf "  waiting  : %.0f\n", wait
    if (k) printf "  kv_usage : %.2f (max across engines)\n", kv
    if (p) printf "  preempt  : %.0f (total since start)\n", pre
  }
' "$M"
echo

# 6. DCGM pairing (optional). Exporter 4.9.0 renamed its default metrics, so
#    each field is accepted under either name: "<= 4.8.4 name:4.9.0+ name".
if [ -n "$DCGM_URL" ] || [ -n "$DCGM_FILE" ]; then
  printf "%s-- DCGM exporter (%s) --%s\n" "$BLD" "${DCGM_URL:-$DCGM_FILE}" "$CLR"
  D="$TMP/dcgm"
  if [ -n "$DCGM_FILE" ]; then
    cp "$DCGM_FILE" "$D" 2>/dev/null || : > "$D"
  else
    curl -fsS -m 5 -o "$D" "${DCGM_URL}/metrics" 2>/dev/null || : > "$D"
  fi
  if [ ! -s "$D" ]; then
    fail "DCGM exporter unreachable or empty"
  elif ! grep -qE '^DCGM_' "$D"; then
    fail "DCGM target returned no DCGM_* series (error page or wrong target?)"
  else
    for pair in \
      'DCGM_FI_DEV_GPU_UTIL:DCGM_FI_DEV_GPU_UTIL_RATIO' \
      'DCGM_FI_PROF_SM_OCCUPANCY:DCGM_FI_PROF_SM_OCCUPANCY_RATIO' \
      'DCGM_FI_DEV_FB_USED:DCGM_FI_DEV_FB_USED_BYTES' \
      'DCGM_FI_DEV_MEM_COPY_UTIL:DCGM_FI_DEV_MEMORY_UTIL_RATIO' \
      'DCGM_FI_DEV_GPU_TEMP:DCGM_FI_DEV_GPU_TEMP_CELSIUS' \
      'DCGM_FI_DEV_XID_ERRORS:DCGM_FI_DEV_XID_ERROR'; do
      old="${pair%%:*}"; new="${pair##*:}"
      if has_series "$old" "$D"; then
        pass "$old present"
      elif has_series "$new" "$D"; then
        pass "$new present (exporter 4.9.0+ name)"
      elif [ "$old" = "DCGM_FI_PROF_SM_OCCUPANCY" ]; then
        warn "$old / $new missing — opt-in field, enable it in the exporter's counters CSV"
      else
        warn "$old / $new missing from DCGM export"
      fi
    done
  fi
  echo
fi

# 7. Summary
printf "%s=== Summary ===%s\n" "$BLD" "$CLR"
printf "  PASSES: %d\n" "$PASS_COUNT"
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
