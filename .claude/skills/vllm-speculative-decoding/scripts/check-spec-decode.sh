#!/usr/bin/env bash
#
# Smoke-check a vLLM /metrics endpoint for speculative-decoding health.
# Confirms:
#   - /health responds
#   - /metrics emits the four canonical vllm:spec_decode_* series
#   - Current acceptance rate, mean acceptance length, per-position rates
#   - No silent-disable: num_drafts_total should be nonzero if configured
#
# Exit: 0 all-good, 1 metrics missing / endpoint broken, 2 metrics present
# but spec-dec appears inactive (warnings).
#
# Usage:
#   check-spec-decode.sh <vllm-base-url>
#   check-spec-decode.sh http://vllm.svc.cluster.local:8000

set -euo pipefail

URL="${1:?vLLM base URL required, e.g. http://localhost:8000}"

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; BLD=$'\033[1m'; CLR=$'\033[0m'
pass() { printf "  %s[PASS]%s %s\n" "$GRN" "$CLR" "$1"; }
warn() { printf "  %s[WARN]%s %s\n" "$YLW" "$CLR" "$1"; WARN_COUNT=$((WARN_COUNT+1)); }
fail() { printf "  %s[FAIL]%s %s\n" "$RED" "$CLR" "$1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
WARN_COUNT=0; FAIL_COUNT=0

printf "%s=== vLLM spec-dec smoke-check against %s ===%s\n\n" "$BLD" "$URL" "$CLR"

# 1. /health
printf "%s-- /health --%s\n" "$BLD" "$CLR"
if curl -fsS -m 5 "${URL}/health" >/dev/null 2>&1; then
  pass "/health responds"
else
  fail "/health unreachable — aborting"
  exit 1
fi
printf "\n"

# 2. /metrics reachable
printf "%s-- /metrics --%s\n" "$BLD" "$CLR"
METRICS="$(curl -fsS -m 10 "${URL}/metrics" 2>/dev/null || true)"
if [ -z "$METRICS" ]; then
  fail "/metrics empty or failed"
  exit 1
fi
pass "/metrics responds ($(printf '%s' "$METRICS" | grep -cE '^vllm:' || true) vllm:* series)"
printf "\n"

# 3. Spec-dec series presence
printf "%s-- Spec-decode metric surface --%s\n" "$BLD" "$CLR"
check() {
  local name="$1"
  if printf '%s' "$METRICS" | grep -qE "^${name}"; then
    pass "$name present"
    return 0
  else
    fail "$name missing"
    return 1
  fi
}

SD_OK=1
check 'vllm:spec_decode_num_drafts_total'                   || SD_OK=0
check 'vllm:spec_decode_num_draft_tokens_total'             || SD_OK=0
check 'vllm:spec_decode_num_accepted_tokens_total'          || SD_OK=0
check 'vllm:spec_decode_num_accepted_tokens_per_pos_total'  || SD_OK=0
printf "\n"

if [ "$SD_OK" = 0 ]; then
  printf "%sSpec-dec metrics missing — is --speculative-config set?%s\n" "$YLW" "$CLR"
  printf "%sCheck engine start log for 'SpeculativeConfig(...)' line.%s\n" "$YLW" "$CLR"
  exit 1
fi

# 4. Extract counters and compute AL
printf "%s-- Current acceptance snapshot --%s\n" "$BLD" "$CLR"

val() {
  # Sum all series values for a given metric name (ignore labels, engine_idx etc)
  printf '%s' "$METRICS" \
    | awk -v m="$1" '$0 ~ "^"m"[ {]" { gsub(/.*[[:space:]]/, "", $0); sum+=$NF } END { print sum+0 }'
}

NUM_DRAFTS=$(val 'vllm:spec_decode_num_drafts_total')
NUM_DRAFT_TOK=$(val 'vllm:spec_decode_num_draft_tokens_total')
NUM_ACC_TOK=$(val 'vllm:spec_decode_num_accepted_tokens_total')

printf "  %-44s %12.0f\n" "num_drafts_total"           "$NUM_DRAFTS"
printf "  %-44s %12.0f\n" "num_draft_tokens_total"     "$NUM_DRAFT_TOK"
printf "  %-44s %12.0f\n" "num_accepted_tokens_total"  "$NUM_ACC_TOK"

if [ "$(printf '%.0f' "$NUM_DRAFTS")" = "0" ]; then
  warn "num_drafts_total is 0 — spec-dec configured but never invoked."
  warn "Possible causes: engine fallback on validation error, no traffic yet,"
  warn "or method detection failed. Send a request, then re-run."
else
  # Acceptance rate = accepted / drafted_tokens
  if [ "$(printf '%.0f' "$NUM_DRAFT_TOK")" != "0" ]; then
    ACC_RATE=$(awk -v a="$NUM_ACC_TOK" -v b="$NUM_DRAFT_TOK" 'BEGIN{printf "%.3f", a/b}')
    printf "  %-44s %12s\n" "acceptance_rate (accepted / drafted)" "$ACC_RATE"
    if awk -v r="$ACC_RATE" 'BEGIN{exit !(r < 0.50)}'; then
      warn "acceptance < 0.50 — drafter divergence / tokenizer / temp drift. See troubleshooting.md §1."
    fi
  fi
  # Mean AL = 1 + accepted / num_drafts
  AL=$(awk -v a="$NUM_ACC_TOK" -v d="$NUM_DRAFTS" 'BEGIN{printf "%.2f", 1 + a/d}')
  printf "  %-44s %12s\n" "mean_acceptance_length (1 + acc/drafts)" "$AL"
fi
printf "\n"

# 5. Per-position acceptance
printf "%s-- Per-position acceptance (counts) --%s\n" "$BLD" "$CLR"
printf '%s' "$METRICS" \
  | awk '
    /^vllm:spec_decode_num_accepted_tokens_per_pos_total/ {
      match($0, /position="[0-9]+"/)
      pos = substr($0, RSTART+10, RLENGTH-11)
      val = $NF
      printf "  pos=%s : %.0f\n", pos, val
    }
  ' \
  | sort -k2 -t'=' -n \
  | head -20
printf "\n"

# 6. Summary
printf "%s=== Summary ===%s\n" "$BLD" "$CLR"
printf "  WARNS: %d\n" "$WARN_COUNT"
printf "  FAILS: %d\n" "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
  printf "%sOverall: FAIL%s\n" "$RED" "$CLR"; exit 1
elif [ "$WARN_COUNT" -gt 0 ]; then
  printf "%sOverall: PASS with warnings%s\n" "$YLW" "$CLR"; exit 2
else
  printf "%sOverall: PASS%s\n" "$GRN" "$CLR"; exit 0
fi
